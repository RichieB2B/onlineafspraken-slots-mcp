# Escape Schijndel availability MCP

This local, read-only MCP server exposes `get_available_slots(date_iso, room)`.
It reads the same public availability feed used by the booking widget at
https://escapeschijndel.nl/reserveren/. It does not book appointments and
requires no account credentials.

## Setup

This copy is already set up on this Mac. If moving it to another computer,
run `sh setup.sh` from this directory to install the Python MCP SDK into
`.venv`.

## Connect to Codex

This copy is already registered in Codex as `escape-schijndel-slots`.
If you move the directory, update the registration with:

```sh
codex mcp remove escape-schijndel-slots
codex mcp add escape-schijndel-slots -- /absolute/path/to/escape-slots-mcp/run.sh
codex mcp list
```

Replace the path with the full path to this directory. Start a new Codex chat
to use the newly registered tool, then ask for Escape Schijndel slots on a
date. The server uses Europe/Amsterdam time and defaults to today when no
date is supplied.

## Limitations

The server uses the widget's public, undocumented read endpoint and the four
appointment type IDs in the supplied widget URL. If the provider changes that
endpoint or those IDs, this server may need updating. Availability can change
between lookup and booking.
