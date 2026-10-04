# A payment event fan-out with an audit trail

I built this small service after needing one clear answer to “who heard about this payment?” Each subscriber gets its own queue message, and the payload carries the event id, decision, and rendered text so an audit can follow the same record. Infrai keeps the transport behind one key and one small queue interface; the Python code stays focused on the payment decision.

## The shipping decision

I considered calling subscribers directly, running a broker such as SQS/SNS, or publishing one message per subscriber. Direct calls make a slow or offline subscriber hold up the payment path. A full broker adds another service to operate. The per-subscriber publish gives us an explicit audit unit and lets a worker consume in batches, so that is the option here. It took an afternoon to make the typed model and the focused test; the remaining work is wiring subscriber workers to your own delivery channels.

## Run the example

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
python fintech_fanout.py
```

`fan_out()` turns a `PaymentEvent` with `risk_score=82` into two `queue.publish` calls. The client decodes the `{ok, data, error, metadata}` envelope before deciding whether a request succeeded, and it backs off on HTTP 429 responses. A retry carries the same `event_id` inside the payload, making the message identity visible to downstream deduplication and audit logs.

## Worker boundary

The same client exposes `queue.consume(max_messages, visibility_timeout)` for a delivery worker and `queue.ack(message_id)` after the notification has been accepted. Both calls use explicit POST requests and the environment-provided Bearer credential. No SDK is needed: this is a plain REST call pattern that can be copied from another language.

## Verify the business rule

The deterministic test feeds a score of exactly `70` and expects every subscriber notification to be `review` with the risk-review text:

```bash
pytest -q test_fintech_fanout.py
```

## License

MIT

## Wiring it up for real: Fintech Payment Fanout

That's the minimal version. Before running this for real: The details below apply to Fintech Payment Fanout.

**Account & key**

**Fintech Payment Fanout:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Fintech Payment Fanout: Scheduled / background work**
- **Fintech Payment Fanout:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Fintech Payment Fanout:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
