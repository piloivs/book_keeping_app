import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  ArrowDownUp,
  BookOpenCheck,
  Building2,
  CircleDollarSign,
  FileText,
  Landmark,
  Plus,
  RefreshCw,
  Settings,
  Users
} from "lucide-react";
import {
  Account,
  BalanceSheet,
  CompanySettings,
  Contact,
  ContactPayload,
  JournalEntry,
  OperationalTransaction,
  OperationalTransactionPayload,
  ProfitAndLoss,
  Summary,
  TransactionKind,
  TransactionStatus,
  api
} from "./lib/api";
import "./styles.css";

const money = new Intl.NumberFormat("en-SG", {
  style: "currency",
  currency: "SGD"
});

type View = "dashboard" | "transactions" | "contacts" | "reports" | "settings";

function formatMoney(value: string | number) {
  return money.format(Number(value));
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function App() {
  const [view, setView] = useState<View>("dashboard");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [settings, setSettings] = useState<CompanySettings | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [transactions, setTransactions] = useState<OperationalTransaction[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [profitAndLoss, setProfitAndLoss] = useState<ProfitAndLoss | null>(null);
  const [balanceSheet, setBalanceSheet] = useState<BalanceSheet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [accountData, settingsData, contactData, transactionData, summaryData, entryData, pnlData, bsData] =
        await Promise.all([
          api.accounts(),
          api.companySettings(),
          api.contacts(),
          api.transactions(),
          api.summary(),
          api.journalEntries(),
          api.profitAndLoss(),
          api.balanceSheet()
        ]);
      setAccounts(accountData);
      setSettings(settingsData);
      setContacts(contactData);
      setTransactions(transactionData);
      setSummary(summaryData);
      setEntries(entryData);
      setProfitAndLoss(pnlData);
      setBalanceSheet(bsData);
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
          <p className="eyebrow">{settings?.company_name ?? "IntelliArtAI"}</p>
          <h1>Bookkeeping</h1>
        </div>
        <button className="iconButton" onClick={() => void loadData()} title="Refresh data" aria-label="Refresh data">
          <RefreshCw size={18} />
        </button>
      </header>

      <nav className="tabs" aria-label="Primary views">
        <TabButton active={view === "dashboard"} icon={<CircleDollarSign size={16} />} label="Dashboard" onClick={() => setView("dashboard")} />
        <TabButton active={view === "transactions"} icon={<FileText size={16} />} label="Transactions" onClick={() => setView("transactions")} />
        <TabButton active={view === "contacts"} icon={<Users size={16} />} label="Contacts" onClick={() => setView("contacts")} />
        <TabButton active={view === "reports"} icon={<BookOpenCheck size={16} />} label="Reports" onClick={() => setView("reports")} />
        <TabButton active={view === "settings"} icon={<Settings size={16} />} label="Settings" onClick={() => setView("settings")} />
      </nav>

      {error ? <div className="notice">{error}</div> : null}

      {view === "dashboard" ? (
        <DashboardView
          accounts={accounts}
          entries={entries}
          loading={loading}
          summary={summary}
          transactions={transactions}
          onRefresh={() => void loadData()}
        />
      ) : null}
      {view === "transactions" ? (
        <TransactionsView
          accounts={accounts}
          contacts={contacts}
          loading={loading}
          transactions={transactions}
          onChanged={() => void loadData()}
        />
      ) : null}
      {view === "contacts" ? <ContactsView contacts={contacts} loading={loading} onChanged={() => void loadData()} /> : null}
      {view === "reports" ? (
        <ReportsView balanceSheet={balanceSheet} loading={loading} profitAndLoss={profitAndLoss} />
      ) : null}
      {view === "settings" && settings ? <SettingsView settings={settings} onChanged={() => void loadData()} /> : null}
    </main>
  );
}

function TabButton({ active, icon, label, onClick }: { active: boolean; icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button className={active ? "tab active" : "tab"} onClick={onClick} type="button">
      {icon}
      {label}
    </button>
  );
}

function DashboardView({
  accounts,
  entries,
  loading,
  summary,
  transactions
}: {
  accounts: Account[];
  entries: JournalEntry[];
  loading: boolean;
  summary: Summary | null;
  transactions: OperationalTransaction[];
  onRefresh: () => void;
}) {
  return (
    <>
      <section className="metrics" aria-label="Financial summary">
        <Metric icon={<CircleDollarSign size={20} />} label="Cash" value={summary?.cash_balance ?? "0"} />
        <Metric icon={<ArrowDownUp size={20} />} label="Receivables" value={summary?.receivables ?? "0"} />
        <Metric icon={<Landmark size={20} />} label="Payables" value={summary?.payables ?? "0"} />
        <Metric icon={<BookOpenCheck size={20} />} label="Net income" value={summary?.net_income ?? "0"} />
      </section>

      <div className="workspace">
        <section className="panel">
          <div className="panelHeader">
            <h2>Operational Queue</h2>
            <span>{transactions.length} records</span>
          </div>
          <TransactionList compact loading={loading} transactions={transactions.slice(0, 6)} />
        </section>
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
          <h2>Recent Journal Entries</h2>
          <span>{entries.length} shown</span>
        </div>
        <EntryList entries={entries} loading={loading} />
      </section>
    </>
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

function TransactionsView({
  accounts,
  contacts,
  loading,
  transactions,
  onChanged
}: {
  accounts: Account[];
  contacts: Contact[];
  loading: boolean;
  transactions: OperationalTransaction[];
  onChanged: () => void;
}) {
  return (
    <div className="workspace">
      <TransactionCaptureForm accounts={accounts} contacts={contacts} onCreated={onChanged} />
      <section className="panel">
        <div className="panelHeader">
          <h2>Income & Expenses</h2>
          <span>{transactions.length} records</span>
        </div>
        <TransactionList loading={loading} transactions={transactions} onPost={onChanged} />
      </section>
    </div>
  );
}

function TransactionCaptureForm({ accounts, contacts, onCreated }: { accounts: Account[]; contacts: Contact[]; onCreated: () => void }) {
  const [kind, setKind] = useState<TransactionKind>("expense");
  const [status, setStatus] = useState<TransactionStatus>("posted");
  const [transactionDate, setTransactionDate] = useState(today());
  const [description, setDescription] = useState("Software subscription");
  const [reference, setReference] = useState("");
  const [amount, setAmount] = useState("100.00");
  const [contactId, setContactId] = useState<number | "">("");
  const [debitAccountId, setDebitAccountId] = useState<number | "">("");
  const [creditAccountId, setCreditAccountId] = useState<number | "">("");
  const [receipt, setReceipt] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const expenseAccounts = accounts.filter((account) => account.type === "expense");
  const revenueAccounts = accounts.filter((account) => account.type === "revenue");
  const cashAccounts = accounts.filter((account) => account.type === "asset");
  const payableAccounts = accounts.filter((account) => account.type === "liability");

  useEffect(() => {
    if (!accounts.length) return;
    if (kind === "expense") {
      setDebitAccountId(expenseAccounts.find((account) => account.code === "5100")?.id ?? expenseAccounts[0]?.id ?? "");
      setCreditAccountId(cashAccounts.find((account) => account.code === "1010")?.id ?? cashAccounts[0]?.id ?? "");
      setDescription("Software subscription");
    } else {
      setDebitAccountId(cashAccounts.find((account) => account.code === "1010")?.id ?? cashAccounts[0]?.id ?? "");
      setCreditAccountId(revenueAccounts.find((account) => account.code === "4100")?.id ?? revenueAccounts[0]?.id ?? "");
      setDescription("Client income");
    }
  }, [accounts, kind]);

  const canSave = useMemo(() => {
    return Boolean(transactionDate && description && debitAccountId && creditAccountId && amount && Number(amount) > 0);
  }, [amount, creditAccountId, debitAccountId, description, transactionDate]);

  async function receiptPayload(file: File) {
    const buffer = await file.arrayBuffer();
    const binary = Array.from(new Uint8Array(buffer), (byte) => String.fromCharCode(byte)).join("");
    return {
      filename: file.name,
      content_type: file.type || undefined,
      content_base64: btoa(binary)
    };
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave || debitAccountId === "" || creditAccountId === "") return;

    const payload: OperationalTransactionPayload = {
      kind,
      status,
      transaction_date: transactionDate,
      description,
      reference: reference || undefined,
      amount,
      contact_id: contactId === "" ? undefined : contactId,
      debit_account_id: debitAccountId,
      credit_account_id: creditAccountId,
      receipt: receipt ? await receiptPayload(receipt) : undefined
    };

    setSaving(true);
    setMessage(null);
    try {
      await api.createTransaction(payload);
      setMessage("Transaction saved.");
      setReference("");
      setReceipt(null);
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
        <h2>Record Transaction</h2>
        <span>Receipt-ready</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <div className="segmented">
          <button className={kind === "expense" ? "selected" : ""} onClick={() => setKind("expense")} type="button">
            Expense
          </button>
          <button className={kind === "income" ? "selected" : ""} onClick={() => setKind("income")} type="button">
            Income
          </button>
        </div>
        <label>
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value as TransactionStatus)}>
            <option value="draft">Draft</option>
            <option value="reviewed">Reviewed</option>
            <option value="posted">Posted</option>
          </select>
        </label>
        <label>
          Date
          <input type="date" value={transactionDate} onChange={(event) => setTransactionDate(event.target.value)} />
        </label>
        <label>
          Description
          <input value={description} onChange={(event) => setDescription(event.target.value)} />
        </label>
        <label>
          Contact
          <select value={contactId} onChange={(event) => setContactId(event.target.value ? Number(event.target.value) : "")}>
            <option value="">None</option>
            {contacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Reference
          <input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="Invoice, receipt, or bank ref" />
        </label>
        <label>
          {kind === "expense" ? "Expense Account" : "Deposit Account"}
          <select value={debitAccountId} onChange={(event) => setDebitAccountId(Number(event.target.value))}>
            {(kind === "expense" ? expenseAccounts : cashAccounts).map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} {account.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {kind === "expense" ? "Paid From" : "Revenue Account"}
          <select value={creditAccountId} onChange={(event) => setCreditAccountId(Number(event.target.value))}>
            {(kind === "expense" ? [...cashAccounts, ...payableAccounts] : revenueAccounts).map((account) => (
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
        <label>
          Receipt
          <input type="file" onChange={(event) => setReceipt(event.target.files?.[0] ?? null)} />
        </label>
        <button className="primaryButton" disabled={!canSave || saving} type="submit">
          <Plus size={18} />
          {saving ? "Saving" : "Save"}
        </button>
        {message ? <p className="formMessage">{message}</p> : null}
      </form>
    </section>
  );
}

function ContactsView({ contacts, loading, onChanged }: { contacts: Contact[]; loading: boolean; onChanged: () => void }) {
  return (
    <div className="workspace">
      <ContactForm onCreated={onChanged} />
      <section className="panel">
        <div className="panelHeader">
          <h2>Customers & Vendors</h2>
          <span>{contacts.length} contacts</span>
        </div>
        {loading ? <div className="empty">Loading contacts...</div> : <ContactList contacts={contacts} />}
      </section>
    </div>
  );
}

function ContactForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [type, setType] = useState<ContactPayload["type"]>("vendor");
  const [email, setEmail] = useState("");
  const [taxIdentifier, setTaxIdentifier] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name) return;
    setSaving(true);
    setMessage(null);
    try {
      await api.createContact({
        name,
        type,
        email: email || undefined,
        tax_identifier: taxIdentifier || undefined
      });
      setName("");
      setEmail("");
      setTaxIdentifier("");
      setMessage("Contact saved.");
      onCreated();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to save contact.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>New Contact</h2>
        <span>Customer or vendor</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Type
          <select value={type} onChange={(event) => setType(event.target.value as ContactPayload["type"])}>
            <option value="vendor">Vendor</option>
            <option value="customer">Customer</option>
            <option value="both">Both</option>
          </select>
        </label>
        <label>
          Email
          <input value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label>
          Tax Identifier
          <input value={taxIdentifier} onChange={(event) => setTaxIdentifier(event.target.value)} />
        </label>
        <button className="primaryButton" disabled={!name || saving} type="submit">
          <Plus size={18} />
          {saving ? "Saving" : "Add"}
        </button>
        {message ? <p className="formMessage">{message}</p> : null}
      </form>
    </section>
  );
}

function ReportsView({ balanceSheet, loading, profitAndLoss }: { balanceSheet: BalanceSheet | null; loading: boolean; profitAndLoss: ProfitAndLoss | null }) {
  if (loading) return <section className="panel empty">Loading reports...</section>;
  return (
    <div className="reportGrid">
      <section className="panel">
        <div className="panelHeader">
          <h2>Profit & Loss</h2>
          <span>Posted entries</span>
        </div>
        <ReportLine label="Revenue" value={profitAndLoss?.revenue ?? "0"} />
        <ReportLine label="Expenses" value={profitAndLoss?.expenses ?? "0"} />
        <ReportLine strong label="Net income" value={profitAndLoss?.net_income ?? "0"} />
      </section>
      <section className="panel">
        <div className="panelHeader">
          <h2>Balance Sheet</h2>
          <span>Current position</span>
        </div>
        <ReportLine label="Assets" value={balanceSheet?.assets ?? "0"} />
        <ReportLine label="Liabilities" value={balanceSheet?.liabilities ?? "0"} />
        <ReportLine label="Equity" value={balanceSheet?.equity ?? "0"} />
        <ReportLine label="Retained earnings" value={balanceSheet?.retained_earnings ?? "0"} />
        <ReportLine strong label="Liabilities + equity" value={balanceSheet?.total_liabilities_and_equity ?? "0"} />
      </section>
    </div>
  );
}

function SettingsView({ settings, onChanged }: { settings: CompanySettings; onChanged: () => void }) {
  const [companyName, setCompanyName] = useState(settings.company_name);
  const [registrationNumber, setRegistrationNumber] = useState(settings.registration_number ?? "");
  const [fiscalYearStartMonth, setFiscalYearStartMonth] = useState(String(settings.fiscal_year_start_month));
  const [baseCurrency, setBaseCurrency] = useState(settings.base_currency);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await api.updateCompanySettings({
        company_name: companyName,
        registration_number: registrationNumber || null,
        fiscal_year_start_month: Number(fiscalYearStartMonth),
        base_currency: baseCurrency
      });
      setMessage("Settings saved.");
      onChanged();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to save settings.");
    }
  }

  return (
    <section className="panel settingsPanel">
      <div className="panelHeader">
        <h2>Company Settings</h2>
        <span>Reporting defaults</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <label>
          Company Name
          <input value={companyName} onChange={(event) => setCompanyName(event.target.value)} />
        </label>
        <label>
          Registration Number
          <input value={registrationNumber} onChange={(event) => setRegistrationNumber(event.target.value)} />
        </label>
        <label>
          Fiscal Year Start Month
          <input min="1" max="12" type="number" value={fiscalYearStartMonth} onChange={(event) => setFiscalYearStartMonth(event.target.value)} />
        </label>
        <label>
          Base Currency
          <input maxLength={3} value={baseCurrency} onChange={(event) => setBaseCurrency(event.target.value.toUpperCase())} />
        </label>
        <button className="primaryButton" type="submit">
          <Building2 size={18} />
          Save
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

function TransactionList({
  compact = false,
  loading,
  transactions,
  onPost
}: {
  compact?: boolean;
  loading: boolean;
  transactions: OperationalTransaction[];
  onPost?: () => void;
}) {
  if (loading) return <div className="empty">Loading transactions...</div>;
  if (!transactions.length) return <div className="empty">No operational transactions yet.</div>;

  async function post(id: number) {
    await api.postTransaction(id);
    onPost?.();
  }

  return (
    <div className="entryList">
      {transactions.map((transaction) => (
        <article className="entry" key={transaction.id}>
          <div className="entryHeader">
            <div>
              <strong>{transaction.description}</strong>
              <span>
                {transaction.transaction_date} · {transaction.kind} · {transaction.status}
              </span>
            </div>
            <span>{formatMoney(transaction.amount)}</span>
          </div>
          {!compact ? (
            <div className="transactionMeta">
              <span>{transaction.contact?.name ?? "No contact"}</span>
              <span>
                {transaction.debit_account.code} {"->"} {transaction.credit_account.code}
              </span>
              <span>{transaction.receipt ? transaction.receipt.original_filename : "No receipt"}</span>
              {transaction.status !== "posted" ? (
                <button className="smallButton" onClick={() => void post(transaction.id)} type="button">
                  Post
                </button>
              ) : null}
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function ContactList({ contacts }: { contacts: Contact[] }) {
  if (!contacts.length) return <div className="empty">No contacts yet.</div>;
  return (
    <div className="entryList">
      {contacts.map((contact) => (
        <article className="entry" key={contact.id}>
          <div className="entryHeader">
            <div>
              <strong>{contact.name}</strong>
              <span>{contact.type}</span>
            </div>
            <span>{contact.tax_identifier ?? ""}</span>
          </div>
          <div className="transactionMeta">
            <span>{contact.email ?? "No email"}</span>
            <span>{contact.phone ?? "No phone"}</span>
          </div>
        </article>
      ))}
    </div>
  );
}

function ReportLine({ label, strong = false, value }: { label: string; strong?: boolean; value: string }) {
  return (
    <div className={strong ? "reportLine strong" : "reportLine"}>
      <span>{label}</span>
      <span>{formatMoney(value)}</span>
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
