type Config = { authBaseUrl: string; assistantBaseUrl: string; operatorToken: string };
type Fetcher = typeof fetch;

const response = (status: number, message: string) => Response.json({ message }, {
  status, headers: { "Cache-Control": "no-store" }
});
const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

function endpoint(base: string, path: string) {
  const url = new URL(base);
  if (!["https:", "http:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error("Invalid service URL");
  }
  return base.replace(/\/+$/, "") + path;
}

export async function proxyAssistant(request: Request, config: Config, fetcher: Fetcher = fetch) {
  const authorization = request.headers.get("authorization") || "";
  if (!authorization.startsWith("Bearer ") || authorization.length > 8192 || authorization.length <= 7) {
    return response(401, "Sign in to use the assistant.");
  }
  if (!config.authBaseUrl || !config.assistantBaseUrl || !config.operatorToken) {
    return response(503, "The assistant is not available yet.");
  }
  let authUrl: string, assistantUrl: string;
  try {
    authUrl = endpoint(config.authBaseUrl, "/v1/auth/me");
    assistantUrl = endpoint(config.assistantBaseUrl, "/v1/assistant/query");
  } catch {
    return response(503, "The assistant service configuration is unavailable.");
  }
  let payload: unknown;
  try {
    if (Number(request.headers.get("content-length")) > 16000) return response(413, "Your message is too long.");
    const text = await request.text();
    if (text.length > 16000) return response(413, "Your message is too long.");
    payload = JSON.parse(text);
  } catch {
    return response(400, "Enter a valid question.");
  }
  if (!record(payload) || typeof payload.question !== "string" ||
      payload.question.trim().length < 3 || payload.question.length > 4000 ||
      (payload.transaction_id !== undefined && (typeof payload.transaction_id !== "string" ||
       payload.transaction_id.length > 128 || !payload.transaction_id.trim()))) {
    return response(400, "Enter a question between 3 and 4,000 characters.");
  }
  const question = payload.question.trim();
  const transactionId = typeof payload.transaction_id === "string" ? payload.transaction_id.trim() : undefined;
  let userId: string;
  const authStartedAt = Date.now();
  try {
    const identity = await fetcher(authUrl, {
      headers: { Authorization: authorization }, cache: "no-store", redirect: "error",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(10000)])
    });
    if (identity.status === 401 || identity.status === 403) return response(401, "Your session expired. Sign in again.");
    if (!identity.ok) {
      console.warn("assistant_auth_http_error", { host: new URL(authUrl).host, status: identity.status });
      return response(503, "Sign-in verification is temporarily unavailable.");
    }
    const user: unknown = await identity.json();
    if (!record(user) || typeof user.userId !== "string" || !user.userId || user.userId.length > 128) {
      return response(401, "Your session could not be verified. Sign in again.");
    }
    userId = user.userId;
  } catch (error) {
    const cause = error instanceof Error && "cause" in error ? error.cause : undefined;
    const errorCode = record(cause) && typeof cause.code === "string" ? cause.code : undefined;
    const timedOut = error instanceof Error && error.name === "TimeoutError";
    console.warn("assistant_auth_request_failed", {
      host: new URL(authUrl).host,
      elapsedMs: Date.now() - authStartedAt,
      errorType: error instanceof Error ? error.name : "UnknownError",
      errorCode
    });
    if (timedOut) return response(504, "Sign-in verification timed out. Try again.");
    return response(503, "Sign-in verification is temporarily unavailable. Try again.");
  }
  try {
    const upstream = await fetcher(assistantUrl, {
      method: "POST", cache: "no-store", redirect: "error",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${config.operatorToken}` },
      body: JSON.stringify({ question, transaction_id: transactionId, user_id: userId }),
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(80000)])
    });
    if (!upstream.ok) {
      const status = upstream.status === 429 ? 429 : upstream.status === 502 ? 502 : 503;
      return response(status, status === 429 ? "The assistant is busy. Try again shortly." :
        "The assistant could not answer right now. Try again shortly.");
    }
    const body: unknown = await upstream.json();
    if (!record(body) || typeof body.answer !== "string" || !body.answer.trim() || body.answer.length > 24000) {
      return response(502, "The assistant returned an incomplete answer. Try again.");
    }
    const citations = Array.isArray(body.citations) ? body.citations.filter(record).slice(0, 20).map(item => ({
      doc_id: String(item.doc_id || "").slice(0, 256), title: String(item.title || "Source").slice(0, 256),
      snippet: String(item.snippet || "").slice(0, 1000), score: typeof item.score === "number" ? item.score : 0
    })) : [];
    return Response.json({ answer: body.answer, citations,
      tool_calls: Array.isArray(body.tool_calls) ? body.tool_calls.filter(record).slice(0, 20).map(item => ({
        name: String(item.name || "").slice(0, 128), result_summary: String(item.result_summary || "").slice(0, 1000)
      })) : []
    }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const timedOut = error instanceof Error && ["TimeoutError", "AbortError"].includes(error.name);
    return response(timedOut ? 504 : 502, timedOut ? "The assistant took too long. Try again." :
      "The assistant is temporarily unreachable. Try again.");
  }
}
