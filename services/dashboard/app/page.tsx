"use client";

import { FormEvent, useEffect, useState } from "react";

type ApiConfig = {
  authBaseUrl: string;
  bankingBaseUrl: string;
  fraudBaseUrl: string;
};

type AuthState = {
  accessToken: string;
  email: string;
  role: string;
  userId: string;
};

type TransactionResult = {
  transaction_id?: string;
  event_id?: string;
  decision?: string;
  fraud_probability?: number;
  risk_level?: string;
  reason_codes?: string[];
  message?: string;
};

type Account = {
  accountId: string;
  userId: string;
  status: string;
  currency: string;
};

type TransactionHistoryItem = {
  transactionId: string;
  accountId: string;
  amount: number;
  currency: string;
  transactionType: string;
  decision: string;
  riskLevel: string;
  createdAt: string;
};

const defaultConfig: ApiConfig = {
  authBaseUrl: process.env.NEXT_PUBLIC_AUTH_API_BASE_URL || "http://localhost:8085",
  bankingBaseUrl: process.env.NEXT_PUBLIC_BANKING_API_BASE_URL || "http://localhost:8084",
  fraudBaseUrl: process.env.NEXT_PUBLIC_FRAUD_API_BASE_URL || "http://localhost:8000"
};

const initialTransaction = {
  account_id: "acct_001",
  amount: "125.50",
  currency: "AUD",
  payee_name: "Grocery Store",
  payment_reference: "Weekly groceries",
  transaction_type: "CARD_PAYMENT",
  country: "AU",
  city: "Sydney"
};

