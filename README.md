# OnlineAfspraken slots MCP

<!-- mcp-name: io.github.RichieB2B/onlineafspraken-slots -->

Read available slots from a public OnlineAfspraken widget URL without an account.
This local MCP server reads availability only; it cannot make a booking.

## Get started

You need Python 3.10 or newer and an MCP client. The commands below use a Unix
shell (macOS or Linux).

1. Download or clone this repository.
2. In its directory, install the package and its dependencies:

   ```sh
   sh setup.sh
   ```

3. Register the server with your MCP client using one of the examples below.
   Replace `/absolute/path/to/onlineafspraken-slots-mcp` with the full path to
   your downloaded copy.
4. Start a new chat and provide a public OnlineAfspraken widget URL. For
   example: “Show today's available times for this widget: [paste the full
   widget URL here].”

You can also pass the URL of a public booking page that embeds one
OnlineAfspraken widget. If the page has several widgets, use the direct URL of
the one you want.

## Connect your MCP client

### Codex

```sh
codex mcp add onlineafspraken-slots -- /absolute/path/to/onlineafspraken-slots-mcp/run.sh
codex mcp list
```

### Claude Code

```sh
claude mcp add --scope user --transport stdio onlineafspraken-slots -- /absolute/path/to/onlineafspraken-slots-mcp/run.sh
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
      "command": "/absolute/path/to/onlineafspraken-slots-mcp/run.sh"
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
opencode mcp add onlineafspraken-slots --global -- /absolute/path/to/onlineafspraken-slots-mcp/run.sh
opencode mcp list
```

The global option makes the server available in every OpenCode project. See
the [OpenCode MCP documentation](https://opencode.ai/v2/docs/mcp-servers) for
project-specific configuration.

After the first PyPI release, clients that support a package runner can launch
the `onlineafspraken-slots-mcp` command from that package instead of using a
local checkout.

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

## Publishing a release

For maintainers: keep the version in `pyproject.toml` and `server.json` in
sync. To publish the first release, [configure a pending PyPI trusted
publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
with these values:

| PyPI field | Value |
| --- | --- |
| PyPI project name | `onlineafspraken-slots-mcp` |
| Owner | `RichieB2B` |
| Repository | `onlineafspraken-slots-mcp` |
| Workflow | `publish-pypi.yml` |
| Environment | `pypi` |

Then publish a GitHub release tagged `v0.1.0`. The
[release workflow](.github/workflows/publish-pypi.yml) builds and checks the
distributions and uploads them to PyPI through trusted publishing. After the
PyPI package is available, publish its MCP Registry listing:

```sh
mcp-publisher validate
mcp-publisher login github
mcp-publisher publish
```

The [official MCP Registry guide](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)
explains publisher installation and GitHub authentication. The registry checks
the `mcp-name` marker above against the README included in the PyPI release.
