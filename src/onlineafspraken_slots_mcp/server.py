"""Read public OnlineAfspraken booking availability over MCP."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import time
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlencode, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP


APPLICATION_ID = "widget-booking"
WIDGET_HOST = "widget.onlineafspraken.nl"
API_ROOT = f"https://{WIDGET_HOST}/consumer/booking/api/method/"
TIMEZONE = ZoneInfo("Europe/Amsterdam")
SERVER = FastMCP("onlineafspraken-slots")


class _WidgetLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attribute = "href" if tag == "a" else "src"
        if tag in {"script", "iframe", "a"}:
            value = dict(attrs).get(attribute)
            if value:
                self.links.append(value)


def _public_https_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("booking_page must be a public HTTPS URL")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        raise ValueError("booking_page must be a public HTTPS URL")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("booking_page must be a public HTTPS URL")
    return value


def _is_widget_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme == "https" and parsed.hostname == WIDGET_HOST and (
        "/consumer/booking/book/key/" in parsed.path
    )


def _discover_widget(booking_page: str) -> str:
    booking_page = _public_https_url(booking_page)
    if _is_widget_url(booking_page):
        return booking_page

    request = Request(booking_page, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        document_url = _public_https_url(response.geturl())
        content_type = response.headers.get_content_type()
        if content_type != "text/html":
            raise ValueError("booking_page did not return an HTML page")
        html = response.read(2_000_001)
    if len(html) > 2_000_000:
        raise ValueError("booking_page is too large to inspect")

    parser = _WidgetLinks()
    parser.feed(html.decode("utf-8", "replace"))
    widgets = list(dict.fromkeys(
        urljoin(document_url, link)
        for link in parser.links
        if _is_widget_url(urljoin(document_url, link))
    ))
    if not widgets:
        raise ValueError("No OnlineAfspraken booking widget found on booking_page")
    if len(widgets) > 1:
        raise ValueError("Multiple booking widgets found; pass a direct widget URL")
    return widgets[0]


def _path_value(widget_url: str, field: str) -> str | None:
    parts = urlsplit(widget_url).path.strip("/").split("/")
    try:
        return parts[parts.index(field) + 1]
    except (ValueError, IndexError):
        return None


def _id_filter(widget_url: str, field: str) -> list[int]:
    raw = _path_value(widget_url, field)
    if not raw or raw == "0":
        return []
    try:
        return [int(value) for value in raw.split(",")]
    except ValueError as exc:
        raise ValueError(f"Invalid {field} filter in the booking widget URL") from exc


def _signed_params(method: str, widget_url: str, filters: dict[str, str]) -> dict[str, str]:
    """Sign a read request in the same way as the public widget."""
    widget_key = _path_value(widget_url, "key")
    if not widget_key:
        raise ValueError("The booking widget URL has no key")
    params = {
        **filters,
        "applicationId": APPLICATION_ID,
        "method": method,
        "api_salt": str(int(time.time() * 1000)),
        "api_lang": _path_value(widget_url, "ln") or "nl",
        "api_format": "json",
    }
    exclude = {"api_salt", "api_key", "api_signature", "api_format", "api_lang", "api_jsonp_callback"}
    signature_text = "".join(key + params[key] for key in sorted(params) if key not in exclude)
    signature_text += APPLICATION_ID + params["api_salt"]
    params["api_signature"] = hashlib.sha1(signature_text.encode("utf-8")).hexdigest()
    params["api_key"] = widget_key
    del params["method"]  # Signed above, then represented in the URL path.
    return params


def _api_items(method: str, widget_url: str, booking_page: str, filters: dict[str, str]) -> list[dict]:
    query = urlencode(_signed_params(method, widget_url, filters))
    request = Request(
        f"{API_ROOT}{method}?{query}",
        headers={
            "Accept": "application/json",
            "Referer": booking_page,
            "X-Requested-With": "XMLHttpRequest",
            "X-OANL-CSRF-PROTECTION": "on",
        },
    )
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    status = payload.get("status", {})
    if status.get("status") != "success":
        raise RuntimeError(f"Booking widget API error: {status.get('message', 'unknown error')}")
    return payload.get("result", {}).get("items", [])


def _rooms(widget_url: str, booking_page: str) -> dict[int, str]:
    selected_ids = _id_filter(widget_url, "at")
    filters = {
        "filter_apptype": ",".join(map(str, selected_ids)),
        "filter_resource": ",".join(map(str, _id_filter(widget_url, "rs"))),
    }
    items = _api_items("getApptypes", widget_url, booking_page, filters)
    names = {int(item["id"]): item["name"] for item in items if item.get("id") and item.get("name")}
    ordered_ids = selected_ids or list(names)
    rooms = {room_id: names[room_id] for room_id in ordered_ids if room_id in names}
    if not rooms:
        raise RuntimeError("The booking widget returned no appointment types")
    return rooms


def _expand_chop(chop: dict) -> list[str]:
    """Expand the widget's time range using its step and inclusive end flag."""
    start = _minutes(chop["startTime"])
    step = chop.get("stepSize")
    if not step:
        return [chop["startTime"]]
    step = int(step)
    if step <= 0:
        raise RuntimeError("The widget returned an invalid time step")
    finish = _minutes(chop["finishTime"])
    if finish < start:
        finish += 24 * 60
    include_finish = chop.get("useFinishTime", True)
    return [
        f"{minute // 60:02d}:{minute % 60:02d}"
        for minute in range(start, min(finish, 24 * 60 - 1) + 1, step)
        if minute < finish or include_finish
    ]


