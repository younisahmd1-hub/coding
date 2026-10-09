---
name: ask
description: Ask another model routed through the OmniRoute gateway and report its answer. Use when the user wants a second opinion, wants to compare how other models (GPT, Gemini, DeepSeek, a combo, etc.) answer, or runs /omniroute:ask.
argument-hint: "[model] <prompt>"
allowed-tools: Bash(omni:*)
---

# Ask a model through OmniRoute

Arguments: `$ARGUMENTS`. If the first word is a model id or combo name (it contains `/`, or appears in `omni models`), use it with `-m`. Otherwise everything is the prompt and `omni` uses its default model (`$OMNIROUTE_MODEL`, else `claude/claude-sonnet-4-6`).

1. When the user names a model loosely ("gpt", "gemini"), run `omni models --filter <hint>` and pick the closest id. Do not guess ids.
2. Send the prompt. For anything longer than one line, or containing quotes, pipe it through stdin with a quoted heredoc:

   ```bash
   omni ask -m <model> - <<'PROMPT'
   <prompt text>
   PROMPT
   ```

   Add `-s "<system prompt>"` or `--max-tokens N` only when they help.
3. Include the context the other model needs (relevant code, the question itself). It cannot see this conversation.
4. Report the answer clearly attributed to that model, plus the `[model: …]` line printed on stderr. If you were asked for a comparison, say where it agrees or disagrees with your own view and why.

If a model fails (HTTP 4xx/5xx from a provider, "empty answer", or a timeout), tell the user which model failed and why in one line, then retry once without `-m` so the default model answers. Do not loop through many models. If `omni` says `OMNIROUTE_API_KEY is not set` or returns HTTP 401, tell the user to set a valid key (see the plugin README) instead of retrying.
