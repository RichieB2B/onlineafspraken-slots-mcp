# OnlineAfspraken slots MCP

Read available slots from a public OnlineAfspraken widget URL without an account.
This local MCP server reads availability only; it cannot make a booking.

## Get started

You need Python 3.10 or newer and an MCP client. The commands below use a Unix
shell (macOS or Linux).

1. Download or clone this repository.
2. In its directory, install the Python dependency:

   ```sh
   sh setup.sh
   ```

3. Register the server with your MCP client using one of the examples below.
   Replace `/absolute/path/to/onlineafspraken-slots` with the full path to your
   downloaded copy.
4. Start a new chat and provide a public OnlineAfspraken widget URL. For
   example: “Show today's available times for this widget: [paste the full
   widget URL here].”

You can also pass the URL of a public booking page that embeds one
OnlineAfspraken widget. If the page has several widgets, use the direct URL of
the one you want.

## Connect your MCP client

### Codex

```sh
codex mcp add onlineafspraken-slots -- /absolute/path/to/onlineafspraken-slots/run.sh
codex mcp list
```

### Claude Code

```sh
claude mcp add --scope user --transport stdio onlineafspraken-slots -- /absolute/path/to/onlineafspraken-slots/run.sh
claude mcp list
```

The user scope makes the server available in all your Claude Code projects.
See the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp)
for other scopes.

### Claude Desktop

Add this entry under `mcpServers` in your Claude Desktop configuration, then
restart Claude Desktop:

```json
{
  "mcpServers": {
    "onlineafspraken-slots": {
      "command": "/absolute/path/to/onlineafspraken-slots/run.sh"
    }
  }
}
```

If you already have an `mcpServers` object, add just the
`onlineafspraken-slots` entry to it. The [Claude Desktop local server
guide](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
explains where to manage local servers and check their connection status.

### OpenCode

```sh
opencode mcp add onlineafspraken-slots --global -- /absolute/path/to/onlineafspraken-slots/run.sh
opencode mcp list
```

The global option makes the server available in every OpenCode project. See
the [OpenCode MCP documentation](https://opencode.ai/v2/docs/mcp-servers) for
project-specific configuration.

## Tool inputs

The server exposes `get_available_slots`:

| Input | Required | Meaning |
| --- | --- | --- |
| `booking_page` | Yes | Full HTTPS URL of a public OnlineAfspraken widget or a page that embeds it. |
| `date_iso` | No | Date in `YYYY-MM-DD` format. Defaults to today in Europe/Amsterdam. |
| `room` | No | Part of an appointment type name to filter the results. |

Results include the appointment type names, available start times, date,
timezone, and the time the availability was checked. The `room` input is named
for the original use case; it works with any appointment type.

## Limitations

The server uses the widget's public, undocumented read endpoint. A provider
change may require an update. A booking page must expose its widget URL in a
script, iframe, or link for automatic discovery. Available slots can change
between lookup and booking.

## License

[MIT](LICENSE)
