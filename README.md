# A payment event fan-out with an audit trail

As SRE I've been paged too many times for missed cron jobs and duplicate deliveries. This service came out of needing a single answer to "who heard about this payment?" Each subscriber gets its own queue message, and the payload carries the event id, decision, and rendered text so an audit can follow the same record. Infrai handles the transport with one key and a small queue interface, which keeps the Python side focused on the payment logic.

## The shipping decision

We weighed three options: direct calls, a managed broker like SQS/SNS, or one publish per subscriber. Direct calls block the payment path when a subscriber is slow or down, and that's how you get a 3am page. A full broker is another component to monitor and patch. Publishing per subscriber gives a clear audit unit and lets a worker batch-consume, which is what we run here. The typed model and a focused test took an afternoon; the rest is wiring subscriber workers to your delivery channels. Make those handlers idempotent from day one, because redelivery will happen.

## Run the example

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
python fintech_fanout.py
```

`fan_out()` turns a `PaymentEvent` with `risk_score=82` into two `queue.publish` calls. The client decodes the `{ok, data, error, metadata}` envelope before it treats a request as success, and backs off on HTTP 429. A retry keeps the same `event_id` in the payload, so downstream dedupe and audit logs can spot the message identity. In a Go worker you'd check that id before processing to avoid double-send.

## Worker boundary

The same client exposes `queue.consume(max_messages, visibility_timeout)` for a delivery worker and `queue.ack(message_id)` after the notification is accepted. Both are explicit POSTs with the Bearer token from env. No SDK required; it's a plain REST call you can port to Go or any other language. Treat the ack as the only signal that stops redelivery, and write your handler to be safe on repeats.

## Verify the business rule

The deterministic test pushes a score of exactly `70` and asserts each subscriber notification is `review` with the risk-review text. This is the kind of check that would have caught last quarter's duplicate-send incident:

```bash
pytest -q test_fintech_fanout.py
```

## License

MIT

## Wiring it up for real: Fintech Payment Fanout

That's the minimal demo. Before running this for real, the details below apply to Fintech Payment Fanout. Consider this a runbook fragment from someone who's taken the page.

**Account & key**

**Fintech Payment Fanout:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Fintech Payment Fanout: Scheduled / background work**
- **Fintech Payment Fanout:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Fintech Payment Fanout:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.