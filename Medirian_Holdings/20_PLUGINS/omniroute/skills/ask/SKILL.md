---
name: ask
description: Ask another model routed through the OmniRoute gateway and report its answer. Use when the user wants a second opinion, wants to compare how other models (GPT, Gemini, DeepSeek, a combo, etc.) answer, or runs /omniroute:ask.
argument-hint: <model> <prompt>
allowed-tools: Bash(omni:*)
---

# Ask a model through OmniRoute

Arguments: `$ARGUMENTS` — the first word is the model id or combo name, the rest is the prompt.

1. If no model was given, or you are unsure of the exact id, run `omni models --filter <hint>` and pick the closest match. Do not guess ids.
2. Send the prompt. For anything longer than one line, or containing quotes, pipe it through stdin with a quoted heredoc:

   ```bash
   omni ask -m <model> - <<'PROMPT'
   <prompt text>
   PROMPT
   ```

   Add `-s "<system prompt>"` or `--max-tokens N` only when they help.
3. Include the context the other model needs (relevant code, the question itself). It cannot see this conversation.
4. Report the answer clearly attributed to that model, plus the `[model: …]` line printed on stderr. If you were asked for a comparison, say where it agrees or disagrees with your own view and why.

If `omni` fails with `OMNIROUTE_API_KEY is not set` or HTTP 401/403, tell the user to export a valid key (see the plugin README) instead of retrying.
