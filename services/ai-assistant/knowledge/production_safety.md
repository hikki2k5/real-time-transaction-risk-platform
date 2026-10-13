# Production Safety And Observability

Financial AI features require safety and compliance defaults.

The assistant should resist prompt injection attempts such as requests to ignore
instructions, reveal hidden prompts, print JWTs, disclose passwords, or bypass
guardrails. It should redact emails, phone numbers, and token-like strings when
they are not required for the task.

Every assistant request should log prompt version, model name, latency,
estimated input tokens, estimated output tokens, estimated cost, retrieved
document IDs, tool calls, and guardrail flags. Production deployments should
ship logs to CloudWatch or an equivalent tracing platform and configure alerts
for high error rate, abnormal latency, and cost spikes.