export default function DashboardPage() {
  const [mounted, setMounted] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [config, setConfig] = useState<ApiConfig>(defaultConfig);
  const [auth, setAuth] = useState<AuthState>({ accessToken: "", email: "", role: "", userId: "" });
  const [authForm, setAuthForm] = useState({ email: "demo@example.com", password: "password123", fullName: "Demo User" });
  const [transaction, setTransaction] = useState(initialTransaction);
  const [result, setResult] = useState<TransactionResult | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [history, setHistory] = useState<TransactionHistoryItem[]>([]);
  const [reviewing, setReviewing] = useState(false);
  const [busy, setBusy] = useState("");
  const accountOptions = accounts.length > 0 ? accounts.map((account) => account.accountId) : ["acct_001", "acct_savings"];

  useEffect(() => {
    setMounted(true);
    const savedConfig = localStorage.getItem("risk-dashboard-config");
    const savedAuth = localStorage.getItem("risk-dashboard-auth");
    if (savedConfig) setConfig(JSON.parse(savedConfig));
    if (savedAuth) setAuth(JSON.parse(savedAuth));
  }, []);

  useEffect(() => {
    localStorage.setItem("risk-dashboard-config", JSON.stringify(config));
  }, [config]);

  useEffect(() => {
    localStorage.setItem("risk-dashboard-auth", JSON.stringify(auth));
  }, [auth]);

  useEffect(() => {
    if (!auth.accessToken) return;
    void loadCustomerData(auth.accessToken);
  }, [auth.accessToken]);

  async function register() {
    await authRequest("Register", `${config.authBaseUrl}/v1/auth/register`, {
      email: authForm.email,
      password: authForm.password,
      fullName: authForm.fullName
    });
  }

  async function login(event: FormEvent) {
    event.preventDefault();
    await authRequest("Login", `${config.authBaseUrl}/v1/auth/login`, {
      email: authForm.email,
      password: authForm.password
    });
  }

  async function authRequest(title: string, url: string, payload: unknown) {
    setBusy(title);
    const result = await postJson(url, payload);
    if (result.ok && isRecord(result.body) && typeof result.body.access_token === "string") {
      setAuth({
        accessToken: result.body.access_token,
        email: String(result.body.email || authForm.email),
        role: String(result.body.role || ""),
        userId: String(result.body.userId || "")
      });
      setResult(null);
    } else if (isRecord(result.body)) {
      setResult({ message: String(result.body.message || "Authentication failed") });
    }
    setBusy("");
  }

  async function loadCustomerData(token: string) {
    const [accountsResult, historyResult] = await Promise.all([
      requestJson(`${config.bankingBaseUrl}/v1/accounts`, { method: "GET" }, token),
      requestJson(`${config.bankingBaseUrl}/v1/transactions?limit=8`, { method: "GET" }, token)
    ]);

    if (Array.isArray(accountsResult.body)) {
      const nextAccounts = accountsResult.body
        .filter(isRecord)
        .map((item) => ({
          accountId: String(item.accountId || item.account_id || ""),
          userId: String(item.userId || item.user_id || ""),
          status: String(item.status || ""),
          currency: String(item.currency || "")
        }))
        .filter((account) => account.accountId);
      setAccounts(nextAccounts);
      if (nextAccounts.length > 0 && !nextAccounts.some((account) => account.accountId === transaction.account_id)) {
        setTransaction((current) => ({ ...current, account_id: nextAccounts[0].accountId }));
      }
    }

    if (Array.isArray(historyResult.body)) {
      setHistory(historyResult.body.filter(isRecord).map(normalizeHistoryItem));
    }
  }

  async function submitTransaction() {
    setBusy("transaction");
    const payload = {
      ...transaction,
      user_id: auth.userId || "user_001",
      amount: Number(transaction.amount),
      merchant_category: `${transaction.payee_name}${transaction.payment_reference ? ` - ${transaction.payment_reference}` : ""}`,
      channel: "WEB",
      status: "SUBMITTED",
      event_timestamp: new Date().toISOString()
    };
    const result = await postJson(`${config.bankingBaseUrl}/internal/transactions`, payload, {
      token: auth.accessToken,
      idempotencyKey: `ui-${crypto.randomUUID()}`
    });
    setResult(normalizeTransactionResult(result.body));
    if (result.ok) {
      setReviewing(false);
      await loadCustomerData(auth.accessToken);
    }
    setBusy("");
  }

  function clearSession() {
    setAuth({ accessToken: "", email: "", role: "", userId: "" });
    setAccounts([]);
    setHistory([]);
    setResult(null);
    localStorage.removeItem("risk-dashboard-auth");
  }

  if (!mounted) {
    return <main className="authShell" />;
  }

  if (!auth.accessToken) {
    return (
      <main className="authShell">
        <section className="authHero">
          <p className="eyebrow">Secure Banking</p>
          <h1>Sign in to continue</h1>
          <p className="lead">
            Manage transaction requests with real-time risk checks before the payment is accepted.
          </p>
          <div className="authMeta">
            <span>Secure access</span>
            <span>Transaction review</span>
            <span>Instant decision</span>
          </div>
        </section>

        <section className="authGrid">
          <section className="panel authCard">
            <div className="panelHeader">
              <h2>{authMode === "login" ? "Login" : "Create account"}</h2>
            </div>
            <div className="authTabs">
              <button className={authMode === "login" ? "active" : "secondary"} type="button" onClick={() => setAuthMode("login")}>
                Login
              </button>
              <button className={authMode === "register" ? "active" : "secondary"} type="button" onClick={() => setAuthMode("register")}>
                Register
              </button>
            </div>
            <form className="stack" onSubmit={authMode === "login" ? login : (event) => { event.preventDefault(); void register(); }}>
              <Field label="Email" value={authForm.email} onChange={(value) => setAuthForm({ ...authForm, email: value })} />
              <Field label="Password" type="password" value={authForm.password} onChange={(value) => setAuthForm({ ...authForm, password: value })} />
              {authMode === "register" ? (
                <Field label="Full name" value={authForm.fullName} onChange={(value) => setAuthForm({ ...authForm, fullName: value })} />
              ) : null}
              <div className="buttonRow">
                <button type="submit" disabled={busy === "Login" || busy === "Register"}>
                  {authMode === "login" ? "Login" : "Register"}
                </button>
              </div>
            </form>
            <p className="muted smallText">
              {authMode === "login"
                ? "Use your registered email and password to access transaction services."
                : "Create a local demo account to receive a secure access token."}
            </p>
            {result?.message ? <p className="errorText">{result.message}</p> : null}
          </section>
        </section>
      </main>
    );
  }

  return (
    <main>
      <header className="topbar">
        <div>
          <p className="eyebrow">Secure Banking</p>
          <h1>{reviewing ? "Review Transaction" : "New Transaction"}</h1>
        </div>
        <div className="tokenBox">
          <span className={auth.accessToken ? "dot ok" : "dot"} />
          <span>{auth.email || "Anonymous"}</span>
          <button className="miniButton" onClick={clearSession}>Sign out</button>
        </div>
      </header>

      <section className="customerLayout">
        <section className="panel transactionPanel">
          <div className="panelHeader">
            <h2>Payment Details</h2>
          </div>
          <form className="formGrid" onSubmit={(event) => { event.preventDefault(); setReviewing(true); setResult(null); }}>
            <AccountSelect accounts={accounts} fallbackOptions={accountOptions} value={transaction.account_id} onChange={(value) => setTransaction({ ...transaction, account_id: value })} />
            <Field label="Amount" type="number" value={transaction.amount} onChange={(value) => setTransaction({ ...transaction, amount: value })} />
            <SelectField label="Currency" value={transaction.currency} options={["AUD", "VND", "USD"]} onChange={(value) => setTransaction({ ...transaction, currency: value })} />
            <Field label="Payee or merchant" value={transaction.payee_name} onChange={(value) => setTransaction({ ...transaction, payee_name: value })} />
            <Field label="Payment reference" value={transaction.payment_reference} onChange={(value) => setTransaction({ ...transaction, payment_reference: value })} />
            <SelectField label="Transaction type" value={transaction.transaction_type} options={["CARD_PAYMENT", "TRANSFER", "ATM_WITHDRAWAL", "LOAN_REPAYMENT"]} onChange={(value) => setTransaction({ ...transaction, transaction_type: value })} />
            <Field label="Merchant country" value={transaction.country} onChange={(value) => setTransaction({ ...transaction, country: value })} />
            <Field label="City" value={transaction.city} onChange={(value) => setTransaction({ ...transaction, city: value })} />
            <div className="formActions">
              <button type="submit" disabled={busy === "transaction"}>
                Review Transaction
              </button>
            </div>
          </form>
          {reviewing ? (
            <ReviewPanel
              transaction={transaction}
              onBack={() => setReviewing(false)}
              onConfirm={submitTransaction}
              busy={busy === "transaction"}
            />
          ) : null}
        </section>

        <aside className="sideColumn">
          {result ? <DecisionPanel result={result} /> : <EmptyDecision />}
          <TransactionHistory items={history} />
        </aside>
      </section>
    </main>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text"
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label>
      <span>{label}</span>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} required />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} required>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function AccountSelect({
  accounts,
  fallbackOptions,
  value,
  onChange
}: {
  accounts: Account[];
  fallbackOptions: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      <span>From account</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} required>
        {accounts.length > 0
          ? accounts.map((account) => (
              <option key={account.accountId} value={account.accountId}>
                {account.accountId} - {account.currency} - {account.status}
              </option>
            ))
          : fallbackOptions.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function ReviewPanel({
  transaction,
  onBack,
  onConfirm,
  busy
}: {
  transaction: typeof initialTransaction;
  onBack: () => void;
  onConfirm: () => Promise<void>;
  busy: boolean;
}) {
  return (
    <section className="reviewPanel">
      <div>
        <h2>Review before submitting</h2>
        <p>Please confirm the transaction details. Once submitted, the payment will be checked in real time.</p>
      </div>
      <dl className="reviewGrid">
        <div>
          <dt>From account</dt>
          <dd>{transaction.account_id}</dd>
        </div>
        <div>
          <dt>Amount</dt>
          <dd>{transaction.currency} {Number(transaction.amount || 0).toFixed(2)}</dd>
        </div>
        <div>
          <dt>Payee</dt>
          <dd>{transaction.payee_name}</dd>
        </div>
        <div>
          <dt>Reference</dt>
          <dd>{transaction.payment_reference || "No reference"}</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{formatTransactionType(transaction.transaction_type)}</dd>
        </div>
        <div>
          <dt>Location</dt>
          <dd>{transaction.city}, {transaction.country}</dd>
        </div>
      </dl>
      <div className="buttonRow">
        <button type="button" onClick={() => { void onConfirm(); }} disabled={busy}>
          {busy ? "Checking..." : "Confirm and Submit"}
        </button>
        <button type="button" className="secondary" onClick={onBack} disabled={busy}>
          Edit Details
        </button>
      </div>
    </section>
  );
}

async function postJson(url: string, payload: unknown, options: { token?: string; idempotencyKey?: string } = {}) {
  return requestJson(
    url,
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    options.token,
    options.idempotencyKey
  );
}

async function requestJson(url: string, init: RequestInit, token?: string, idempotencyKey?: string) {
  try {
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);

    const response = await fetch(url, { ...init, headers });
    const text = await response.text();
    const body = text ? JSON.parse(text) : { status: response.status };
    return { ok: response.ok, status: response.status, body };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      body: {
        message: error instanceof Error ? error.message : "Request failed"
      }
    };
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeTransactionResult(value: unknown): TransactionResult {
  if (!isRecord(value)) return { message: "Transaction request failed" };
  return {
    transaction_id: typeof value.transaction_id === "string" ? value.transaction_id : undefined,
    event_id: typeof value.event_id === "string" ? value.event_id : undefined,
    decision: typeof value.decision === "string" ? value.decision : undefined,
    fraud_probability: typeof value.fraud_probability === "number" ? value.fraud_probability : undefined,
    risk_level: typeof value.risk_level === "string" ? value.risk_level : undefined,
    reason_codes: Array.isArray(value.reason_codes) ? value.reason_codes.map(String) : undefined,
    message: typeof value.message === "string" ? value.message : undefined
  };
}

function normalizeHistoryItem(value: Record<string, unknown>): TransactionHistoryItem {
  return {
    transactionId: String(value.transactionId || value.transaction_id || ""),
    accountId: String(value.accountId || value.account_id || ""),
    amount: Number(value.amount || 0),
    currency: String(value.currency || ""),
    transactionType: String(value.transactionType || value.transaction_type || ""),
    decision: String(value.decision || ""),
    riskLevel: String(value.riskLevel || value.risk_level || ""),
    createdAt: String(value.createdAt || value.created_at || "")
  };
}

function EmptyDecision() {
  return (
    <section className="emptyDecision">
      <h2>Ready to Check</h2>
      <p>Submit a transaction and the result will appear here.</p>
    </section>
  );
}

function DecisionPanel({ result }: { result: TransactionResult }) {
  const decision = result.decision || "ERROR";
  const normalized = decision.toUpperCase();
  const approved = normalized === "APPROVE" || normalized === "APPROVED";
  const review = normalized === "REVIEW";
  const blocked = normalized === "BLOCK";
  const title = approved ? "Approved" : review ? "Review Needed" : blocked ? "Blocked" : "Unable to Process";
  const subtitle = approved
    ? "Your transaction has been accepted."
    : review
      ? "Your transaction was received but needs additional review."
      : blocked
        ? "This transaction was blocked for your protection."
        : result.message || "The transaction could not be completed.";

  return (
    <section className={`decisionPanel ${approved ? "approved" : review ? "review" : blocked ? "blocked" : "error"}`}>
      <div>
        <p className="decisionLabel">Transaction Result</p>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      <div className="decisionDetails">
        {result.transaction_id ? (
          <div>
            <span>Reference</span>
            <strong>{result.transaction_id}</strong>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function TransactionHistory({ items }: { items: TransactionHistoryItem[] }) {
  return (
    <section className="historyPanel">
      <h2>Recent Transactions</h2>
      {items.length === 0 ? (
        <p className="muted smallText">No recent transactions yet.</p>
      ) : (
        <div className="historyList">
          {items.map((item) => (
            <article className="historyItem" key={item.transactionId}>
              <div>
                <strong>{formatTransactionType(item.transactionType)}</strong>
                <span>{item.accountId}</span>
              </div>
              <div className="historyRight">
                <strong>{item.currency} {item.amount.toFixed(2)}</strong>
                <span className={decisionClass(item.decision)}>{formatDecision(item.decision)}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function formatTransactionType(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDecision(value: string) {
  if (value === "APPROVE") return "Approved";
  if (value === "REVIEW") return "Review";
  if (value === "BLOCK") return "Blocked";
  return value || "Unknown";
}

function decisionClass(value: string) {
  if (value === "APPROVE") return "decisionBadge approved";
  if (value === "REVIEW") return "decisionBadge review";
  if (value === "BLOCK") return "decisionBadge blocked";
  return "decisionBadge";
}
