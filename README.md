# OnlineAfspraken slots MCP

This local, read-only MCP server exposes
`get_available_slots(booking_page, date_iso, room)`. Pass a public HTTPS page
that embeds an OnlineAfspraken booking widget, or pass a direct widget URL.

The server discovers the widget key and appointment type IDs from the widget
URL, fetches their current names, then reads available times. It does not book
appointments or require account credentials. Dates default to today in
Europe/Amsterdam; `room` optionally filters by part of an appointment type
name.

## Setup

This copy is already set up on this Mac. If moving it to another computer,
run `sh setup.sh` from this directory to install the Python MCP SDK into
`.venv`.

## Connect to Codex

This copy is already registered in Codex as `onlineafspraken-slots`.
If you move the directory, update the registration with:

```sh
codex mcp remove onlineafspraken-slots
codex mcp add onlineafspraken-slots -- /absolute/path/to/onlineafspraken-slots/run.sh
codex mcp list
```

Replace the path with the full path to this directory. Start a new Codex chat
to use the newly registered tool, then ask for slots at a public
OnlineAfspraken booking page on a date.

## Limitations

The server uses the widget's public, undocumented read endpoint. If the
provider changes that endpoint or the widget URL format, this server may need
updating. Booking pages must expose the widget URL in a script, iframe, or
link in their HTML. Availability can change between lookup and booking.
