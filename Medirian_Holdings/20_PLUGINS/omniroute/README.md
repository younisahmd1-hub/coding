# omniroute — Claude Code plugin

Connects Claude Code to the OmniRoute AI gateway at `https://omni.inamoriyama.com`.

| Part | What it gives you |
|---|---|
| `skills/ask` → `/omniroute:ask <model> <prompt>` | Send a prompt to any model or combo on the gateway (second opinions, comparisons). Claude can also use it on its own. |
| `skills/models` → `/omniroute:models [filter]` | List the model ids the gateway exposes. |
| `bin/omni` → `scripts/omni.py` | Small Python CLI (standard library only) for the gateway's OpenAI-compatible API at `/api/v1` (the `/v1` alias on omni.inamoriyama.com sits behind nginx's own login, so the plugin doesn't use it). Claude Code puts `bin/` on the Bash PATH while the plugin is on; the `bin/omni` wrapper finds `python3`, `python` or the Windows `py` launcher. Needs Python 3.8+ (Windows: `winget install Python.Python.3.13`). |
| `.mcp.json` → MCP server `omniroute` | The gateway's own MCP tools (health, combos, quotas, costs, routing, budget guard) over `/api/mcp/stream`. |

## Setup

1. **Create an API key** in the OmniRoute dashboard → API Manager. For the MCP tools the key needs the `mcp:connect` scope (or `manage`).
2. **Give Claude Code the key.** On Windows: `setx OMNIROUTE_API_KEY "<your key>"`, then open a new terminal. On macOS/Linux, export it in the shell that starts Claude Code:

   ```bash
   export OMNIROUTE_API_KEY="<your key>"
   # optional, only for a different gateway:
   export OMNIROUTE_URL="https://omni.inamoriyama.com"
   ```

   Never commit the key to this repository.
3. **Turn on the MCP transport** (only for the MCP tools): OmniRoute dashboard → Settings → MCP transport → `streamable-http`. Without it, the `omniroute` MCP server shows as failed in `/mcp`; the `omni` CLI and both skills work either way.
4. **Install the plugin** from inside Claude Code:

   ```
   /plugin marketplace add younisahmd1-hub/coding
   /plugin install omniroute@medirian
   ```

   Then restart Claude Code and check with `/omniroute:models` and `/mcp`.

## Use

```
/omniroute:models gemini
/omniroute:ask openai/gpt-5 Review this function for race conditions: ...
```

Directly in a terminal:

```bash
omni ping
omni models --filter claude
echo "Summarise this diff" | omni ask -m my-combo -
```

## Tests

```bash
cd Medirian_Holdings/20_PLUGINS/omniroute && python3 -m unittest discover -s tests -t .
claude plugin validate Medirian_Holdings/20_PLUGINS/omniroute
```

## Not part of this plugin

Routing **Claude Code's own model traffic** through the gateway is a user setting, not something a plugin can set. If you want that, put `ANTHROPIC_BASE_URL` (the gateway URL) and `ANTHROPIC_AUTH_TOKEN` (the key) under `env` in your own `~/.claude/settings.json`, and check first that the gateway serves the Anthropic `/v1/messages` format.
