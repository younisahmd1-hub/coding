#!/usr/bin/env python3
"""omni: talk to an OmniRoute gateway's OpenAI-compatible API (/api/v1).

Usage:
  omni ping                          check the URL and key
  omni models [--filter TEXT]        list model ids the gateway exposes
  omni ask [-m MODEL] [-s SYSTEM] [--max-tokens N] PROMPT   (PROMPT "-" reads stdin)

Environment:
  OMNIROUTE_API_KEY   gateway API key (required; sent as a Bearer token)
  OMNIROUTE_URL       gateway URL, default https://omni.inamoriyama.com
                      (a trailing /v1 or /api/v1 is accepted and ignored)
  OMNIROUTE_TIMEOUT   request timeout in seconds, default 120
  OMNIROUTE_MODEL     model used when -m is not given, default claude/claude-sonnet-4-6
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://omni.inamoriyama.com"
DEFAULT_MODEL = "claude/claude-sonnet-4-6"


class OmniError(Exception):
    pass


def api_base():
    # OmniRoute serves its OpenAI-compatible API under /api/v1; the /v1 alias can sit
    # behind a reverse proxy's own auth (as on omni.inamoriyama.com), so always use /api/v1.
    url = os.environ.get("OMNIROUTE_URL", "").strip() or DEFAULT_URL
    url = url.rstrip("/")
    for suffix in ("/api/v1", "/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
            break
    return url + "/api/v1"


def request(method, path, body=None):
    key = os.environ.get("OMNIROUTE_API_KEY", "").strip()
    if not key:
        raise OmniError("OMNIROUTE_API_KEY is not set. Create a key in the OmniRoute "
                        "dashboard (API Manager) and export it.")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(api_base() + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    timeout = float(os.environ.get("OMNIROUTE_TIMEOUT", "120"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        try:
            err = json.loads(detail).get("error", detail)
            detail = err.get("message", err) if isinstance(err, dict) else err
        except (ValueError, AttributeError):
            detail = " ".join(detail.split())[:300]
        hint = " (check OMNIROUTE_API_KEY)" if e.code == 401 else ""
        raise OmniError(f"HTTP {e.code} from {api_base()}{path}: {detail}{hint}")
    except urllib.error.URLError as e:
        raise OmniError(f"cannot reach {api_base()}: {e.reason}")
    except (TimeoutError, OSError) as e:
        raise OmniError(f"no answer from {api_base()}{path} within {timeout:g}s ({e}); "
                        "try another model or raise OMNIROUTE_TIMEOUT")


def list_models(filter_text=None):
    ids = sorted(m.get("id", "") for m in request("GET", "/models").get("data", []))
    if filter_text:
        ids = [i for i in ids if filter_text.lower() in i.lower()]
    return ids


def ask(model, prompt, system=None, max_tokens=None):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {"model": model, "messages": messages, "stream": False}
    if max_tokens:
        body["max_tokens"] = max_tokens
    resp = request("POST", "/chat/completions", body)
    choices = resp.get("choices") or []
    if not choices:
        raise OmniError(f"empty answer from {model}: the gateway returned no choices, which usually "
                        "means every provider behind it failed; try another model")
    content = choices[0].get("message", {}).get("content") or ""
    if not content.strip():
        reason = choices[0].get("finish_reason") or "unknown"
        hint = "; raise --max-tokens" if reason == "length" else ""
        raise OmniError(f"{model} returned an empty message (finish_reason={reason}){hint}")
    return content, resp.get("model", model), resp.get("usage") or {}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="omni", description="OmniRoute gateway client")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="check the URL and key")
    p_models = sub.add_parser("models", help="list model ids")
    p_models.add_argument("--filter", help="case-insensitive substring filter")
    p_ask = sub.add_parser("ask", help="send one prompt to a model")
    p_ask.add_argument("-m", "--model", help="model id or combo name (default: $OMNIROUTE_MODEL or "
                       + DEFAULT_MODEL + ")")
    p_ask.add_argument("-s", "--system", help="system prompt")
    p_ask.add_argument("--max-tokens", type=int)
    p_ask.add_argument("prompt", help='prompt text, or "-" to read stdin')
    args = parser.parse_args(argv)

    try:
        if args.cmd == "ping":
            print(f"ok: {api_base()} ({len(list_models())} models)")
        elif args.cmd == "models":
            ids = list_models(args.filter)
            print("\n".join(ids) if ids else "(no models matched)")
        else:
            prompt = sys.stdin.read() if args.prompt == "-" else args.prompt
            if not prompt.strip():
                raise OmniError("empty prompt")
            model = args.model or os.environ.get("OMNIROUTE_MODEL", "").strip() or DEFAULT_MODEL
            content, model, usage = ask(model, prompt, args.system, args.max_tokens)
            print(content)
            tokens = ", ".join(f"{k}={v}" for k, v in usage.items() if isinstance(v, int))
            print(f"[model: {model}{'; ' + tokens if tokens else ''}]", file=sys.stderr)
    except OmniError as e:
        print(f"omni: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
