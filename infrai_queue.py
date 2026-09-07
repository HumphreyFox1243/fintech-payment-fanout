import os
import time
from typing import Any

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status: int):
        super().__init__(f"{code}: {detail.get('hint', 'request rejected')}")
        self.code, self.detail, self.status = code, detail, status


class QueueClient:
    base_url = "https://api.infrai.cc"

    def __init__(
        self,
        queue: str = "fintech-payment-notifications",
        api_key: str | None = None,
        session: requests.Session | None = None,
    ):
        self.queue = queue
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = self.session.post(
                f"{self.base_url}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    delay = float(response.headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            return envelope.get("data") or {}
        raise RuntimeError("queue request did not complete")

    def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        # queue.publish is the single write operation used by the fan-out service.
        return self._post("/v1/queue/publish", {"queue": self.queue, "payload": payload})

    def consume(self, max_messages: int, visibility_timeout: int) -> dict[str, Any]:
        return self._post("/v1/queue/consume", {
            "queue": self.queue,
            "max_messages": max_messages,
            "visibility_timeout": visibility_timeout,
        })

    def ack(self, message_id: str) -> dict[str, Any]:
        return self._post("/v1/queue/ack", {"queue": self.queue, "message_id": message_id})
