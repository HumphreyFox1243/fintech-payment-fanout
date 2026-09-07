from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from infrai_queue import QueueClient


@dataclass(frozen=True)
class PaymentEvent:
    event_id: str
    account_id: str
    amount: Decimal
    currency: str
    risk_score: int


@dataclass(frozen=True)
class Notification:
    subscriber: str
    event_id: str
    kind: str
    body: str


def notifications_for(event: PaymentEvent, subscribers: list[str]) -> list[Notification]:
    kind = "review" if event.risk_score >= 70 else "payment"
    body = f"{event.currency} {event.amount} payment {event.event_id}"
    if kind == "review":
        body += " needs risk review"
    return [Notification(s, event.event_id, kind, body) for s in subscribers]


def fan_out(event: PaymentEvent, subscribers: list[str], client: QueueClient) -> list[dict[str, Any]]:
    receipts = []
    for notification in notifications_for(event, subscribers):
        receipts.append(client.publish({
            "event_id": notification.event_id,
            "subscriber": notification.subscriber,
            "kind": notification.kind,
            "body": notification.body,
        }))
    return receipts


if __name__ == "__main__":
    event = PaymentEvent("pay_2026_001", "acct_42", Decimal("125.50"), "USD", 82)
    print(fan_out(event, ["email:chenhua@changba.com"], QueueClient()))
