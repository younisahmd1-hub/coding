---
name: models
description: List the models and combos available on the OmniRoute gateway, optionally filtered. Use when the user asks which models the gateway offers or runs /omniroute:models.
argument-hint: "[filter]"
allowed-tools: Bash(omni:*)
---

# List OmniRoute models

Run `omni models` (add `--filter "$ARGUMENTS"` when a filter was given) and show the result as a compact list grouped by provider prefix (the part before `/`, if any).

If the omniroute MCP tools are connected, `omniroute_list_models_catalog` adds pricing and `omniroute_list_combos` lists routing combos; use them when the user asks about cost or combos.

If `omni` reports a missing key or HTTP 401/403, point the user to the plugin README setup steps.
