import io
import json
import os
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

omni = SourceFileLoader("omni", str(Path(__file__).resolve().parents[1] / "bin" / "omni")).load_module()

KEY = "test-key"


class FakeGateway(BaseHTTPRequestHandler):
    last_body = None

    def log_message(self, *args):
        pass

    def _send(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authorized(self):
        if self.headers.get("Authorization") != "Bearer " + KEY:
            self._send(401, {"error": {"message": "invalid api key"}})
            return False
        return True

    def do_GET(self):
        if not self._authorized():
            return
        if self.path == "/v1/models":
            self._send(200, {"data": [{"id": "openai/gpt-5"}, {"id": "gemini/gemini-3-pro"}, {"id": "my-combo"}]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._authorized():
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeGateway.last_body = body
        if self.path == "/v1/chat/completions":
            self._send(200, {
                "model": body["model"],
                "choices": [{"message": {"role": "assistant", "content": "echo: " + body["messages"][-1]["content"]}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            })
        else:
            self._send(404, {"error": "not found"})


class OmniTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeGateway)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def run_cli(self, argv, env):
        out, err = io.StringIO(), io.StringIO()
        clean = {k: v for k, v in os.environ.items() if not k.startswith("OMNIROUTE_")}
        clean["NO_PROXY"] = clean["no_proxy"] = "127.0.0.1"
        with mock.patch.dict(os.environ, {**clean, **env}, clear=True), redirect_stdout(out), redirect_stderr(err):
            code = omni.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_api_base_defaults_and_strips_v1(self):
        with mock.patch.dict(os.environ, {"OMNIROUTE_URL": ""}):
            self.assertEqual(omni.api_base(), "https://omni.inamoriyama.com/v1")
        with mock.patch.dict(os.environ, {"OMNIROUTE_URL": "https://gw.example/v1/"}):
            self.assertEqual(omni.api_base(), "https://gw.example/v1")

    def test_missing_key(self):
        code, _, err = self.run_cli(["models"], {"OMNIROUTE_URL": self.url})
        self.assertEqual(code, 1)
        self.assertIn("OMNIROUTE_API_KEY is not set", err)

    def test_bad_key_reports_401(self):
        code, _, err = self.run_cli(["models"], {"OMNIROUTE_URL": self.url, "OMNIROUTE_API_KEY": "nope"})
        self.assertEqual(code, 1)
        self.assertIn("HTTP 401", err)
        self.assertIn("invalid api key", err)

    def test_models_sorted_and_filtered(self):
        env = {"OMNIROUTE_URL": self.url + "/v1", "OMNIROUTE_API_KEY": KEY}
        code, out, _ = self.run_cli(["models"], env)
        self.assertEqual(code, 0)
        self.assertEqual(out.split(), ["gemini/gemini-3-pro", "my-combo", "openai/gpt-5"])
        code, out, _ = self.run_cli(["models", "--filter", "GPT"], env)
        self.assertEqual(out.split(), ["openai/gpt-5"])

    def test_ask_sends_system_and_prints_usage(self):
        env = {"OMNIROUTE_URL": self.url, "OMNIROUTE_API_KEY": KEY}
        code, out, err = self.run_cli(["ask", "-m", "my-combo", "-s", "be brief", "--max-tokens", "50", "hello"], env)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "echo: hello")
        self.assertIn("[model: my-combo; prompt_tokens=3, completion_tokens=2]", err)
        body = FakeGateway.last_body
        self.assertEqual(body["messages"][0], {"role": "system", "content": "be brief"})
        self.assertEqual(body["max_tokens"], 50)
        self.assertFalse(body["stream"])

    def test_ask_reads_stdin(self):
        env = {"OMNIROUTE_URL": self.url, "OMNIROUTE_API_KEY": KEY}
        with mock.patch("sys.stdin", io.StringIO("from stdin")):
            code, out, _ = self.run_cli(["ask", "-m", "openai/gpt-5", "-"], env)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "echo: from stdin")

    def test_ping(self):
        code, out, _ = self.run_cli(["ping"], {"OMNIROUTE_URL": self.url, "OMNIROUTE_API_KEY": KEY})
        self.assertEqual(code, 0)
        self.assertIn("3 models", out)


if __name__ == "__main__":
    unittest.main()
