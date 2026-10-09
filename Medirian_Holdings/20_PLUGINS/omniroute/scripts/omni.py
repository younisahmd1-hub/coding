#!/usr/bin/env python3
"""omni: talk to an OmniRoute gateway's OpenAI-compatible /v1 API.

Usage:
  omni ping                          check the URL and key
  omni models [--filter TEXT]        list model ids the gateway exposes
  omni ask -m MODEL [-s SYSTEM] [--max-tokens N] PROMPT   (PROMPT "-" reads stdin)

Environment:
  OMNIROUTE_API_KEY   gateway API key (required; sent as a Bearer token)
  OMNIROUTE_URL       gateway URL, default https://omni.inamoriyama.com
                      (a trailing /v1 is accepted and ignored)
  OMNIROUTE_TIMEOUT   request timeout in seconds, default 120
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://omni.inamoriyama.com"


class OmniError(Exception):
    pass


def api_base():
    url = os.environ.get("OMNIROUTE_URL", "").strip() or DEFAULT_URL
    url = url.rstrip("/")
    if url.endswith("/v1"):
        url = url[: -len("/v1")]
    return url + "/v1"


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
        hint = " (check OMNIROUTE_API_KEY)" if e.code in (401, 403) else ""
        raise OmniError(f"HTTP {e.code} from {api_base()}{path}: {detail}{hint}")
    except urllib.error.URLError as e:
        raise OmniError(f"cannot reach {api_base()}: {e.reason}")


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
        raise OmniError("gateway returned no choices: " + json.dumps(resp)[:300])
    content = choices[0].get("message", {}).get("content") or ""
    return content, resp.get("model", model), resp.get("usage") or {}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="omni", description="OmniRoute gateway client")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="check the URL and key")
    p_models = sub.add_parser("models", help="list model ids")
    p_models.add_argument("--filter", help="case-insensitive substring filter")
    p_ask = sub.add_parser("ask", help="send one prompt to a model")
    p_ask.add_argument("-m", "--model", required=True, help="model id or combo name")
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
            content, model, usage = ask(args.model, prompt, args.system, args.max_tokens)
            print(content)
            tokens = ", ".join(f"{k}={v}" for k, v in usage.items() if isinstance(v, int))
            print(f"[model: {model}{'; ' + tokens if tokens else ''}]", file=sys.stderr)
    except OmniError as e:
        print(f"omni: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
