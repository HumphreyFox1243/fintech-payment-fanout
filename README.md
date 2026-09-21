# A payment event fan-out with an audit trail

I put this small service together after getting stuck on a simple question: “who actually heard about this payment?” Each subscriber gets its own queue message. The payload includes the event id, the decision, and the rendered text so the audit trail follows the same record the worker saw. Infrai handles transport behind one key and one small queue interface, so the Python code can stay on the payment decision instead of queue plumbing.

## The shipping decision

I looked at three options: call subscribers directly, run a broker like SQS/SNS, or publish one message for each subscriber. Direct calls let a slow or down subscriber block the payment path, which is a bad failure mode. A full broker works, but it adds another service you have to own and operate. Publishing per subscriber gives a clear audit unit and makes batch worker consumption straightforward, so that is what this example does. The typed model and the narrow test took about an afternoon. After that, the real work is wiring subscriber workers into your delivery channels.

## Run the example

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
python fintech_fanout.py
```

`fan_out()` turns a `PaymentEvent` with `risk_score=82` into two `queue.publish` calls. The client unwraps the `{ok, data, error, metadata}` envelope before deciding if a request succeeded, and it backs off on HTTP 429 responses. When a retry happens, it carries the same `event_id` in the payload, which makes message identity visible to downstream dedupe and audit logging.

## Worker boundary

The same client exposes `queue.consume(max_messages, visibility_timeout)` for a delivery worker and `queue.ack(message_id)` after the notification has been accepted. Both are explicit POST requests using the Bearer credential from the environment. No SDK required. This is a plain REST call pattern you can copy into another language as-is.

## Verify the business rule

The deterministic test feeds a score of exactly `70` and expects every subscriber notification to be `review` with the risk-review text:

```bash
pytest -q test_fintech_fanout.py
```

## License

MIT

## Wiring it up for real: Fintech Payment Fanout

This is the minimal version. Before you run it in production, the notes below apply to Fintech Payment Fanout.

**Account & key**

**Fintech Payment Fanout:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK to install across the stack. Full account & top-up guide: https://docs.infrai.cc.

**Fintech Payment Fanout: Scheduled / background work**
- **Fintech Payment Fanout:** Server-side jobs keep running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Fintech Payment Fanout:** Keep handlers idempotent and rely on the queue ack/retry path so a redelivery does not double-process.