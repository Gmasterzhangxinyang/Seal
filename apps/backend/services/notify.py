"""
MEC202 notification helpers.

Sends notifications to Wene (via webhook → Feishu DM) when certain events occur,
such as a file entering the manual review queue.
"""

import json
import logging
import threading
from urllib.request import Request, urlopen
from urllib.error import URLError

log = logging.getLogger("mec202.notify")

# Webhook endpoint — the review_webhook.py server running on Hermes machine.
# Default to WireGuard address so robot machine works out of the box.
# Local dev without WG: override via MEC202_WEBHOOK_URL=http://127.0.0.1:8002/review
import os

_WEBHOOK_URL = os.environ.get(
    "MEC202_WEBHOOK_URL",
    "http://10.66.66.1:8002/review",
)


def _post_async(url: str, payload: dict):
    """Fire-and-forget POST in a daemon thread; never blocks the caller."""

    def _post():
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    log.info("Review notification sent: %s", payload.get("reason", ""))
                else:
                    log.warning("Webhook returned %d", resp.status)
        except URLError as e:
            log.error("Webhook unreachable: %s", e)
        except Exception:
            log.exception("Unexpected error sending webhook")

    t = threading.Thread(target=_post, daemon=True)
    t.start()


def notify_review_queue(
    operator_id: str,
    doc_type: str = "文件",
    reason: str = "自动核验不确定",
    warnings: list | None = None,
    application_id: str = "",
):
    """Notify Wene that a file has entered the manual review queue.

    Fire-and-forget — will not raise exceptions or block the caller.
    """
    payload = {
        "operator_id": operator_id,
        "doc_type": doc_type,
        "reason": reason,
        "warnings": warnings or [],
        "application_id": application_id,
    }
    _post_async(_WEBHOOK_URL, payload)