def _minutes(hhmm: str) -> int:
    hour, minute = map(int, hhmm.split(":"))
    return hour * 60 + minute


def _read_slots(booking_page: str, requested_date: date) -> dict:
    widget_url = _discover_widget(booking_page)
    rooms = _rooms(widget_url, booking_page)
    filters = {
        "startDate": requested_date.isoformat(),
        "filter_apptype": ",".join(map(str, rooms)),
        "filter_resource": ",".join(map(str, _id_filter(widget_url, "rs"))),
    }
    items = _api_items("getTimes", widget_url, booking_page, filters)
    times_by_room: dict[int, set[str]] = {room_id: set() for room_id in rooms}
    for item in items:
        if item.get("date") != requested_date.isoformat():
            continue
        room_id = item.get("appTypeId")
        if room_id not in times_by_room:
            continue
        for chop in item.get("times", []):
            times_by_room[room_id].update(_expand_chop(chop))

    return {
        "booking_page": booking_page,
        "date": requested_date.isoformat(),
        "timezone": "Europe/Amsterdam",
        "checked_at": datetime.now(TIMEZONE).isoformat(timespec="seconds"),
        "rooms": [
            {"name": name, "times": sorted(times_by_room[room_id])}
            for room_id, name in rooms.items()
        ],
    }


@SERVER.tool()
def get_available_slots(booking_page: str, date_iso: str | None = None, room: str | None = None) -> dict:
    """Get public OnlineAfspraken slots for a booking page and ISO date.

    booking_page may be a page embedding one OnlineAfspraken widget or the
    widget URL itself. Omit date_iso for today in Europe/Amsterdam. Optionally
    filter by part of an appointment type name. This tool never books.
    """
    try:
        requested_date = date.fromisoformat(date_iso) if date_iso else datetime.now(TIMEZONE).date()
    except ValueError as exc:
        raise ValueError("date_iso must be YYYY-MM-DD") from exc
    if requested_date < datetime.now(TIMEZONE).date():
        raise ValueError("date_iso must be today or later")

    result = _read_slots(booking_page, requested_date)
    if room:
        matches = [entry for entry in result["rooms"] if room.casefold() in entry["name"].casefold()]
        if not matches:
            available = ", ".join(entry["name"] for entry in result["rooms"])
            raise ValueError(f"No room matches {room!r}; available rooms: {available}")
        result["rooms"] = matches
    return result


def main() -> None:
    """Start the MCP server over stdio."""
    SERVER.run(transport="stdio")


if __name__ == "__main__":
    main()
