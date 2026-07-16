import hashlib
import hmac
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.config import settings
from app.services.a5_auth_service import verify_a5_callback_signature


def signed_headers(body: str, secret: str, timestamp: int, *, lowercase: bool = True) -> dict[str, str]:
    signature = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    signature_header = "x-a5-signature" if lowercase else "X-A5-Signature"
    timestamp_header = "x-a5-timestamp" if lowercase else "X-A5-Timestamp"
    return {signature_header: signature, timestamp_header: str(timestamp)}


class A5CallbackSecurityTest(unittest.TestCase):
    def test_lowercase_asgi_headers_with_valid_hmac_are_accepted(self):
        body = '{"operation_no":"OP-1","status":"WORKING"}'
        timestamp = int(datetime.now(timezone.utc).timestamp())

        with patch.object(settings, "a5_api_secret", "test-secret"), patch.object(settings, "a5_ip_whitelist", ""):
            valid = verify_a5_callback_signature(
                signed_headers(body, "test-secret", timestamp),
                body,
            )

        self.assertTrue(valid)

    def test_missing_secret_rejects_even_when_signature_header_exists(self):
        with patch.object(settings, "a5_api_secret", ""), patch.object(settings, "a5_ip_whitelist", ""):
            valid = verify_a5_callback_signature(
                {"x-a5-signature": "arbitrary", "x-a5-timestamp": "0"},
                "{}",
            )

        self.assertFalse(valid)

    def test_expired_timestamp_is_rejected_before_signature_is_applied(self):
        body = '{"operation_no":"OP-1"}'
        timestamp = int((datetime.now(timezone.utc) - timedelta(minutes=6)).timestamp())

        with patch.object(settings, "a5_api_secret", "test-secret"), patch.object(settings, "a5_ip_whitelist", ""):
            valid = verify_a5_callback_signature(
                signed_headers(body, "test-secret", timestamp, lowercase=False),
                body,
            )

        self.assertFalse(valid)


if __name__ == "__main__":
    unittest.main()
