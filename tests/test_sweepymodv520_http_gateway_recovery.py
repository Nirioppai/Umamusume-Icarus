import unittest
from pathlib import Path

from career_bot.runner import CareerRunner

ROOT = Path(__file__).resolve().parents[1]
CLIENT_SOURCE = (ROOT / "uma_api" / "client.py").read_text(encoding="utf-8")
RUNNER_SOURCE = (ROOT / "career_bot" / "runner.py").read_text(encoding="utf-8")


class SweepyModV520GatewayRecoveryTests(unittest.TestCase):
    def test_http_504_is_recoverable_for_runner(self):
        runner = CareerRunner(".")
        self.assertTrue(
            runner._is_recoverable_error(
                Exception("HTTP 504 on single_mode_free/check_event: Gateway Timeout")
            )
        )
        self.assertTrue(runner._is_recoverable_error(Exception("HTTP 502 on single_mode_free/load")))
        self.assertTrue(runner._is_recoverable_error(Exception("HTTP 503 on single_mode_free/exec_command")))

    def test_runner_source_contains_gateway_tokens(self):
        for token in ("HTTP 502", "HTTP 503", "HTTP 504", "Gateway Timeout", "status=504"):
            self.assertIn(token, RUNNER_SOURCE)

    def test_client_retries_temporary_gateway_statuses_inside_post_loop(self):
        self.assertIn("retryable_http_statuses = {500, 502, 503, 504}", CLIENT_SOURCE)
        self.assertIn("while True:", CLIENT_SOURCE)
        self.assertIn("http_retries_left = 5", CLIENT_SOURCE)
        self.assertIn("resp.status_code in retryable_http_statuses", CLIENT_SOURCE)
        self.assertIn("temporary gateway/server error", CLIENT_SOURCE)
        self.assertIn("Retrying in", CLIENT_SOURCE)
        self.assertLess(
            CLIENT_SOURCE.index("retryable_http_statuses = {500, 502, 503, 504}"),
            CLIENT_SOURCE.index("res = unpack(resp.text.strip(), self.udid_str)"),
        )

    def test_result_code_retries_are_iterative_and_independent(self):
        self.assertIn("retries_205_left = retry_205", CLIENT_SOURCE)
        self.assertIn("retries_208_left = retry_208", CLIENT_SOURCE)
        self.assertIn("attempt_208 = 0", CLIENT_SOURCE)
        self.assertIn("wait_min = min(0.8 * (2 ** attempt_208), 12.0)", CLIENT_SOURCE)
        self.assertIn("continue", CLIENT_SOURCE[CLIENT_SOURCE.index("if rc == 205"):CLIENT_SOURCE.index("err_detail = format_api_error")])
        self.assertNotIn("return self.call(ep, args", CLIENT_SOURCE)

    def test_client_keeps_permanent_http_errors_fatal(self):
        self.assertIn("print(f\"HTTP error on {ep}: status={resp.status_code} body={body_preview}\")", CLIENT_SOURCE)
        self.assertIn("raise Exception(f'HTTP {resp.status_code} on {ep}: {body_preview}')", CLIENT_SOURCE)


if __name__ == "__main__":
    unittest.main()
