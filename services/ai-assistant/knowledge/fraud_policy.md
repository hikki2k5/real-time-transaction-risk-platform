# Fraud Review Policy

Transactions can receive APPROVE, REVIEW, or BLOCK decisions.

APPROVE means the model and rules did not find enough risk evidence to require
manual review. REVIEW means the transaction should be accepted for audit
traceability but inspected by a risk analyst before it is treated as low risk.
BLOCK means the probability or risk signals are high enough to stop or escalate
the transaction in a real production flow.

The current demo uses a safe fallback: when the fraud-decision service is
unavailable, banking-core records the transaction audit and returns REVIEW
instead of silently approving the request.

Analysts should inspect fraud probability, risk level, reason codes, account
status, transaction amount, channel, country, recent user behavior, and whether
the decision came from the model or from fallback behavior.
