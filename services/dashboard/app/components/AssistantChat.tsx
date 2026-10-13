"use client";

import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { ChevronDown, ChevronRight, FileText, LoaderCircle, RotateCcw, Send, Square, Trash2 } from "lucide-react";
import styles from "./AssistantChat.module.css";

type AssistantChatProps = {
  accessToken: string;
  transactionId?: string;
  transactions: { transactionId: string; decision: string; amount: number; currency: string }[];
};

type Citation = { doc_id: string; title: string; snippet: string; score: number };
type Message = {
  id: number;
  role: "user" | "assistant";
  text: string;
  question: string;
  transactionId?: string;
  status: "pending" | "complete" | "error" | "stopped";
  citations: Citation[];
};
type Request = { controller: AbortController; timer?: ReturnType<typeof setTimeout> };

const suggestions = [
  "What can cause a transaction to be blocked?",
  "What happens when a payment needs review?",
  "How do transaction risk checks work?"
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isCitation(value: unknown): value is Citation {
  return isRecord(value) && typeof value.doc_id === "string" && typeof value.title === "string"
    && typeof value.snippet === "string" && typeof value.score === "number" && Number.isFinite(value.score);
}

function shortTransactionId(value: string) {
  return value.length > 16 ? `${value.slice(0, 8)}...${value.slice(-5)}` : value;
}

export default function AssistantChat(props: AssistantChatProps) {
  // A new credential starts an isolated session, including draft and request state.
  return <ChatSession key={props.accessToken} {...props} />;
}

function ChatSession({ accessToken, transactionId, transactions }: AssistantChatProps) {
  const headingId = useId();
  const selectId = useId();
  const questionId = useId();
  const [selected, setSelected] = useState(transactionId || "");
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const active = useRef<Request | null>(null);
  const sequence = useRef(0);
  const thread = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setSelected(transactionId || "");
  }, [transactionId]);

  useEffect(() => () => {
    const request = active.current;
    active.current = null;
    if (request) {
      clearTimeout(request.timer);
      request.controller.abort();
    }
  }, []);

  useEffect(() => {
    if (thread.current) thread.current.scrollTop = thread.current.scrollHeight;
  }, [messages]);

  const options = transactions.filter((item, index, items) => item.transactionId
    && items.findIndex((other) => other.transactionId === item.transactionId) === index);
  const extraId = selected && !options.some((item) => item.transactionId === selected) ? selected : "";

  function cancel() {
    const request = active.current;
    active.current = null;
    if (request) {
      clearTimeout(request.timer);
      request.controller.abort();
    }
    setBusy(false);
  }

  function stop() {
    cancel();
    setMessages((current) => current.map((message) => message.status === "pending"
      ? { ...message, status: "stopped", text: "Request stopped." } : message));
    textarea.current?.focus();
  }

  function clear() {
    if (!window.confirm("Clear this chat?")) return;
    cancel();
    setMessages([]);
    setDraft("");
    textarea.current?.focus();
  }

  async function ask(question: string, context?: string, retryId?: number) {
    question = question.trim();
    if (question.length < 3 || question.length > 4000 || !accessToken || active.current) return;
    const id = retryId ?? ++sequence.current;
    const pending: Message = {
      id, role: "assistant", text: "", question, transactionId: context,
      status: "pending", citations: []
    };
    if (retryId !== undefined) {
      setMessages((current) => current.map((message) => message.id === id ? pending : message));
    } else {
      const user: Message = { ...pending, id: ++sequence.current, role: "user", text: question, status: "complete" };
      setMessages((current) => [...current, user, pending]);
      setDraft("");
    }
    setBusy(true);
    const request: Request = { controller: new AbortController() };
    active.current = request;
    let timedOut = false;
    request.timer = setTimeout(() => {
      timedOut = true;
      request.controller.abort();
    }, 100_000);

    function update(changes: Partial<Message>) {
      if (active.current !== request) return;
      setMessages((current) => current.map((message) => message.id === id ? { ...message, ...changes } : message));
    }

    try {
      const response = await fetch("/api/assistant", {
        method: "POST",
        headers: { "Authorization": `Bearer ${accessToken}`, "Content-Type": "application/json" },
        body: JSON.stringify({ question, ...(context ? { transaction_id: context } : {}) }),
        signal: request.controller.signal
      });
      if (!response.ok) {
        const errorBody: unknown = await response.json().catch(() => null);
        const message = isRecord(errorBody) && typeof errorBody.message === "string"
          ? errorBody.message.trim() : "";
        throw new Error(message || (response.status === 401 || response.status === 403
          ? "Access denied. Sign in again to continue."
          : response.status === 429 ? "Too many requests. Try again shortly."
            : "The assistant could not complete this request. Please retry."));
      }
      const body: unknown = await response.json();
      if (!isRecord(body) || typeof body.answer !== "string" || !body.answer.trim()) {
        throw new Error("The assistant returned an invalid response. Please retry.");
      }
      update({ text: body.answer, citations: Array.isArray(body.citations) ? body.citations.filter(isCitation) : [], status: "complete" });
    } catch (error) {
      update({ status: "error", text: timedOut
        ? "The request timed out after 100 seconds. Please retry."
        : error instanceof Error && error.name !== "TypeError" ? error.message
          : "Could not reach the assistant. Check your connection and retry." });
    } finally {
      clearTimeout(request.timer);
      if (active.current === request) {
        active.current = null;
        setBusy(false);
      }
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(draft.trim(), selected || undefined);
  }

  return (
    <section className={styles.assistant} aria-labelledby={headingId}>
      <header className={styles.header}>
        <h2 id={headingId}>AI Assistant</h2>
        <button type="button" className={styles.iconButton} onClick={clear}
          disabled={!messages.length && !draft} title="Clear chat" aria-label="Clear chat">
          <Trash2 size={18} aria-hidden="true" />
        </button>
      </header>
      <div className={styles.context}>
        <label htmlFor={selectId}>Transaction</label>
        <select id={selectId} value={selected} onChange={(event) => setSelected(event.target.value)} disabled={busy}>
          <option value="">General question</option>
          {extraId ? <option value={extraId} title={extraId}>Latest: {shortTransactionId(extraId)}</option> : null}
          {options.map((item, index) => (
            <option key={item.transactionId} value={item.transactionId} title={item.transactionId}>
              {item.decision} - {item.currency} {Number.isFinite(item.amount) ? item.amount.toFixed(2) : "--"} - {shortTransactionId(item.transactionId)}
              {item.transactionId === transactionId || (!transactionId && index === 0) ? " (Latest)" : ""}
            </option>
          ))}
        </select>
      </div>
      <div ref={thread} className={styles.thread} role="log" aria-label="Assistant chat" aria-live="polite" aria-relevant="additions text" tabIndex={0}>
        {messages.length === 0 ? (
          <div className={styles.suggestions}>
            {suggestions.map((question) => (
              <button type="button" key={question} className={styles.suggestion} disabled={!accessToken}
                onClick={() => { setDraft(question); textarea.current?.focus(); }}>
                <span>{question}</span><ChevronRight size={16} aria-hidden="true" />
              </button>
            ))}
          </div>
        ) : messages.map((message) => (
          <article key={message.id} className={`${styles.message} ${message.role === "user" ? styles.userMessage : ""}`}>
            <div className={styles.messageHeading}>
              <strong>{message.role === "user" ? "You" : "AI Assistant"}</strong>
              {message.role === "user" && message.transactionId ? <span>{message.transactionId}</span> : null}
            </div>
            {message.status === "pending" ? (
              <p className={styles.loading}><LoaderCircle size={16} className={styles.spinner} aria-hidden="true" />Thinking...</p>
            ) : <p className={`${styles.answer} ${message.status === "error" ? styles.error : ""}`}>{message.text}</p>}
            {message.status === "error" || message.status === "stopped" ? (
              <button type="button" className={styles.retry} disabled={busy || !accessToken}
                onClick={() => { void ask(message.question, message.transactionId, message.id); }}>
                <RotateCcw size={15} aria-hidden="true" />Retry
              </button>
            ) : null}
            {message.citations.length > 0 ? (
              <details className={styles.sources}>
                <summary><FileText size={15} aria-hidden="true" />Sources ({message.citations.length})<ChevronDown size={15} className={styles.chevron} aria-hidden="true" /></summary>
                <ol className={styles.citationList}>
                  {message.citations.map((citation, index) => (
                    <li key={`${citation.doc_id}-${index}`}>
                      <details className={styles.citation}>
                        <summary>{citation.title || citation.doc_id}<ChevronDown size={14} className={styles.chevron} aria-hidden="true" /></summary>
                        <p className={styles.answer}>{citation.snippet}</p>
                        <div className={styles.citationMeta}><span>{citation.doc_id}</span></div>
                      </details>
                    </li>
                  ))}
                </ol>
              </details>
            ) : null}
          </article>
        ))}
      </div>
      <form className={styles.composer} onSubmit={submit}>
        <label htmlFor={questionId}>Question</label>
        <div className={styles.inputRow}>
          <textarea ref={textarea} id={questionId} rows={3} value={draft} maxLength={4000}
            onChange={(event) => setDraft(event.target.value)} disabled={!accessToken}
            placeholder="Ask a question" />
          {busy ? (
            <button type="button" className={styles.stopButton} onClick={stop} title="Stop request" aria-label="Stop request">
              <Square size={18} aria-hidden="true" />
            </button>
          ) : (
            <button type="submit" className={styles.sendButton} disabled={!accessToken || draft.trim().length < 3 || draft.trim().length > 4000}
              title="Send question" aria-label="Send question"><Send size={18} aria-hidden="true" /></button>
          )}
        </div>
        {!accessToken ? <p className={styles.error} role="status">Sign in to ask a question.</p> : null}
      </form>
    </section>
  );
}
