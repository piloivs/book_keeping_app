import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import { ArrowDownUp, BookOpenCheck, CircleDollarSign, Landmark, Plus, RefreshCw } from "lucide-react";
import { Account, JournalEntry, JournalEntryPayload, Summary, api } from "./lib/api";
import "./styles.css";

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD"
});

function formatMoney(value: string | number) {
  return money.format(Number(value));
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [accountData, summaryData, entryData] = await Promise.all([
        api.accounts(),
        api.summary(),
        api.journalEntries()
      ]);
      setAccounts(accountData);
      setSummary(summaryData);
      setEntries(entryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load bookkeeping data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Local ledger</p>
          <h1>Bookkeeping</h1>
        </div>
        <button className="iconButton" onClick={() => void loadData()} title="Refresh data" aria-label="Refresh data">
          <RefreshCw size={18} />
        </button>
      </header>

      {error ? <div className="notice">{error}</div> : null}

      <section className="metrics" aria-label="Financial summary">
        <Metric icon={<CircleDollarSign size={20} />} label="Cash" value={summary?.cash_balance ?? "0"} />
        <Metric icon={<ArrowDownUp size={20} />} label="Receivables" value={summary?.receivables ?? "0"} />
        <Metric icon={<Landmark size={20} />} label="Payables" value={summary?.payables ?? "0"} />
        <Metric icon={<BookOpenCheck size={20} />} label="Net income" value={summary?.net_income ?? "0"} />
      </section>

      <div className="workspace">
        <TransactionForm accounts={accounts} onCreated={() => void loadData()} />
        <section className="panel">
          <div className="panelHeader">
            <h2>Chart of Accounts</h2>
            <span>{accounts.length} accounts</span>
          </div>
          <AccountsTable accounts={accounts} loading={loading} />
        </section>
      </div>

      <section className="panel">
        <div className="panelHeader">
          <h2>Recent Entries</h2>
          <span>{entries.length} shown</span>
        </div>
        <EntryList entries={entries} loading={loading} />
      </section>
    </main>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <article className="metric">
      <div className="metricIcon">{icon}</div>
      <div>
        <p>{label}</p>
        <strong>{formatMoney(value)}</strong>
      </div>
    </article>
  );
}

function TransactionForm({ accounts, onCreated }: { accounts: Account[]; onCreated: () => void }) {
  const [entryDate, setEntryDate] = useState(today());
  const [memo, setMemo] = useState("Owner contribution");
  const [reference, setReference] = useState("");
  const [debitAccountId, setDebitAccountId] = useState<number | "">("");
  const [creditAccountId, setCreditAccountId] = useState<number | "">("");
  const [amount, setAmount] = useState("100.00");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (accounts.length && debitAccountId === "" && creditAccountId === "") {
      setDebitAccountId(accounts.find((account) => account.code === "1000")?.id ?? accounts[0].id);
      setCreditAccountId(accounts.find((account) => account.code === "3000")?.id ?? accounts[1]?.id ?? accounts[0].id);
    }
  }, [accounts, creditAccountId, debitAccountId]);

  const canSave = useMemo(() => {
    return Boolean(entryDate && memo && debitAccountId && creditAccountId && amount && Number(amount) > 0);
  }, [amount, creditAccountId, debitAccountId, entryDate, memo]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave || debitAccountId === "" || creditAccountId === "") return;

    const payload: JournalEntryPayload = {
      entry_date: entryDate,
      memo,
      reference: reference || undefined,
      lines: [
        { account_id: debitAccountId, debit: amount, description: memo },
        { account_id: creditAccountId, credit: amount, description: memo }
      ]
    };

    setSaving(true);
    setMessage(null);
    try {
      await api.createJournalEntry(payload);
      setMessage("Transaction saved.");
      onCreated();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to save transaction.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>New Transaction</h2>
        <span>Balanced entry</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <label>
          Date
          <input type="date" value={entryDate} onChange={(event) => setEntryDate(event.target.value)} />
        </label>
        <label>
          Memo
          <input value={memo} onChange={(event) => setMemo(event.target.value)} />
        </label>
        <label>
          Reference
          <input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="Optional" />
        </label>
        <label>
          Debit
          <select value={debitAccountId} onChange={(event) => setDebitAccountId(Number(event.target.value))}>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} {account.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Credit
          <select value={creditAccountId} onChange={(event) => setCreditAccountId(Number(event.target.value))}>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} {account.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Amount
          <input min="0.01" step="0.01" type="number" value={amount} onChange={(event) => setAmount(event.target.value)} />
        </label>
        <button className="primaryButton" disabled={!canSave || saving} type="submit">
          <Plus size={18} />
          {saving ? "Saving" : "Add"}
        </button>
        {message ? <p className="formMessage">{message}</p> : null}
      </form>
    </section>
  );
}

function AccountsTable({ accounts, loading }: { accounts: Account[]; loading: boolean }) {
  if (loading) return <div className="empty">Loading accounts...</div>;
  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Type</th>
            <th className="number">Balance</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <tr key={account.id}>
              <td>{account.code}</td>
              <td>{account.name}</td>
              <td className="typeCell">{account.type}</td>
              <td className="number">{formatMoney(account.balance)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EntryList({ entries, loading }: { entries: JournalEntry[]; loading: boolean }) {
  if (loading) return <div className="empty">Loading entries...</div>;
  if (!entries.length) return <div className="empty">No journal entries yet.</div>;

  return (
    <div className="entryList">
      {entries.map((entry) => (
        <article className="entry" key={entry.id}>
          <div className="entryHeader">
            <div>
              <strong>{entry.memo}</strong>
              <span>{entry.entry_date}</span>
            </div>
            <span>{entry.reference ?? `#${entry.id}`}</span>
          </div>
          <div className="entryLines">
            {entry.lines.map((line) => (
              <div key={line.id}>
                <span>
                  {line.account_code} {line.account_name}
                </span>
                <span>{Number(line.debit) > 0 ? formatMoney(line.debit) : ""}</span>
                <span>{Number(line.credit) > 0 ? formatMoney(line.credit) : ""}</span>
              </div>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

