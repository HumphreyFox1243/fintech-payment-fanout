from decimal import Decimal

from fintech_fanout import PaymentEvent, notifications_for


def test_high_risk_payment_is_marked_for_review_for_each_subscriber():
    event = PaymentEvent("evt_1", "acct_7", Decimal("9.99"), "USD", 70)
    result = notifications_for(event, ["email:a", "webhook:risk"])
    assert [n.kind for n in result] == ["review", "review"]
    assert all("needs risk review" in n.body for n in result)
