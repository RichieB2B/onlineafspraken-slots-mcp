"""Read Escape Schijndel's public booking availability over MCP."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP


BOOKING_PAGE = "https://escapeschijndel.nl/reserveren/"
API_URL = "https://widget.onlineafspraken.nl/consumer/booking/api/method/getTimes"
WIDGET_KEY = "mfde44culy14-adda04"  # Public key in the user-supplied widget URL.
APPLICATION_ID = "widget-booking"
ROOMS = {
    484242: "Het Brabantse Lab",
    484248: "No Way Out NEDERLANDS",
    484245: "Professor Co de Kraker",
    630020: "The Crimsons Recipe",
}
TIMEZONE = ZoneInfo("Europe/Amsterdam")
SERVER = FastMCP("escape-schijndel-slots")


def _signed_params(requested_date: date) -> dict[str, str]:
    """Sign a read request in the same way as the public booking widget."""
    params = {
        "applicationId": APPLICATION_ID,
        "startDate": requested_date.isoformat(),
        "filter_apptype": ",".join(str(room_id) for room_id in ROOMS),
        "filter_resource": "",
        "method": "getTimes",
        "api_salt": str(int(time.time() * 1000)),
        "api_lang": "nl",
        "api_format": "json",
    }
    unsigned = {key: value for key, value in params.items() if key not in {
        "api_salt", "api_key", "api_signature", "api_format", "api_lang", "api_jsonp_callback"
    }}
    signature_text = "".join(key + unsigned[key] for key in sorted(unsigned))
    signature_text += APPLICATION_ID + params["api_salt"]
    params["api_signature"] = hashlib.sha1(signature_text.encode("utf-8")).hexdigest()
    params["api_key"] = WIDGET_KEY
    del params["method"]  # Signed above, then represented in the URL path.
    return params


def _expand_chop(chop: dict) -> list[str]:
    """Expand the widget's time range using its step and inclusive end flag."""
    start = _minutes(chop["startTime"])
    step = chop.get("stepSize")
    if not step:
        return [chop["startTime"]]
    step = int(step)
    if step <= 0:
        raise RuntimeError("The widget returned an invalid time step.")
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


def _read_slots(requested_date: date) -> dict:
    query = urlencode(_signed_params(requested_date))
    request = Request(
        f"{API_URL}?{query}",
        headers={
            "Accept": "application/json",
            "Referer": BOOKING_PAGE,
            "X-Requested-With": "XMLHttpRequest",
            "X-OANL-CSRF-PROTECTION": "on",
        },
    )
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    status = payload.get("status", {})
    if status.get("status") != "success":
        raise RuntimeError(f"Booking widget API error: {status.get('message', 'unknown error')}")

    times_by_room: dict[int, set[str]] = {room_id: set() for room_id in ROOMS}
    for item in payload.get("result", {}).get("items", []):
        if item.get("date") != requested_date.isoformat():
            continue
        room_id = item.get("appTypeId")
        if room_id not in times_by_room:
            continue
        for chop in item.get("times", []):
            times_by_room[room_id].update(_expand_chop(chop))

    return {
        "date": requested_date.isoformat(),
        "timezone": "Europe/Amsterdam",
        "checked_at": datetime.now(TIMEZONE).isoformat(timespec="seconds"),
        "rooms": [
            {"name": name, "times": sorted(times_by_room[room_id])}
            for room_id, name in ROOMS.items()
        ],
        "source": BOOKING_PAGE,
    }


@SERVER.tool()
def get_available_slots(date_iso: str | None = None, room: str | None = None) -> dict:
    """Get selectable Escape Schijndel slots for an ISO date (YYYY-MM-DD).

    Omit date_iso for today in Europe/Amsterdam. Optionally filter to one room
    using part of its name. This reads public availability and never books.
    """
    try:
        requested_date = date.fromisoformat(date_iso) if date_iso else datetime.now(TIMEZONE).date()
    except ValueError as exc:
        raise ValueError("date_iso must be YYYY-MM-DD") from exc
    if requested_date < datetime.now(TIMEZONE).date():
        raise ValueError("date_iso must be today or later")

    result = _read_slots(requested_date)
    if room:
        matches = [entry for entry in result["rooms"] if room.casefold() in entry["name"].casefold()]
        if not matches:
            raise ValueError(f"No room matches {room!r}; available rooms: " + ", ".join(x["name"] for x in result["rooms"]))
        result["rooms"] = matches
    return result


if __name__ == "__main__":
    SERVER.run(transport="stdio")
