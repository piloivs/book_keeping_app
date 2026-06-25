import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  ArrowDownUp,
  BookOpenCheck,
  Building2,
  CircleDollarSign,
  Download,
  ClipboardList,
  FileText,
  Landmark,
  Plus,
  Printer,
  RefreshCw,
  Settings,
  Upload,
  Users
} from "lucide-react";
import {
  Account,
  AccountsReceivableAgeing,
  BalanceSheet,
  ChartOfAccountsImportMode,
  ChartOfAccountsValidationResult,
  ClientHistory,
  ClientHistoryEntry,
  CompanySettings,
  Contact,
  ContactPayload,
  CpfProfile,
  CustomerReceipt,
  CustomerReceiptPayload,
  DepositStatus,
  Employee,
  EmployeePayload,
  EmployeeStatus,
  JournalEntry,
  OperationalTransaction,
  OperationalTransactionPayload,
  PayrollRun,
  PayrollRunPayload,
  PayrollStatus,
  ProfitAndLoss,
  PurchaseOrder,
  PurchaseOrderPayload,
  PurchaseOrderStatus,
  SalesOrder,
  SalesOrderPayload,
  SalesOrderStatus,
  SalesInvoice,
  SalesInvoicePayload,
  SalesInvoiceStatus,
  Summary,
  TransactionKind,
  TransactionStatus,
  VendorQualificationStatus,
  api
} from "./lib/api";
import "./styles.css";

const money = new Intl.NumberFormat("en-SG", {
  style: "currency",
  currency: "SGD"
});

type View = "dashboard" | "finance" | "sales" | "purchasing" | "hrPayroll" | "reports" | "settings";

function formatMoney(value: string | number) {
  return money.format(Number(value));
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function compactDate(value: string) {
  return value.replace(/-/g, "");
}

function displayClientPo(value: string) {
  return value.startsWith("NO-PO-") ? "No client PO" : value;
}

function App() {
  const [view, setView] = useState<View>("dashboard");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [settings, setSettings] = useState<CompanySettings | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [transactions, setTransactions] = useState<OperationalTransaction[]>([]);
  const [salesOrders, setSalesOrders] = useState<SalesOrder[]>([]);
  const [salesInvoices, setSalesInvoices] = useState<SalesInvoice[]>([]);
  const [customerReceipts, setCustomerReceipts] = useState<CustomerReceipt[]>([]);
  const [clientHistory, setClientHistory] = useState<ClientHistory | null>(null);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [payrollRuns, setPayrollRuns] = useState<PayrollRun[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [arAgeing, setArAgeing] = useState<AccountsReceivableAgeing | null>(null);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [profitAndLoss, setProfitAndLoss] = useState<ProfitAndLoss | null>(null);
  const [balanceSheet, setBalanceSheet] = useState<BalanceSheet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [accountData, settingsData, contactData, employeeData, transactionData, salesOrderData, salesInvoiceData, customerReceiptData, clientHistoryData, purchaseOrderData, payrollData, summaryData, arAgeingData, entryData, pnlData, bsData] =
        await Promise.all([
          api.accounts(),
          api.companySettings(),
          api.contacts(),
          api.employees(),
          api.transactions(),
          api.salesOrders(),
          api.salesInvoices(),
          api.customerReceipts(),
          api.clientHistory(),
          api.purchaseOrders(),
          api.payroll(),
          api.summary(),
          api.accountsReceivableAgeing(),
          api.journalEntries(),
          api.profitAndLoss(),
          api.balanceSheet()
        ]);
      setAccounts(accountData);
      setSettings(settingsData);
      setContacts(contactData);
      setEmployees(employeeData);
      setTransactions(transactionData);
      setSalesOrders(salesOrderData);
      setSalesInvoices(salesInvoiceData);
      setCustomerReceipts(customerReceiptData);
      setClientHistory(clientHistoryData);
      setPurchaseOrders(purchaseOrderData);
      setPayrollRuns(payrollData);
      setSummary(summaryData);
      setArAgeing(arAgeingData);
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
          <h1>Operations Core</h1>
        </div>
        <button className="iconButton" onClick={() => void loadData()} title="Refresh data" aria-label="Refresh data">
          <RefreshCw size={18} />
        </button>
      </header>

      <nav className="tabs" aria-label="Primary views">
        <TabButton active={view === "dashboard"} icon={<CircleDollarSign size={16} />} label="Dashboard" onClick={() => setView("dashboard")} />
        <TabButton active={view === "finance"} icon={<Landmark size={16} />} label="Finance" onClick={() => setView("finance")} />
        <TabButton active={view === "sales"} icon={<ArrowDownUp size={16} />} label="Sales" onClick={() => setView("sales")} />
        <TabButton active={view === "purchasing"} icon={<ClipboardList size={16} />} label="Purchasing" onClick={() => setView("purchasing")} />
        <TabButton active={view === "hrPayroll"} icon={<Users size={16} />} label="HR & Payroll" onClick={() => setView("hrPayroll")} />
        <TabButton active={view === "reports"} icon={<BookOpenCheck size={16} />} label="Reports" onClick={() => setView("reports")} />
        <TabButton active={view === "settings"} icon={<Settings size={16} />} label="Settings" onClick={() => setView("settings")} />
      </nav>

      {error ? <div className="notice">{error}</div> : null}

      {view === "dashboard" ? (
        <DashboardView
          accounts={accounts}
          arAgeing={arAgeing}
          entries={entries}
          loading={loading}
          summary={summary}
          transactions={transactions}
        />
      ) : null}
      {view === "finance" ? (
        <FinanceView
          accounts={accounts}
          contacts={contacts}
          loading={loading}
          transactions={transactions}
          onChanged={() => void loadData()}
        />
      ) : null}
      {view === "sales" ? (
        <SalesView
          accounts={accounts}
          contacts={contacts}
          customerReceipts={customerReceipts}
          clientHistory={clientHistory}
          loading={loading}
          salesInvoices={salesInvoices}
          salesOrders={salesOrders}
          onChanged={() => void loadData()}
        />
      ) : null}
      {view === "purchasing" ? (
        <PurchasingView
          accounts={accounts}
          contacts={contacts}
          loading={loading}
          purchaseOrders={purchaseOrders}
          onChanged={() => void loadData()}
        />
      ) : null}
      {view === "hrPayroll" ? (
        <HrPayrollView
          accounts={accounts}
          employees={employees}
          loading={loading}
          payrollRuns={payrollRuns}
          settings={settings}
          onChanged={() => void loadData()}
        />
      ) : null}
      {view === "reports" ? (
        <ReportsView balanceSheet={balanceSheet} loading={loading} profitAndLoss={profitAndLoss} />
      ) : null}
      {view === "settings" && settings ? <SettingsView accounts={accounts} loading={loading} settings={settings} onChanged={() => void loadData()} /> : null}
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
  arAgeing,
  entries,
  loading,
  summary,
  transactions
}: {
  accounts: Account[];
  arAgeing: AccountsReceivableAgeing | null;
  entries: JournalEntry[];
  loading: boolean;
  summary: Summary | null;
  transactions: OperationalTransaction[];
}) {
  return (
    <>
      <section className="metrics" aria-label="Financial summary">
        <Metric icon={<CircleDollarSign size={20} />} label="Cash" value={summary?.cash_balance ?? "0"} />
        <Metric icon={<ArrowDownUp size={20} />} label="Receivables" value={summary?.receivables ?? "0"} />
        <Metric icon={<Landmark size={20} />} label="Payables" value={summary?.payables ?? "0"} />
        <Metric icon={<BookOpenCheck size={20} />} label="Net income" value={summary?.net_income ?? "0"} />
      </section>

      <AccountsReceivableAgeingPanel ageing={arAgeing} loading={loading} />

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
          <div className="printArea">
            <div className="printHeader">
              <h2>Chart of Accounts</h2>
              <span>Generated {today()}</span>
            </div>
            <AccountsTable accounts={accounts} loading={loading} />
          </div>
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

function ChartOfAccountsTools({ onChanged }: { onChanged: () => void }) {
  const [mode, setMode] = useState<ChartOfAccountsImportMode>("add_only");
  const [message, setMessage] = useState<string | null>(null);
  const [validation, setValidation] = useState<ChartOfAccountsValidationResult | null>(null);
  const [busy, setBusy] = useState(false);

  function selectImportMode(nextMode: ChartOfAccountsImportMode) {
    if (nextMode === mode) return;

    const confirmed = window.confirm(
      nextMode === "setup_replace"
        ? "Setup Replace is intended only for initial company setup. It can replace the full chart of accounts from an imported CSV and is blocked after accounts are used by transactions, documents, payroll, contacts, or journal lines.\n\nContinue with Setup Replace mode?"
        : "Add Only keeps existing account codes unchanged and only adds new accounts from an imported CSV. Existing matching account codes will be skipped.\n\nContinue with Add Only mode?"
    );
    if (!confirmed) return;

    setMode(nextMode);
    setMessage(null);
    setValidation(null);
  }

  async function downloadTemplate() {
    setBusy(true);
    setMessage(null);
    setValidation(null);
    try {
      await api.downloadAccountsTemplate();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to download template.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadExport() {
    setBusy(true);
    setMessage(null);
    setValidation(null);
    try {
      await api.downloadAccountsExport();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to export chart of accounts.");
    } finally {
      setBusy(false);
    }
  }

  async function importFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setBusy(true);
    setMessage(null);
    setValidation(null);
    try {
      const csvText = await file.text();
      const validationResult = await api.validateAccounts(mode, csvText);
      setValidation(validationResult);
      if (!validationResult.can_import) {
        setMessage("Import blocked by validation errors.");
        return;
      }

      if (validationResult.warnings.length) {
        const warningText = validationResult.warnings.map((warning) => warning.message).join("\n");
        const confirmed = window.confirm(`Validation found ${validationResult.warnings.length} warning${validationResult.warnings.length === 1 ? "" : "s"}:\n\n${warningText}\n\nContinue importing?`);
        if (!confirmed) {
          setMessage("Import cancelled after validation.");
          return;
        }
      }

      const result = await api.importAccounts(mode, csvText);
      setMessage(`Validation passed. Imported ${result.created} new account${result.created === 1 ? "" : "s"}; skipped ${result.skipped}.`);
      onChanged();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to import chart of accounts.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="coaTools noPrint">
      <div className="segmented" aria-label="Chart of accounts import mode">
        <button className={mode === "add_only" ? "active" : ""} onClick={() => selectImportMode("add_only")} type="button">
          Add Only
        </button>
        <button className={mode === "setup_replace" ? "active" : ""} onClick={() => selectImportMode("setup_replace")} type="button">
          Setup Replace
        </button>
      </div>
      <div className="rowActions">
        <button className="smallButton" disabled={busy} onClick={downloadTemplate} type="button">
          <Download size={15} />
          Template
        </button>
        <button className="smallButton" disabled={busy} onClick={downloadExport} type="button">
          <Download size={15} />
          Export
        </button>
        <label className={busy ? "smallButton disabled" : "smallButton"}>
          <Upload size={15} />
          Import
          <input accept=".csv,text/csv" hidden onChange={importFile} type="file" />
        </label>
        <button className="smallButton" onClick={() => window.print()} type="button">
          <Printer size={15} />
          Print
        </button>
      </div>
      {message ? <p className="formMessage">{message}</p> : null}
      {validation ? <ChartOfAccountsValidationSummary validation={validation} /> : null}
    </div>
  );
}

function ChartOfAccountsValidationSummary({ validation }: { validation: ChartOfAccountsValidationResult }) {
  return (
    <div className="validationSummary">
      <div>
        <strong>{validation.can_import ? "Ready to import" : "Import blocked"}</strong>
        <span>{validation.account_count} account rows checked</span>
      </div>
      {validation.errors.length ? <ValidationIssueList title="Errors" items={validation.errors.map((issue) => issue.message)} /> : null}
      {validation.warnings.length ? <ValidationIssueList title="Warnings" items={validation.warnings.map((issue) => issue.message)} /> : null}
      {validation.info.length ? <ValidationIssueList title="Notes" items={validation.info.map((issue) => issue.message)} /> : null}
    </div>
  );
}

function ValidationIssueList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="validationGroup">
      <span>{title}</span>
      <ul>
        {items.slice(0, 4).map((item) => (
          <li key={item}>{item}</li>
        ))}
        {items.length > 4 ? <li>{items.length - 4} more...</li> : null}
      </ul>
    </div>
  );
}

function AccountsReceivableAgeingPanel({ ageing, loading }: { ageing: AccountsReceivableAgeing | null; loading: boolean }) {
  if (loading) return <section className="panel empty">Loading A/R ageing...</section>;
  const buckets = [
    { label: "0-30", value: ageing?.current ?? "0" },
    { label: "31-60", value: ageing?.days_31_60 ?? "0" },
    { label: "61-90", value: ageing?.days_61_90 ?? "0" },
    { label: "90+", value: ageing?.days_over_90 ?? "0" }
  ];
  return (
    <section className="panel arAgeingPanel">
      <div className="panelHeader">
        <h2>A/R Ageing</h2>
        <span>As of {ageing?.as_of ?? today()}</span>
      </div>
      <div className="ageingSummary" aria-label="Accounts receivable ageing buckets">
        {buckets.map((bucket) => (
          <div className="ageingBucket" key={bucket.label}>
            <span>{bucket.label}</span>
            <strong>{formatMoney(bucket.value)}</strong>
          </div>
        ))}
        <div className="ageingBucket total">
          <span>Total</span>
          <strong>{formatMoney(ageing?.total ?? "0")}</strong>
        </div>
      </div>
      {ageing?.rows.length ? (
        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th className="number">0-30</th>
                <th className="number">31-60</th>
                <th className="number">61-90</th>
                <th className="number">90+</th>
                <th className="number">Total</th>
              </tr>
            </thead>
            <tbody>
              {ageing.rows.map((row) => (
                <tr key={`${row.customer_id ?? "unassigned"}-${row.customer_name}`}>
                  <td>{row.customer_name}</td>
                  <td className="number">{formatMoney(row.current)}</td>
                  <td className="number">{formatMoney(row.days_31_60)}</td>
                  <td className="number">{formatMoney(row.days_61_90)}</td>
                  <td className="number">{formatMoney(row.days_over_90)}</td>
                  <td className="number">{formatMoney(row.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty">No open receivables yet.</div>
      )}
    </section>
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

function FinanceView({
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

type PurchaseOrderDraftLine = {
  description: string;
  quantity: string;
  unit_price: string;
  tax_amount: string;
  expense_account_id: number | "";
};

type SalesOrderDraftLine = {
  description: string;
  quantity: string;
  unit_price: string;
  tax_amount: string;
  revenue_account_id: number | "";
};

function SalesView({
  accounts,
  contacts,
  customerReceipts,
  clientHistory,
  loading,
  salesInvoices,
  salesOrders,
  onChanged
}: {
  accounts: Account[];
  contacts: Contact[];
  customerReceipts: CustomerReceipt[];
  clientHistory: ClientHistory | null;
  loading: boolean;
  salesInvoices: SalesInvoice[];
  salesOrders: SalesOrder[];
  onChanged: () => void;
}) {
  const customerContacts = contacts.filter((contact) => contact.type === "customer" || contact.type === "both");

  return (
    <>
      <div className="workspace">
        <ContactForm accounts={accounts} fixedType="customer" title="New Customer" subtitle="Sales master record" onCreated={onChanged} />
        <section className="panel">
          <div className="panelHeader">
            <h2>Customer Master</h2>
            <span>{customerContacts.length} customers</span>
          </div>
          {loading ? <div className="empty">Loading customers...</div> : <ContactList contacts={customerContacts} />}
        </section>
      </div>
      <div className="workspace">
        <SalesInvoiceForm accounts={accounts} contacts={contacts} salesOrders={salesOrders} onCreated={onChanged} />
        <section className="panel">
          <div className="panelHeader">
            <h2>Sales Invoices</h2>
            <span>{salesInvoices.length} records</span>
          </div>
          <SalesInvoiceList loading={loading} salesInvoices={salesInvoices} salesOrders={salesOrders} onChanged={onChanged} />
        </section>
      </div>
      <div className="workspace">
        <CustomerReceiptForm accounts={accounts} contacts={contacts} salesInvoices={salesInvoices} onCreated={onChanged} />
        <section className="panel">
          <div className="panelHeader">
            <h2>Customer Receipts</h2>
            <span>{customerReceipts.length} records</span>
          </div>
          <CustomerReceiptList customerReceipts={customerReceipts} loading={loading} />
        </section>
      </div>
      <div className="workspace">
        <SalesOrderForm accounts={accounts} contacts={contacts} onCreated={onChanged} />
        <section className="panel">
          <div className="panelHeader">
            <h2>Client Purchase Orders</h2>
            <span>{salesOrders.length} records</span>
          </div>
          <SalesOrderList loading={loading} salesOrders={salesOrders} onChanged={onChanged} />
        </section>
      </div>
      <ClientHistoryView clientHistory={clientHistory} loading={loading} />
    </>
  );
}

function ClientHistoryView({ clientHistory, loading }: { clientHistory: ClientHistory | null; loading: boolean }) {
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
  const clients = clientHistory?.clients ?? [];
  const selectedClient = clients.find((entry) => entry.customer.id === selectedClientId) ?? clients[0] ?? null;

  useEffect(() => {
    if (!clients.length) {
      setSelectedClientId(null);
      return;
    }
    if (!selectedClientId || !clients.some((entry) => entry.customer.id === selectedClientId)) {
      setSelectedClientId(clients[0].customer.id);
    }
  }, [clients, selectedClientId]);

  if (loading) return <section className="panel"><div className="empty">Loading client history...</div></section>;
  if (!clientHistory || !clients.length) return <section className="panel"><div className="empty">No client order or payment history yet.</div></section>;

  return (
    <>
      <div className="metrics">
        <Metric label="Ordered" value={selectedClient?.ordered_total ?? "0"} icon={<ClipboardList size={20} />} />
        <Metric label="Invoiced" value={selectedClient?.invoiced_total ?? "0"} icon={<FileText size={20} />} />
        <Metric label="Paid" value={selectedClient?.paid_total ?? "0"} icon={<CircleDollarSign size={20} />} />
        <Metric label="Unbilled" value={selectedClient?.unbilled_total ?? "0"} icon={<BookOpenCheck size={20} />} />
      </div>
      <div className="clientHistoryLayout">
        <section className="panel">
          <div className="panelHeader">
            <h2>Clients</h2>
            <span>{clients.length} records</span>
          </div>
          <div className="clientSelector">
            {clients.map((entry) => (
              <button
                className={selectedClient?.customer.id === entry.customer.id ? "clientOption active" : "clientOption"}
                key={entry.customer.id}
                onClick={() => setSelectedClientId(entry.customer.id)}
                type="button"
              >
                <strong>{entry.customer.name}</strong>
                <span>A/R {formatMoney(entry.receivable_total)} - Unbilled {formatMoney(entry.unbilled_total)}</span>
              </button>
            ))}
          </div>
        </section>
        {selectedClient ? <ClientHistoryDetail entry={selectedClient} /> : null}
      </div>
    </>
  );
}

function ClientHistoryDetail({ entry }: { entry: ClientHistoryEntry }) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>{entry.customer.name}</h2>
        <span>{entry.customer.payment_terms ?? "No terms"}</span>
      </div>
      <div className="ageingSummary clientTotals">
        <div className="ageingBucket">
          <span>Ordered</span>
          <strong>{formatMoney(entry.ordered_total)}</strong>
        </div>
        <div className="ageingBucket">
          <span>Invoiced</span>
          <strong>{formatMoney(entry.invoiced_total)}</strong>
        </div>
        <div className="ageingBucket">
          <span>Paid</span>
          <strong>{formatMoney(entry.paid_total)}</strong>
        </div>
        <div className="ageingBucket">
          <span>A/R</span>
          <strong>{formatMoney(entry.receivable_total)}</strong>
        </div>
        <div className="ageingBucket total">
          <span>Unbilled</span>
          <strong>{formatMoney(entry.unbilled_total)}</strong>
        </div>
      </div>
      <div className="historySections">
        <HistoryGroup title="Sales Bookings" count={entry.sales_orders.length}>
          {entry.sales_orders.length ? (
            entry.sales_orders.map((order) => (
              <article className="entry" key={order.id}>
                <div className="entryHeader">
                  <div>
                    <strong>{order.order_number}</strong>
                    <span>{displayClientPo(order.client_po_number)} - {order.received_date} - {order.status}</span>
                  </div>
                  <span>{formatMoney(order.total)}</span>
                </div>
                <div className="transactionMeta clientHistoryMeta">
                  <span>Invoiced {formatMoney(order.invoiced_total)}</span>
                  <span>Paid {formatMoney(order.paid_total)}</span>
                  <span>Unbilled {formatMoney(order.unbilled_total)}</span>
                  <span>{order.expected_delivery_date ?? "No delivery date"}</span>
                </div>
              </article>
            ))
          ) : (
            <div className="empty">No sales bookings.</div>
          )}
        </HistoryGroup>
        <HistoryGroup title="Invoices" count={entry.sales_invoices.length}>
          {entry.sales_invoices.length ? (
            entry.sales_invoices.map((invoice) => (
              <article className="entry" key={invoice.id}>
                <div className="entryHeader">
                  <div>
                    <strong>{invoice.invoice_number}</strong>
                    <span>Due {invoice.due_date} - {invoice.status}</span>
                  </div>
                  <span>{formatMoney(invoice.amount_due)}</span>
                </div>
                <div className="transactionMeta clientHistoryMeta">
                  <span>Total {formatMoney(invoice.total)}</span>
                  <span>Paid {formatMoney(invoice.amount_paid)}</span>
                  <span>{invoice.sales_order?.order_number ?? "No linked booking"}</span>
                  <span>{invoice.journal_entry_id ? `Journal #${invoice.journal_entry_id}` : "No journal"}</span>
                </div>
              </article>
            ))
          ) : (
            <div className="empty">No invoices.</div>
          )}
        </HistoryGroup>
        <HistoryGroup title="Receipts" count={entry.customer_receipts.length}>
          {entry.customer_receipts.length ? (
            entry.customer_receipts.map((receipt) => (
              <article className="entry" key={receipt.id}>
                <div className="entryHeader">
                  <div>
                    <strong>{receipt.receipt_number}</strong>
                    <span>{receipt.receipt_date} - {receipt.status}</span>
                  </div>
                  <span>{formatMoney(receipt.amount)}</span>
                </div>
                <div className="transactionMeta clientHistoryMeta">
                  <span>{receipt.bank_account.code} {receipt.bank_account.name}</span>
                  <span>{receipt.reference ?? "No reference"}</span>
                  <span>{receipt.allocations.map((allocation) => allocation.invoice.invoice_number).join(", ")}</span>
                  <span>{receipt.journal_entry_id ? `Journal #${receipt.journal_entry_id}` : "No journal"}</span>
                </div>
              </article>
            ))
          ) : (
            <div className="empty">No receipts.</div>
          )}
        </HistoryGroup>
      </div>
    </section>
  );
}

function HistoryGroup({ children, count, title }: { children: React.ReactNode; count: number; title: string }) {
  return (
    <div className="historyGroup">
      <div className="panelHeader">
        <h2>{title}</h2>
        <span>{count} records</span>
      </div>
      <div className="entryList">{children}</div>
    </div>
  );
}

function SalesInvoiceForm({
  accounts,
  contacts,
  salesOrders,
  onCreated
}: {
  accounts: Account[];
  contacts: Contact[];
  salesOrders: SalesOrder[];
  onCreated: () => void;
}) {
  const revenueAccounts = accounts.filter((account) => account.type === "revenue");
  const customerContacts = contacts.filter((contact) => contact.type === "customer" || contact.type === "both");
  const firstRevenueId = revenueAccounts[0]?.id ?? "";
  const [status, setStatus] = useState<SalesInvoiceStatus>("issued");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [customerId, setCustomerId] = useState<number | "">("");
  const [salesOrderId, setSalesOrderId] = useState<number | "">("");
  const [issueDate, setIssueDate] = useState(today());
  const [dueDate, setDueDate] = useState(today());
  const [currency, setCurrency] = useState("SGD");
  const [paymentTerms, setPaymentTerms] = useState("");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<SalesOrderDraftLine[]>([
    { description: "Client service", quantity: "1", unit_price: "1000.00", tax_amount: "0.00", revenue_account_id: firstRevenueId }
  ]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const selectedCustomer = customerContacts.find((contact) => contact.id === customerId);
  const customerSalesOrders = salesOrders.filter(
    (order) => order.customer.id === customerId && !["closed", "cancelled"].includes(order.status) && Number(order.unbilled_total) > 0
  );
  const total = lines.reduce((sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_price || 0) + Number(line.tax_amount || 0), 0);
  const canSave =
    Boolean(customerId && issueDate && dueDate && currency.length === 3 && lines.length) &&
    new Date(dueDate) >= new Date(issueDate) &&
    lines.every((line) => line.description && Number(line.quantity) > 0 && Number(line.unit_price) >= 0 && Number(line.tax_amount) >= 0 && line.revenue_account_id);

  useEffect(() => {
    if (!firstRevenueId || !lines.length || lines.some((line) => line.revenue_account_id !== "")) return;
    setLines((current) => current.map((line) => ({ ...line, revenue_account_id: firstRevenueId })));
  }, [firstRevenueId, lines]);

  useEffect(() => {
    if (selectedCustomer?.payment_terms) {
      setPaymentTerms(selectedCustomer.payment_terms);
    }
  }, [selectedCustomer?.id]);

  useEffect(() => {
    if (salesOrderId || customerSalesOrders.length !== 1) return;
    setSalesOrderId(customerSalesOrders[0].id);
  }, [customerId, customerSalesOrders, salesOrderId]);

  function updateLine(index: number, changes: Partial<SalesOrderDraftLine>) {
    setLines((current) => current.map((line, lineIndex) => (lineIndex === index ? { ...line, ...changes } : line)));
  }

  function addLine() {
    setLines((current) => [
      ...current,
      { description: "", quantity: "1", unit_price: "0.00", tax_amount: "0.00", revenue_account_id: firstRevenueId }
    ]);
  }

  function removeLine(index: number) {
    setLines((current) => (current.length === 1 ? current : current.filter((_, lineIndex) => lineIndex !== index)));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave || customerId === "") return;
    const payload: SalesInvoicePayload = {
      invoice_number: invoiceNumber || undefined,
      status,
      customer_id: customerId,
      sales_order_id: salesOrderId || undefined,
      issue_date: issueDate,
      due_date: dueDate,
      currency,
      payment_terms: paymentTerms || undefined,
      notes: notes || undefined,
      lines: lines.map((line) => ({
        description: line.description,
        quantity: line.quantity,
        unit_price: line.unit_price,
        tax_amount: line.tax_amount,
        revenue_account_id: Number(line.revenue_account_id)
      }))
    };
    setSaving(true);
    setMessage(null);
    try {
      await api.createSalesInvoice(payload);
      setInvoiceNumber("");
      setSalesOrderId("");
      setNotes("");
      setMessage(status === "issued" ? "Invoice issued and posted." : "Draft invoice saved.");
      onCreated();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to save invoice.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>Create Invoice</h2>
        <span>{formatMoney(total.toFixed(2))}</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <div className="formGrid">
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value as SalesInvoiceStatus)}>
              <option value="issued">Issue Now</option>
              <option value="draft">Draft</option>
            </select>
          </label>
          <label>
            Invoice No.
            <input value={invoiceNumber} onChange={(event) => setInvoiceNumber(event.target.value)} placeholder="Auto if blank" />
          </label>
        </div>
        <label>
          Customer
          <select value={customerId} onChange={(event) => { setCustomerId(event.target.value ? Number(event.target.value) : ""); setSalesOrderId(""); }}>
            <option value="">Select customer</option>
            {customerContacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Link Sales Booking
          <select value={salesOrderId} onChange={(event) => setSalesOrderId(event.target.value ? Number(event.target.value) : "")}>
            <option value="">No linked booking</option>
            {customerSalesOrders.map((order) => (
              <option key={order.id} value={order.id}>
                {order.order_number} - unbilled {formatMoney(order.unbilled_total)}
              </option>
            ))}
          </select>
        </label>
        <div className="formGrid">
          <label>
            Issue Date
            <input type="date" value={issueDate} onChange={(event) => setIssueDate(event.target.value)} />
          </label>
          <label>
            Due Date
            <input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} />
          </label>
        </div>
        <div className="formGrid">
          <label>
            Currency
            <input maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} />
          </label>
          <label>
            Payment Terms
            <input value={paymentTerms} onChange={(event) => setPaymentTerms(event.target.value)} placeholder="Net 30" />
          </label>
        </div>
        <div className="lineEditor">
          {lines.map((line, index) => (
            <div className="poLine" key={index}>
              <label>
                Description
                <input value={line.description} onChange={(event) => updateLine(index, { description: event.target.value })} />
              </label>
              <div className="formGrid">
                <label>
                  Qty
                  <input min="0.001" step="0.001" type="number" value={line.quantity} onChange={(event) => updateLine(index, { quantity: event.target.value })} />
                </label>
                <label>
                  Unit Price
                  <input min="0" step="0.01" type="number" value={line.unit_price} onChange={(event) => updateLine(index, { unit_price: event.target.value })} />
                </label>
              </div>
              <div className="formGrid">
                <label>
                  Tax
                  <input min="0" step="0.01" type="number" value={line.tax_amount} onChange={(event) => updateLine(index, { tax_amount: event.target.value })} />
                </label>
                <label>
                  Revenue Account
                  <select value={line.revenue_account_id} onChange={(event) => updateLine(index, { revenue_account_id: Number(event.target.value) })}>
                    <option value="">Select</option>
                    {revenueAccounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.code} {account.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button className="smallButton" disabled={lines.length === 1} onClick={() => removeLine(index)} type="button">
                Remove Line
              </button>
            </div>
          ))}
          <button className="smallButton" onClick={addLine} type="button">
            <Plus size={14} />
            Add Line
          </button>
        </div>
        <label>
          Notes
          <input value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <button className="primaryButton" disabled={!canSave || saving} type="submit">
          <Plus size={18} />
          {saving ? "Saving" : "Save Invoice"}
        </button>
        {message ? <p className="formMessage">{message}</p> : null}
      </form>
    </section>
  );
}

function SalesInvoiceList({
  loading,
  salesInvoices,
  salesOrders,
  onChanged
}: {
  loading: boolean;
  salesInvoices: SalesInvoice[];
  salesOrders: SalesOrder[];
  onChanged: () => void;
}) {
  if (loading) return <div className="empty">Loading sales invoices...</div>;
  if (!salesInvoices.length) return <div className="empty">No sales invoices yet.</div>;

  async function issue(id: number) {
    await api.issueSalesInvoice(id);
    onChanged();
  }

  async function linkToOrder(invoiceId: number, salesOrderId: number) {
    await api.linkSalesInvoiceToOrder(invoiceId, salesOrderId);
    onChanged();
  }

  return (
    <div className="entryList">
      {salesInvoices.map((invoice) => (
        <article className="entry" key={invoice.id}>
          {(() => {
            const linkCandidates = salesOrders.filter(
              (order) =>
                !invoice.sales_order &&
                order.customer.id === invoice.customer.id &&
                !["closed", "cancelled"].includes(order.status) &&
                Number(order.unbilled_total) >= Number(invoice.total)
            );
            const suggestedOrder = linkCandidates.length === 1 ? linkCandidates[0] : null;
            return (
              <>
          <div className="entryHeader">
            <div>
              <strong>{invoice.invoice_number}</strong>
              <span>
                {invoice.customer.name} - Due {invoice.due_date} - {invoice.status}
              </span>
            </div>
            <span>{formatMoney(invoice.amount_due)}</span>
          </div>
          <div className="transactionMeta purchaseMeta">
            <span>Total {formatMoney(invoice.total)}</span>
            <span>Paid {formatMoney(invoice.amount_paid)}</span>
            <span>{invoice.sales_order ? invoice.sales_order.order_number : "No linked booking"}</span>
            <span>{invoice.payment_terms ?? "No terms"}</span>
            <div className="rowActions">
              {invoice.status === "draft" ? (
                <button className="smallButton" onClick={() => void issue(invoice.id)} type="button">
                  Issue
                </button>
              ) : null}
              {suggestedOrder ? (
                <button className="smallButton" onClick={() => void linkToOrder(invoice.id, suggestedOrder.id)} type="button">
                  Link {suggestedOrder.order_number}
                </button>
              ) : null}
            </div>
          </div>
          <div className="entryLines poLines">
            {invoice.lines.slice(0, 4).map((line) => (
              <div key={line.id}>
                <span>{line.description}</span>
                <span>
                  {line.quantity} x {formatMoney(line.unit_price)}
                </span>
                <span>{formatMoney(line.line_total)}</span>
              </div>
            ))}
          </div>
              </>
            );
          })()}
        </article>
      ))}
    </div>
  );
}

function CustomerReceiptForm({
  accounts,
  contacts,
  salesInvoices,
  onCreated
}: {
  accounts: Account[];
  contacts: Contact[];
  salesInvoices: SalesInvoice[];
  onCreated: () => void;
}) {
  const bankAccounts = accounts.filter((account) => account.type === "asset");
  const customerContacts = contacts.filter((contact) => contact.type === "customer" || contact.type === "both");
  const openInvoices = salesInvoices.filter((invoice) => !["draft", "paid", "voided"].includes(invoice.status) && Number(invoice.amount_due) > 0);
  const [receiptNumber, setReceiptNumber] = useState("");
  const [customerId, setCustomerId] = useState<number | "">("");
  const [invoiceId, setInvoiceId] = useState<number | "">("");
  const [receiptDate, setReceiptDate] = useState(today());
  const [currency, setCurrency] = useState("SGD");
  const [amount, setAmount] = useState("");
  const [bankAccountId, setBankAccountId] = useState<number | "">(bankAccounts.find((account) => account.code === "1010")?.id ?? bankAccounts[0]?.id ?? "");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const customerInvoices = openInvoices.filter((invoice) => invoice.customer.id === customerId);
  const selectedInvoice = openInvoices.find((invoice) => invoice.id === invoiceId);
  const suggestedReceiptNumber = selectedInvoice ? `${selectedInvoice.invoice_number}-R${compactDate(receiptDate)}-01` : "";
  const canSave = Boolean(customerId && invoiceId && receiptDate && currency.length === 3 && Number(amount) > 0 && bankAccountId);

  useEffect(() => {
    if (selectedInvoice) {
      setAmount(selectedInvoice.amount_due);
      setCurrency(selectedInvoice.currency);
      setReceiptNumber(`${selectedInvoice.invoice_number}-R${compactDate(receiptDate)}-01`);
    }
  }, [selectedInvoice?.id, receiptDate]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave || customerId === "" || invoiceId === "" || bankAccountId === "") return;
    const payload: CustomerReceiptPayload = {
      receipt_number: receiptNumber && receiptNumber !== suggestedReceiptNumber ? receiptNumber : undefined,
      status: "posted",
      customer_id: customerId,
      receipt_date: receiptDate,
      currency,
      amount,
      bank_account_id: bankAccountId,
      reference: reference || undefined,
      notes: notes || undefined,
      allocations: [{ invoice_id: invoiceId, amount }]
    };
    setSaving(true);
    setMessage(null);
    try {
      await api.createCustomerReceipt(payload);
      setReceiptNumber("");
      setInvoiceId("");
      setAmount("");
      setReference("");
      setNotes("");
      setMessage("Customer receipt posted.");
      onCreated();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to post customer receipt.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>Record Receipt</h2>
        <span>{amount ? formatMoney(amount) : "No invoice"}</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <label>
          Customer
          <select value={customerId} onChange={(event) => { setCustomerId(event.target.value ? Number(event.target.value) : ""); setInvoiceId(""); setAmount(""); }}>
            <option value="">Select customer</option>
            {customerContacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Invoice
          <select value={invoiceId} onChange={(event) => setInvoiceId(event.target.value ? Number(event.target.value) : "")}>
            <option value="">Select open invoice</option>
            {customerInvoices.map((invoice) => (
              <option key={invoice.id} value={invoice.id}>
                {invoice.invoice_number} - {formatMoney(invoice.amount_due)}
              </option>
            ))}
          </select>
        </label>
        <div className="formGrid">
          <label>
            Receipt No.
            <input value={receiptNumber} onChange={(event) => setReceiptNumber(event.target.value)} placeholder={suggestedReceiptNumber || "Auto if blank"} />
          </label>
          <label>
            Receipt Date
            <input type="date" value={receiptDate} onChange={(event) => setReceiptDate(event.target.value)} />
          </label>
        </div>
        <div className="formGrid">
          <label>
            Amount
            <input min="0.01" step="0.01" type="number" value={amount} onChange={(event) => setAmount(event.target.value)} />
          </label>
          <label>
            Bank Account
            <select value={bankAccountId} onChange={(event) => setBankAccountId(event.target.value ? Number(event.target.value) : "")}>
              <option value="">Select bank</option>
              {bankAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.code} {account.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Reference
          <input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="Bank reference" />
        </label>
        <label>
          Notes
          <input value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <button className="primaryButton" disabled={!canSave || saving} type="submit">
          <Plus size={18} />
          {saving ? "Posting" : "Post Receipt"}
        </button>
        {message ? <p className="formMessage">{message}</p> : null}
      </form>
    </section>
  );
}

function CustomerReceiptList({ customerReceipts, loading }: { customerReceipts: CustomerReceipt[]; loading: boolean }) {
  if (loading) return <div className="empty">Loading customer receipts...</div>;
  if (!customerReceipts.length) return <div className="empty">No customer receipts yet.</div>;
  return (
    <div className="entryList">
      {customerReceipts.map((receipt) => (
        <article className="entry" key={receipt.id}>
          <div className="entryHeader">
            <div>
              <strong>{receipt.receipt_number}</strong>
              <span>
                {receipt.customer.name} - {receipt.receipt_date} - {receipt.status}
              </span>
            </div>
            <span>{formatMoney(receipt.amount)}</span>
          </div>
          <div className="transactionMeta purchaseMeta">
            <span>{receipt.bank_account.code} {receipt.bank_account.name}</span>
            <span>{receipt.reference ?? "No reference"}</span>
            <span>{receipt.allocations.map((allocation) => allocation.invoice.invoice_number).join(", ")}</span>
            <span>{receipt.journal_entry_id ? `Journal #${receipt.journal_entry_id}` : "No journal"}</span>
          </div>
        </article>
      ))}
    </div>
  );
}

function SalesOrderForm({ accounts, contacts, onCreated }: { accounts: Account[]; contacts: Contact[]; onCreated: () => void }) {
  const revenueAccounts = accounts.filter((account) => account.type === "revenue");
  const customerContacts = contacts.filter((contact) => contact.type === "customer" || contact.type === "both");
  const firstRevenueId = revenueAccounts[0]?.id ?? "";
  const [status, setStatus] = useState<SalesOrderStatus>("received");
  const [orderNumber, setOrderNumber] = useState("");
  const [clientPoNumber, setClientPoNumber] = useState("");
  const [customerId, setCustomerId] = useState<number | "">("");
  const [receivedDate, setReceivedDate] = useState(today());
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState("");
  const [currency, setCurrency] = useState("SGD");
  const [paymentTerms, setPaymentTerms] = useState("");
  const [depositRequired, setDepositRequired] = useState(true);
  const [depositRate, setDepositRate] = useState("0.10");
  const [depositAmount, setDepositAmount] = useState("");
  const [depositDueDate, setDepositDueDate] = useState("");
  const [depositStatus, setDepositStatus] = useState<DepositStatus>("requested");
  const [notes, setNotes] = useState("");
  const [deliveryInstructions, setDeliveryInstructions] = useState("");
  const [lines, setLines] = useState<SalesOrderDraftLine[]>([
    { description: "Client service", quantity: "1", unit_price: "1000.00", tax_amount: "0.00", revenue_account_id: firstRevenueId }
  ]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!firstRevenueId || !lines.length || lines.some((line) => line.revenue_account_id !== "")) return;
    setLines((current) => current.map((line) => ({ ...line, revenue_account_id: firstRevenueId })));
  }, [firstRevenueId, lines]);

  const selectedCustomer = customerContacts.find((contact) => contact.id === customerId);
  const total = lines.reduce((sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_price || 0) + Number(line.tax_amount || 0), 0);
  const calculatedDeposit = depositRequired ? Number(depositAmount || 0) || total * Number(depositRate || 0) : 0;
  const canSave =
    Boolean(customerId && receivedDate && currency.length === 3 && lines.length) &&
    lines.every((line) => line.description && Number(line.quantity) > 0 && Number(line.unit_price) >= 0 && Number(line.tax_amount) >= 0 && line.revenue_account_id) &&
    (!depositRequired || (calculatedDeposit > 0 && calculatedDeposit <= total));

  useEffect(() => {
    if (selectedCustomer?.payment_terms) {
      setPaymentTerms(selectedCustomer.payment_terms);
    }
  }, [selectedCustomer?.id]);

  function updateLine(index: number, changes: Partial<SalesOrderDraftLine>) {
    setLines((current) => current.map((line, lineIndex) => (lineIndex === index ? { ...line, ...changes } : line)));
  }

  function addLine() {
    setLines((current) => [
      ...current,
      { description: "", quantity: "1", unit_price: "0.00", tax_amount: "0.00", revenue_account_id: firstRevenueId }
    ]);
  }

  function removeLine(index: number) {
    setLines((current) => (current.length === 1 ? current : current.filter((_, lineIndex) => lineIndex !== index)));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave || customerId === "") return;

    const payload: SalesOrderPayload = {
      order_number: orderNumber || undefined,
      client_po_number: clientPoNumber || undefined,
      status,
      customer_id: customerId,
      received_date: receivedDate,
      expected_delivery_date: expectedDeliveryDate || undefined,
      currency,
      payment_terms: paymentTerms || undefined,
      deposit_required: depositRequired,
      deposit_rate: depositRequired ? Number(depositRate || 0).toFixed(4) : "0.0000",
      deposit_amount: depositRequired && depositAmount ? depositAmount : undefined,
      deposit_due_date: depositRequired ? depositDueDate || undefined : undefined,
      deposit_status: depositRequired ? depositStatus : "not_requested",
      notes: notes || undefined,
      delivery_instructions: deliveryInstructions || undefined,
      lines: lines.map((line) => ({
        description: line.description,
        quantity: line.quantity,
        unit_price: line.unit_price,
        tax_amount: line.tax_amount,
        revenue_account_id: Number(line.revenue_account_id)
      }))
    };

    setSaving(true);
    setMessage(null);
    try {
      await api.createSalesOrder(payload);
      setOrderNumber("");
      setClientPoNumber("");
      setPaymentTerms("");
      setDepositAmount("");
      setDepositDueDate("");
      setDepositStatus("requested");
      setNotes("");
      setDeliveryInstructions("");
      setMessage("Client PO saved.");
      onCreated();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to save client PO.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>Sales Booking</h2>
        <span>{formatMoney(total)}</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <div className="formGrid">
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value as SalesOrderStatus)}>
              <option value="draft">Draft</option>
              <option value="received">Received</option>
              <option value="accepted">Accepted</option>
            </select>
          </label>
          <label>
            Sales Order
            <input value={orderNumber} onChange={(event) => setOrderNumber(event.target.value)} placeholder="Auto if blank" />
          </label>
        </div>
        <label>
          Client PO Number
          <input value={clientPoNumber} onChange={(event) => setClientPoNumber(event.target.value)} placeholder="Optional customer PO reference" />
        </label>
        <label>
          Customer
          <select value={customerId} onChange={(event) => setCustomerId(event.target.value ? Number(event.target.value) : "")}>
            <option value="">Select customer</option>
            {customerContacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>
        </label>
        <div className="formGrid">
          <label>
            Received Date
            <input type="date" value={receivedDate} onChange={(event) => setReceivedDate(event.target.value)} />
          </label>
          <label>
            Expected Delivery
            <input type="date" value={expectedDeliveryDate} onChange={(event) => setExpectedDeliveryDate(event.target.value)} />
          </label>
        </div>
        <label>
          Currency
          <input maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} />
        </label>
        <label>
          Payment Terms
          <input value={paymentTerms} onChange={(event) => setPaymentTerms(event.target.value)} placeholder="Agreed customer terms" />
        </label>
        <div className="lineEditor">
          <div className="poLine">
            <label className="checkLabel">
              <input checked={depositRequired} type="checkbox" onChange={(event) => setDepositRequired(event.target.checked)} />
              Deposit required
            </label>
            {depositRequired ? (
              <>
                <div className="segmented">
                  <button className={depositRate === "0.05" && !depositAmount ? "selected" : ""} onClick={() => { setDepositRate("0.05"); setDepositAmount(""); }} type="button">
                    5%
                  </button>
                  <button className={depositRate === "0.10" && !depositAmount ? "selected" : ""} onClick={() => { setDepositRate("0.10"); setDepositAmount(""); }} type="button">
                    10%
                  </button>
                  <button className={depositAmount ? "selected" : ""} onClick={() => setDepositAmount(calculatedDeposit ? calculatedDeposit.toFixed(2) : "")} type="button">
                    Custom
                  </button>
                </div>
                <div className="formGrid">
                  <label>
                    Deposit Amount
                    <input
                      min="0.01"
                      step="0.01"
                      type="number"
                      value={depositAmount}
                      onChange={(event) => setDepositAmount(event.target.value)}
                      placeholder={calculatedDeposit ? calculatedDeposit.toFixed(2) : "Auto from rate"}
                    />
                  </label>
                  <label>
                    Deposit Due
                    <input type="date" value={depositDueDate} onChange={(event) => setDepositDueDate(event.target.value)} />
                  </label>
                </div>
                <label>
                  Deposit Status
                  <select value={depositStatus} onChange={(event) => setDepositStatus(event.target.value as DepositStatus)}>
                    <option value="requested">Requested</option>
                    <option value="invoiced">Invoiced</option>
                    <option value="paid">Paid</option>
                    <option value="applied">Applied</option>
                  </select>
                </label>
                <div className="statusNote">Deposit preview: {formatMoney(calculatedDeposit.toFixed(2))}</div>
              </>
            ) : null}
          </div>
        </div>

        <div className="lineEditor">
          {lines.map((line, index) => (
            <div className="poLine" key={index}>
              <label>
                Description
                <input value={line.description} onChange={(event) => updateLine(index, { description: event.target.value })} />
              </label>
              <div className="formGrid">
                <label>
                  Qty
                  <input min="0.001" step="0.001" type="number" value={line.quantity} onChange={(event) => updateLine(index, { quantity: event.target.value })} />
                </label>
                <label>
                  Unit Price
                  <input min="0" step="0.01" type="number" value={line.unit_price} onChange={(event) => updateLine(index, { unit_price: event.target.value })} />
                </label>
              </div>
              <div className="formGrid">
                <label>
                  Tax
                  <input min="0" step="0.01" type="number" value={line.tax_amount} onChange={(event) => updateLine(index, { tax_amount: event.target.value })} />
                </label>
                <label>
                  Revenue Account
                  <select value={line.revenue_account_id} onChange={(event) => updateLine(index, { revenue_account_id: Number(event.target.value) })}>
                    <option value="">Select</option>
                    {revenueAccounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.code} {account.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button className="smallButton" disabled={lines.length === 1} onClick={() => removeLine(index)} type="button">
                Remove Line
              </button>
            </div>
          ))}
          <button className="smallButton" onClick={addLine} type="button">
            <Plus size={14} />
            Add Line
          </button>
        </div>

        <label>
          Delivery Instructions
          <input value={deliveryInstructions} onChange={(event) => setDeliveryInstructions(event.target.value)} />
        </label>
        <label>
          Notes
          <input value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <button className="primaryButton" disabled={!canSave || saving} type="submit">
          <Plus size={18} />
          {saving ? "Saving" : "Save Sales Booking"}
        </button>
        {message ? <p className="formMessage">{message}</p> : null}
      </form>
    </section>
  );
}

function SalesOrderList({
  loading,
  salesOrders,
  onChanged
}: {
  loading: boolean;
  salesOrders: SalesOrder[];
  onChanged: () => void;
}) {
  if (loading) return <div className="empty">Loading client purchase orders...</div>;
  if (!salesOrders.length) return <div className="empty">No client purchase orders yet.</div>;

  async function accept(id: number) {
    await api.acceptSalesOrder(id);
    onChanged();
  }

  async function cancel(id: number) {
    await api.cancelSalesOrder(id);
    onChanged();
  }

  return (
    <div className="entryList">
      {salesOrders.map((order) => (
        <article className="entry" key={order.id}>
          <div className="entryHeader">
            <div>
              <strong>{order.order_number}</strong>
              <span>
                {displayClientPo(order.client_po_number)} - {order.received_date} - {order.status}
              </span>
            </div>
            <span>{formatMoney(order.total)}</span>
          </div>
          <div className="transactionMeta purchaseMeta">
            <span>{order.customer.name}</span>
            <span>{order.expected_delivery_date ?? "No delivery date"}</span>
            <span>{order.deposit_required ? `${formatMoney(order.deposit_amount)} deposit - ${order.deposit_status}` : "No deposit"}</span>
            <span>{order.payment_terms ?? "No terms"}</span>
            <div className="rowActions">
              {["draft", "received"].includes(order.status) ? (
                <button className="smallButton" onClick={() => void accept(order.id)} type="button">
                  Accept
                </button>
              ) : null}
              {["draft", "received", "accepted"].includes(order.status) ? (
                <button className="smallButton" onClick={() => void cancel(order.id)} type="button">
                  Cancel
                </button>
              ) : null}
            </div>
          </div>
          <div className="transactionMeta purchaseMeta">
            <span>Ordered {formatMoney(order.total)}</span>
            <span>Invoiced {formatMoney(order.invoiced_total)}</span>
            <span>Paid {formatMoney(order.paid_total)}</span>
            <span>Unbilled {formatMoney(order.unbilled_total)}</span>
          </div>
          <div className="entryLines poLines">
            {order.lines.slice(0, 4).map((line) => (
              <div key={line.id}>
                <span>{line.description}</span>
                <span>
                  {line.quantity} x {formatMoney(line.unit_price)}
                </span>
                <span>{formatMoney(line.line_total)}</span>
              </div>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

function PurchasingView({
  accounts,
  contacts,
  loading,
  purchaseOrders,
  onChanged
}: {
  accounts: Account[];
  contacts: Contact[];
  loading: boolean;
  purchaseOrders: PurchaseOrder[];
  onChanged: () => void;
}) {
  const vendorContacts = contacts.filter((contact) => contact.type === "vendor" || contact.type === "both");

  return (
    <>
      <div className="workspace">
        <ContactForm accounts={accounts} fixedType="vendor" title="New Vendor" subtitle="Purchasing master record" onCreated={onChanged} />
        <section className="panel">
          <div className="panelHeader">
            <h2>Vendor Master</h2>
            <span>{vendorContacts.length} vendors</span>
          </div>
          {loading ? <div className="empty">Loading vendors...</div> : <ContactList contacts={vendorContacts} />}
        </section>
      </div>
      <div className="workspace">
        <PurchaseOrderForm accounts={accounts} contacts={contacts} onCreated={onChanged} />
        <section className="panel">
          <div className="panelHeader">
            <h2>Purchase Orders</h2>
            <span>{purchaseOrders.length} records</span>
          </div>
          <PurchaseOrderList loading={loading} purchaseOrders={purchaseOrders} onChanged={onChanged} />
        </section>
      </div>
    </>
  );
}

function PurchaseOrderForm({ accounts, contacts, onCreated }: { accounts: Account[]; contacts: Contact[]; onCreated: () => void }) {
  const expenseAccounts = accounts.filter((account) => account.type === "expense");
  const vendorContacts = contacts.filter((contact) => contact.type === "vendor" || contact.type === "both");
  const firstExpenseId = expenseAccounts[0]?.id ?? "";
  const [status, setStatus] = useState<PurchaseOrderStatus>("draft");
  const [poNumber, setPoNumber] = useState("");
  const [vendorId, setVendorId] = useState<number | "">("");
  const [issueDate, setIssueDate] = useState(today());
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState("");
  const [currency, setCurrency] = useState("SGD");
  const [paymentTerms, setPaymentTerms] = useState("");
  const [notes, setNotes] = useState("");
  const [deliveryInstructions, setDeliveryInstructions] = useState("");
  const [lines, setLines] = useState<PurchaseOrderDraftLine[]>([
    { description: "Professional service", quantity: "1", unit_price: "100.00", tax_amount: "0.00", expense_account_id: firstExpenseId }
  ]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!firstExpenseId || !lines.length || lines.some((line) => line.expense_account_id !== "")) return;
    setLines((current) => current.map((line) => ({ ...line, expense_account_id: firstExpenseId })));
  }, [firstExpenseId, lines]);

  const selectedVendor = vendorContacts.find((contact) => contact.id === vendorId);
  const canIssue = selectedVendor?.vendor_qualification_status === "qualified";
  const total = lines.reduce((sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_price || 0) + Number(line.tax_amount || 0), 0);
  const canSave =
    Boolean(vendorId && issueDate && currency.length === 3 && lines.length) &&
    lines.every((line) => line.description && Number(line.quantity) > 0 && Number(line.unit_price) >= 0 && Number(line.tax_amount) >= 0 && line.expense_account_id);

  useEffect(() => {
    if (selectedVendor?.payment_terms) {
      setPaymentTerms(selectedVendor.payment_terms);
    }
  }, [selectedVendor?.id]);

  function updateLine(index: number, changes: Partial<PurchaseOrderDraftLine>) {
    setLines((current) => current.map((line, lineIndex) => (lineIndex === index ? { ...line, ...changes } : line)));
  }

  function addLine() {
    setLines((current) => [
      ...current,
      { description: "", quantity: "1", unit_price: "0.00", tax_amount: "0.00", expense_account_id: firstExpenseId }
    ]);
  }

  function removeLine(index: number) {
    setLines((current) => (current.length === 1 ? current : current.filter((_, lineIndex) => lineIndex !== index)));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave || vendorId === "") return;

    const payload: PurchaseOrderPayload = {
      po_number: poNumber || undefined,
      status,
      vendor_id: vendorId,
      issue_date: issueDate,
      expected_delivery_date: expectedDeliveryDate || undefined,
      currency,
      payment_terms: paymentTerms || undefined,
      notes: notes || undefined,
      delivery_instructions: deliveryInstructions || undefined,
      lines: lines.map((line) => ({
        description: line.description,
        quantity: line.quantity,
        unit_price: line.unit_price,
        tax_amount: line.tax_amount,
        expense_account_id: Number(line.expense_account_id)
      }))
    };

    setSaving(true);
    setMessage(null);
    try {
      await api.createPurchaseOrder(payload);
      setPoNumber("");
      setPaymentTerms("");
      setNotes("");
      setDeliveryInstructions("");
      setMessage("Purchase order saved.");
      onCreated();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to save purchase order.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>New Purchase Order</h2>
        <span>{formatMoney(total)}</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <div className="formGrid">
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value as PurchaseOrderStatus)}>
              <option value="draft">Draft</option>
              <option value="issued">Issued</option>
            </select>
          </label>
          <label>
            PO Number
            <input value={poNumber} onChange={(event) => setPoNumber(event.target.value)} placeholder="Auto if blank" />
          </label>
        </div>
        <label>
          Vendor
          <select value={vendorId} onChange={(event) => setVendorId(event.target.value ? Number(event.target.value) : "")}>
            <option value="">Select vendor</option>
            {vendorContacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name} ({qualificationLabel(contact.vendor_qualification_status)})
              </option>
            ))}
          </select>
        </label>
        {selectedVendor ? (
          <div className={canIssue ? "statusNote" : "statusNote warning"}>
            {selectedVendor.name} is {qualificationLabel(selectedVendor.vendor_qualification_status)}.
          </div>
        ) : null}
        <div className="formGrid">
          <label>
            Issue Date
            <input type="date" value={issueDate} onChange={(event) => setIssueDate(event.target.value)} />
          </label>
          <label>
            Expected Delivery
            <input type="date" value={expectedDeliveryDate} onChange={(event) => setExpectedDeliveryDate(event.target.value)} />
          </label>
        </div>
        <label>
          Currency
          <input maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} />
        </label>
        <label>
          Payment Terms
          <input value={paymentTerms} onChange={(event) => setPaymentTerms(event.target.value)} placeholder="From proposal or accepted quote" />
        </label>

        <div className="lineEditor">
          {lines.map((line, index) => (
            <div className="poLine" key={index}>
              <label>
                Description
                <input value={line.description} onChange={(event) => updateLine(index, { description: event.target.value })} />
              </label>
              <div className="formGrid">
                <label>
                  Qty
                  <input min="0.001" step="0.001" type="number" value={line.quantity} onChange={(event) => updateLine(index, { quantity: event.target.value })} />
                </label>
                <label>
                  Unit Price
                  <input min="0" step="0.01" type="number" value={line.unit_price} onChange={(event) => updateLine(index, { unit_price: event.target.value })} />
                </label>
              </div>
              <div className="formGrid">
                <label>
                  Tax
                  <input min="0" step="0.01" type="number" value={line.tax_amount} onChange={(event) => updateLine(index, { tax_amount: event.target.value })} />
                </label>
                <label>
                  Expense Account
                  <select value={line.expense_account_id} onChange={(event) => updateLine(index, { expense_account_id: Number(event.target.value) })}>
                    <option value="">Select</option>
                    {expenseAccounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.code} {account.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button className="smallButton" disabled={lines.length === 1} onClick={() => removeLine(index)} type="button">
                Remove Line
              </button>
            </div>
          ))}
          <button className="smallButton" onClick={addLine} type="button">
            <Plus size={14} />
            Add Line
          </button>
        </div>

        <label>
          Delivery Instructions
          <input value={deliveryInstructions} onChange={(event) => setDeliveryInstructions(event.target.value)} />
        </label>
        <label>
          Notes
          <input value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <button className="primaryButton" disabled={!canSave || saving || (status === "issued" && !canIssue)} type="submit">
          <Plus size={18} />
          {saving ? "Saving" : "Save PO"}
        </button>
        {message ? <p className="formMessage">{message}</p> : null}
      </form>
    </section>
  );
}

function PurchaseOrderList({
  loading,
  purchaseOrders,
  onChanged
}: {
  loading: boolean;
  purchaseOrders: PurchaseOrder[];
  onChanged: () => void;
}) {
  if (loading) return <div className="empty">Loading purchase orders...</div>;
  if (!purchaseOrders.length) return <div className="empty">No purchase orders yet.</div>;

  async function issue(id: number) {
    await api.issuePurchaseOrder(id);
    onChanged();
  }

  async function cancel(id: number) {
    await api.cancelPurchaseOrder(id);
    onChanged();
  }

  return (
    <div className="entryList">
      {purchaseOrders.map((order) => (
        <article className="entry" key={order.id}>
          <div className="entryHeader">
            <div>
              <strong>{order.po_number}</strong>
              <span>
                {order.issue_date} - {order.status}
              </span>
            </div>
            <span>{formatMoney(order.total)}</span>
          </div>
          <div className="transactionMeta purchaseMeta">
            <span>{order.vendor.name}</span>
            <span>{qualificationLabel(order.vendor.vendor_qualification_status)}</span>
            <span>{order.payment_terms ?? "No PO terms"}</span>
            <div className="rowActions">
              {order.status === "draft" ? (
                <button className="smallButton" disabled={order.vendor.vendor_qualification_status !== "qualified"} onClick={() => void issue(order.id)} type="button">
                  Issue
                </button>
              ) : null}
              {["draft", "issued", "partially_received"].includes(order.status) ? (
                <button className="smallButton" onClick={() => void cancel(order.id)} type="button">
                  Cancel
                </button>
              ) : null}
            </div>
          </div>
          <div className="entryLines poLines">
            {order.lines.slice(0, 4).map((line) => (
              <div key={line.id}>
                <span>{line.description}</span>
                <span>
                  {line.quantity} x {formatMoney(line.unit_price)}
                </span>
                <span>{formatMoney(line.line_total)}</span>
              </div>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

function qualificationLabel(status: VendorQualificationStatus) {
  if (status === "qualified") return "Qualified";
  if (status === "suspended") return "Suspended";
  if (status === "rejected") return "Rejected";
  return "Pending";
}

function EmployeesView({ employees, loading, onChanged }: { employees: Employee[]; loading: boolean; onChanged: () => void }) {
  return (
    <div className="workspace">
      <EmployeeForm onCreated={onChanged} />
      <section className="panel">
        <div className="panelHeader">
          <h2>Employee Master</h2>
          <span>{employees.length} employees</span>
        </div>
        {loading ? <div className="empty">Loading employees...</div> : <EmployeeList employees={employees} />}
      </section>
    </div>
  );
}

function EmployeeForm({ onCreated }: { onCreated: () => void }) {
  const [staffId, setStaffId] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [status, setStatus] = useState<EmployeeStatus>("active");
  const [startDate, setStartDate] = useState("");
  const [monthlySalary, setMonthlySalary] = useState("3000.00");
  const [cpfProfile, setCpfProfile] = useState<CpfProfile>("sc_or_third_year_pr_55_below");
  const [employeeCpfRate, setEmployeeCpfRate] = useState("20");
  const [employerCpfRate, setEmployerCpfRate] = useState("17");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (cpfProfile === "sc_or_third_year_pr_55_below") {
      setEmployeeCpfRate("20");
      setEmployerCpfRate("17");
    }
    if (cpfProfile === "not_applicable") {
      setEmployeeCpfRate("0");
      setEmployerCpfRate("0");
    }
  }, [cpfProfile]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name || Number(monthlySalary) <= 0) return;

    const payload: EmployeePayload = {
      staff_id: staffId || undefined,
      name,
      email: email || undefined,
      phone: phone || undefined,
      job_title: jobTitle || undefined,
      status,
      start_date: startDate || undefined,
      monthly_salary: monthlySalary,
      cpf_profile: cpfProfile,
      employee_cpf_rate: (Number(employeeCpfRate) / 100).toFixed(4),
      employer_cpf_rate: (Number(employerCpfRate) / 100).toFixed(4),
      notes: notes || undefined
    };

    setSaving(true);
    setMessage(null);
    try {
      await api.createEmployee(payload);
      setStaffId("");
      setName("");
      setEmail("");
      setPhone("");
      setJobTitle("");
      setStartDate("");
      setNotes("");
      setMessage("Employee saved.");
      onCreated();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to save employee.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>New Employee</h2>
        <span>HR master data</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <div className="formGrid">
          <label>
            Staff ID
            <input value={staffId} onChange={(event) => setStaffId(event.target.value)} />
          </label>
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value as EmployeeStatus)}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </label>
        </div>
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Job Title
          <input value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} />
        </label>
        <div className="formGrid">
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            Phone
            <input value={phone} onChange={(event) => setPhone(event.target.value)} />
          </label>
        </div>
        <label>
          Start Date
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        </label>
        <label>
          Current Monthly Salary
          <input min="0.01" step="0.01" type="number" value={monthlySalary} onChange={(event) => setMonthlySalary(event.target.value)} />
        </label>
        <label>
          CPF Profile
          <select value={cpfProfile} onChange={(event) => setCpfProfile(event.target.value as CpfProfile)}>
            <option value="sc_or_third_year_pr_55_below">SC / 3rd-year PR, 55 and below</option>
            <option value="custom">Custom rates</option>
            <option value="not_applicable">Not applicable</option>
          </select>
        </label>
        <div className="formGrid">
          <label>
            Employee CPF %
            <input
              disabled={cpfProfile !== "custom"}
              min="0"
              max="100"
              step="0.01"
              type="number"
              value={employeeCpfRate}
              onChange={(event) => setEmployeeCpfRate(event.target.value)}
            />
          </label>
          <label>
            Employer CPF %
            <input
              disabled={cpfProfile !== "custom"}
              min="0"
              max="100"
              step="0.01"
              type="number"
              value={employerCpfRate}
              onChange={(event) => setEmployerCpfRate(event.target.value)}
            />
          </label>
        </div>
        <label>
          Notes
          <input value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <button className="primaryButton" disabled={!name || Number(monthlySalary) <= 0 || saving} type="submit">
          <Plus size={18} />
          {saving ? "Saving" : "Add Employee"}
        </button>
        {message ? <p className="formMessage">{message}</p> : null}
      </form>
    </section>
  );
}

function EmployeeList({ employees }: { employees: Employee[] }) {
  if (!employees.length) return <div className="empty">No employees yet.</div>;
  return (
    <div className="entryList">
      {employees.map((employee) => (
        <article className="entry" key={employee.id}>
          <div className="entryHeader">
            <div>
              <strong>{employee.name}</strong>
              <span>
                {employee.staff_id ?? "No staff ID"} Â· {employee.status}
              </span>
            </div>
            <span>{formatMoney(employee.monthly_salary)}</span>
          </div>
          <div className="transactionMeta employeeMeta">
            <span>{employee.job_title ?? "No job title"}</span>
            <span>{employee.email ?? "No email"}</span>
            <span>{employee.start_date ?? "No start date"}</span>
            <span>{cpfProfileLabel(employee.cpf_profile)}</span>
          </div>
        </article>
      ))}
    </div>
  );
}

function cpfProfileLabel(profile: CpfProfile) {
  if (profile === "sc_or_third_year_pr_55_below") return "SC / 3rd-year PR, 55 and below";
  if (profile === "not_applicable") return "CPF not applicable";
  return "Custom CPF";
}

function HrPayrollView({
  accounts,
  employees,
  loading,
  payrollRuns,
  settings,
  onChanged
}: {
  accounts: Account[];
  employees: Employee[];
  loading: boolean;
  payrollRuns: PayrollRun[];
  settings: CompanySettings | null;
  onChanged: () => void;
}) {
  const [selectedPayslip, setSelectedPayslip] = useState<PayrollRun | null>(null);

  return (
    <>
      <div className="workspace">
        <EmployeeForm onCreated={onChanged} />
        <section className="panel">
          <div className="panelHeader">
            <h2>Employee Master</h2>
            <span>{employees.length} employees</span>
          </div>
          {loading ? <div className="empty">Loading employees...</div> : <EmployeeList employees={employees} />}
        </section>
      </div>
      <div className="workspace">
        <PayrollForm accounts={accounts} employees={employees} onCreated={onChanged} />
        <section className="panel">
          <div className="panelHeader">
            <h2>Payroll Runs</h2>
            <span>{payrollRuns.length} records</span>
          </div>
          <PayrollList loading={loading} payrollRuns={payrollRuns} onPost={onChanged} onPrint={setSelectedPayslip} />
        </section>
      </div>
      {selectedPayslip ? (
        <PayslipModal
          payrollRun={selectedPayslip}
          companyName={settings?.company_name ?? "IntelliArtAI"}
          registrationNumber={settings?.registration_number ?? null}
          onClose={() => setSelectedPayslip(null)}
        />
      ) : null}
    </>
  );
}

function PayrollForm({ accounts, employees, onCreated }: { accounts: Account[]; employees: Employee[]; onCreated: () => void }) {
  const [status, setStatus] = useState<PayrollStatus>("posted");
  const [employeeId, setEmployeeId] = useState<number | "">("");
  const [employeeName, setEmployeeName] = useState("");
  const [periodStart, setPeriodStart] = useState(today().slice(0, 8) + "01");
  const [periodEnd, setPeriodEnd] = useState(today());
  const [payDate, setPayDate] = useState(today());
  const [grossSalary, setGrossSalary] = useState("3000.00");
  const [cpfSubjectWage, setCpfSubjectWage] = useState("3000.00");
  const [employeeCpfRate, setEmployeeCpfRate] = useState("20");
  const [employerCpfRate, setEmployerCpfRate] = useState("17");
  const [salaryAccountId, setSalaryAccountId] = useState<number | "">("");
  const [employerCpfAccountId, setEmployerCpfAccountId] = useState<number | "">("");
  const [cashAccountId, setCashAccountId] = useState<number | "">("");
  const [cpfPayableAccountId, setCpfPayableAccountId] = useState<number | "">("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const expenseAccounts = accounts.filter((account) => account.type === "expense");
  const assetAccounts = accounts.filter((account) => account.type === "asset");
  const liabilityAccounts = accounts.filter((account) => account.type === "liability");
  const activeEmployees = employees.filter((employee) => employee.status === "active");

  useEffect(() => {
    if (!accounts.length) return;
    setSalaryAccountId(expenseAccounts.find((account) => account.code === "5300")?.id ?? expenseAccounts[0]?.id ?? "");
    setEmployerCpfAccountId(expenseAccounts.find((account) => account.code === "5310")?.id ?? expenseAccounts[0]?.id ?? "");
    setCashAccountId(assetAccounts.find((account) => account.code === "1010")?.id ?? assetAccounts[0]?.id ?? "");
    setCpfPayableAccountId(liabilityAccounts.find((account) => account.code === "2100")?.id ?? liabilityAccounts[0]?.id ?? "");
  }, [accounts]);

  useEffect(() => {
    if (employeeId === "") return;
    const employee = employees.find((item) => item.id === employeeId);
    if (!employee) return;
    setEmployeeName(employee.name);
    setGrossSalary(Number(employee.monthly_salary).toFixed(2));
    setCpfSubjectWage(Math.min(Number(employee.monthly_salary), 8000).toFixed(2));
    setEmployeeCpfRate((Number(employee.employee_cpf_rate) * 100).toString());
    setEmployerCpfRate((Number(employee.employer_cpf_rate) * 100).toString());
  }, [employeeId, employees]);

  useEffect(() => {
    const gross = Number(grossSalary);
    if (!Number.isFinite(gross) || gross <= 0) return;
    setCpfSubjectWage(Math.min(gross, 8000).toFixed(2));
  }, [grossSalary]);

  const payrollPreview = useMemo(() => {
    const subjectWage = Number(cpfSubjectWage);
    const employeeRate = Number(employeeCpfRate) / 100;
    const employerRate = Number(employerCpfRate) / 100;
    const gross = Number(grossSalary);
    if (![subjectWage, employeeRate, employerRate, gross].every(Number.isFinite)) {
      return { employeeCpf: 0, employerCpf: 0, netPay: 0, totalCpf: 0 };
    }
    const employeeCpf = Math.floor(subjectWage * employeeRate);
    const totalCpf = Math.round(subjectWage * (employeeRate + employerRate));
    const employerCpf = totalCpf - employeeCpf;
    return {
      employeeCpf,
      employerCpf,
      netPay: gross - employeeCpf,
      totalCpf
    };
  }, [cpfSubjectWage, employeeCpfRate, employerCpfRate, grossSalary]);

  const canSave = Boolean(
    employeeName &&
      periodStart &&
      periodEnd &&
      payDate &&
      Number(grossSalary) > 0 &&
      Number(cpfSubjectWage) >= 0 &&
      salaryAccountId &&
      employerCpfAccountId &&
      cashAccountId &&
      cpfPayableAccountId
  );

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave || salaryAccountId === "" || employerCpfAccountId === "" || cashAccountId === "" || cpfPayableAccountId === "") return;

    const payload: PayrollRunPayload = {
      status,
      employee_id: employeeId === "" ? undefined : employeeId,
      employee_name: employeeName,
      period_start: periodStart,
      period_end: periodEnd,
      pay_date: payDate,
      gross_salary: grossSalary,
      cpf_subject_wage: cpfSubjectWage,
      employee_cpf_rate: (Number(employeeCpfRate) / 100).toFixed(4),
      employer_cpf_rate: (Number(employerCpfRate) / 100).toFixed(4),
      salary_account_id: salaryAccountId,
      employer_cpf_account_id: employerCpfAccountId,
      cash_account_id: cashAccountId,
      cpf_payable_account_id: cpfPayableAccountId,
      notes: notes || undefined
    };

    setSaving(true);
    setMessage(null);
    try {
      await api.createPayroll(payload);
      setEmployeeName("");
      setNotes("");
      setMessage("Payroll saved.");
      onCreated();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to save payroll.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>Run Payroll</h2>
        <span>Singapore CPF</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <label>
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value as PayrollStatus)}>
            <option value="draft">Draft</option>
            <option value="posted">Posted</option>
          </select>
        </label>
        <label>
          Employee
          <select value={employeeId} onChange={(event) => setEmployeeId(event.target.value ? Number(event.target.value) : "")}>
            <option value="">Manual entry</option>
            {activeEmployees.map((employee) => (
              <option key={employee.id} value={employee.id}>
                {employee.name} {employee.staff_id ? `(${employee.staff_id})` : ""}
              </option>
            ))}
          </select>
        </label>
        <label>
          Employee Name
          <input value={employeeName} onChange={(event) => setEmployeeName(event.target.value)} />
        </label>
        <div className="formGrid">
          <label>
            Period Start
            <input type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} />
          </label>
          <label>
            Period End
            <input type="date" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} />
          </label>
        </div>
        <label>
          Pay Date
          <input type="date" value={payDate} onChange={(event) => setPayDate(event.target.value)} />
        </label>
        <label>
          Gross Salary
          <input min="0.01" step="0.01" type="number" value={grossSalary} onChange={(event) => setGrossSalary(event.target.value)} />
        </label>
        <label>
          CPF Subject Wage
          <input min="0" step="0.01" type="number" value={cpfSubjectWage} onChange={(event) => setCpfSubjectWage(event.target.value)} />
        </label>
        <div className="formGrid">
          <label>
            Employee CPF %
            <input min="0" max="100" step="0.01" type="number" value={employeeCpfRate} onChange={(event) => setEmployeeCpfRate(event.target.value)} />
          </label>
          <label>
            Employer CPF %
            <input min="0" max="100" step="0.01" type="number" value={employerCpfRate} onChange={(event) => setEmployerCpfRate(event.target.value)} />
          </label>
        </div>
        <div className="payrollPreview">
          <span>Employee CPF {formatMoney(payrollPreview.employeeCpf)}</span>
          <span>Employer CPF {formatMoney(payrollPreview.employerCpf)}</span>
          <span>Net pay {formatMoney(payrollPreview.netPay)}</span>
        </div>
        <label>
          Salary Expense
          <select value={salaryAccountId} onChange={(event) => setSalaryAccountId(Number(event.target.value))}>
            {expenseAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} {account.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Employer CPF Expense
          <select value={employerCpfAccountId} onChange={(event) => setEmployerCpfAccountId(Number(event.target.value))}>
            {expenseAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} {account.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Paid From
          <select value={cashAccountId} onChange={(event) => setCashAccountId(Number(event.target.value))}>
            {assetAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} {account.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          CPF Payable
          <select value={cpfPayableAccountId} onChange={(event) => setCpfPayableAccountId(Number(event.target.value))}>
            {liabilityAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} {account.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Notes
          <input value={notes} onChange={(event) => setNotes(event.target.value)} />
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

function PayrollList({
  loading,
  payrollRuns,
  onPost,
  onPrint
}: {
  loading: boolean;
  payrollRuns: PayrollRun[];
  onPost: () => void;
  onPrint: (payrollRun: PayrollRun) => void;
}) {
  if (loading) return <div className="empty">Loading payroll...</div>;
  if (!payrollRuns.length) return <div className="empty">No payroll runs yet.</div>;

  async function post(id: number) {
    await api.postPayroll(id);
    onPost();
  }

  return (
    <div className="entryList">
      {payrollRuns.map((run) => (
        <article className="entry" key={run.id}>
          <div className="entryHeader">
            <div>
              <strong>{run.employee_name}</strong>
              <span>
                {run.period_start} to {run.period_end} Â· {run.status}
              </span>
            </div>
            <span>{formatMoney(run.gross_salary)}</span>
          </div>
          <div className="transactionMeta payrollMeta">
            <span>Net {formatMoney(run.net_pay)}</span>
            <span>Employee CPF {formatMoney(run.employee_cpf)}</span>
            <span>Employer CPF {formatMoney(run.employer_cpf)}</span>
            <div className="rowActions">
              {run.status !== "posted" ? (
                <button className="smallButton" onClick={() => void post(run.id)} type="button">
                  Post
                </button>
              ) : null}
              <button className="smallButton" onClick={() => onPrint(run)} type="button">
                <Printer size={14} />
                Payslip
              </button>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function PayslipModal({
  companyName,
  registrationNumber,
  payrollRun,
  onClose
}: {
  companyName: string;
  registrationNumber: string | null;
  payrollRun: PayrollRun;
  onClose: () => void;
}) {
  return (
    <div className="payslipOverlay" role="dialog" aria-modal="true" aria-label="Salary slip">
      <section className="payslipSheet printArea">
        <div className="payslipActions noPrint">
          <button className="smallButton" onClick={onClose} type="button">
            Close
          </button>
          <button className="primaryButton" onClick={() => window.print()} type="button">
            <Printer size={18} />
            Print
          </button>
        </div>

        <header className="payslipHeader">
          <div>
            <p className="eyebrow">Itemised Pay Slip</p>
            <h2>{companyName}</h2>
            {registrationNumber ? <span>Registration No. {registrationNumber}</span> : null}
          </div>
          <div>
            <strong>Pay Date</strong>
            <span>{payrollRun.pay_date}</span>
          </div>
        </header>

        <div className="payslipGrid">
          <PayslipField label="Employee" value={payrollRun.employee_name} />
          <PayslipField label="Salary Period" value={`${payrollRun.period_start} to ${payrollRun.period_end}`} />
          <PayslipField label="Status" value={payrollRun.status} />
          <PayslipField label="Reference" value={`PAY-${payrollRun.id}`} />
        </div>

        <div className="payslipColumns">
          <section>
            <h3>Earnings</h3>
            <PayslipLine label="Basic salary" value={payrollRun.gross_salary} />
            <PayslipLine label="Gross salary" value={payrollRun.gross_salary} strong />
          </section>
          <section>
            <h3>Deductions</h3>
            <PayslipLine label="Employee CPF" value={payrollRun.employee_cpf} />
            <PayslipLine label="Total deductions" value={payrollRun.employee_cpf} strong />
          </section>
        </div>

        <section className="payslipSummary">
          <PayslipLine label="Net salary paid" value={payrollRun.net_pay} strong />
          <PayslipLine label="Employer CPF contribution" value={payrollRun.employer_cpf} />
          <PayslipLine label="Total CPF payable" value={Number(payrollRun.employee_cpf) + Number(payrollRun.employer_cpf)} />
        </section>

        {payrollRun.notes ? <p className="payslipNotes">{payrollRun.notes}</p> : null}
      </section>
    </div>
  );
}

function PayslipField({ label, value }: { label: string; value: string }) {
  return (
    <div className="payslipField">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PayslipLine({ label, strong = false, value }: { label: string; strong?: boolean; value: string | number }) {
  return (
    <div className={strong ? "payslipLine strong" : "payslipLine"}>
      <span>{label}</span>
      <span>{formatMoney(value)}</span>
    </div>
  );
}

function ContactsView({
  accounts,
  contacts,
  loading,
  onChanged
}: {
  accounts: Account[];
  contacts: Contact[];
  loading: boolean;
  onChanged: () => void;
}) {
  return (
    <div className="workspace">
      <ContactForm accounts={accounts} onCreated={onChanged} />
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

function ContactForm({
  accounts,
  fixedType,
  title = "New Contact",
  subtitle = "Customer or vendor",
  onCreated
}: {
  accounts: Account[];
  fixedType?: ContactPayload["type"];
  title?: string;
  subtitle?: string;
  onCreated: () => void;
}) {
  const expenseAccounts = accounts.filter((account) => account.type === "expense");
  const [name, setName] = useState("");
  const [type, setType] = useState<ContactPayload["type"]>(fixedType ?? "vendor");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [taxIdentifier, setTaxIdentifier] = useState("");
  const [vendorQualificationStatus, setVendorQualificationStatus] = useState<VendorQualificationStatus>("pending");
  const [paymentTerms, setPaymentTerms] = useState("Net 30");
  const [defaultExpenseAccountId, setDefaultExpenseAccountId] = useState<number | "">("");
  const [qualificationExpiresOn, setQualificationExpiresOn] = useState("");
  const [qualificationNotes, setQualificationNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const isVendor = type === "vendor" || type === "both";

  useEffect(() => {
    if (fixedType) {
      setType(fixedType);
    }
  }, [fixedType]);

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
        phone: phone || undefined,
        tax_identifier: taxIdentifier || undefined,
        vendor_qualification_status: isVendor ? vendorQualificationStatus : "pending",
        payment_terms: paymentTerms || undefined,
        default_expense_account_id: isVendor && defaultExpenseAccountId !== "" ? defaultExpenseAccountId : undefined,
        qualification_expires_on: isVendor ? qualificationExpiresOn || undefined : undefined,
        qualification_notes: isVendor ? qualificationNotes || undefined : undefined
      });
      setName("");
      setEmail("");
      setPhone("");
      setTaxIdentifier("");
      setQualificationExpiresOn("");
      setQualificationNotes("");
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
        <h2>{title}</h2>
        <span>{subtitle}</span>
      </div>
      <form className="transactionForm" onSubmit={(event) => void submit(event)}>
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        {fixedType ? null : (
          <label>
            Type
            <select value={type} onChange={(event) => setType(event.target.value as ContactPayload["type"])}>
              <option value="vendor">Vendor</option>
              <option value="customer">Customer</option>
              <option value="both">Both</option>
            </select>
          </label>
        )}
        <label>
          Email
          <input value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label>
          Phone
          <input value={phone} onChange={(event) => setPhone(event.target.value)} />
        </label>
        <label>
          Tax Identifier
          <input value={taxIdentifier} onChange={(event) => setTaxIdentifier(event.target.value)} />
        </label>
        <label>
          Default Payment Terms
          <input value={paymentTerms} onChange={(event) => setPaymentTerms(event.target.value)} />
        </label>
        {isVendor ? (
          <>
            <label>
              Vendor Qualification
              <select value={vendorQualificationStatus} onChange={(event) => setVendorQualificationStatus(event.target.value as VendorQualificationStatus)}>
                <option value="pending">Pending</option>
                <option value="qualified">Qualified</option>
                <option value="suspended">Suspended</option>
                <option value="rejected">Rejected</option>
              </select>
            </label>
            <label>
              Default Expense Account
              <select value={defaultExpenseAccountId} onChange={(event) => setDefaultExpenseAccountId(event.target.value ? Number(event.target.value) : "")}>
                <option value="">None</option>
                {expenseAccounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.code} {account.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Qualification Expiry
              <input type="date" value={qualificationExpiresOn} onChange={(event) => setQualificationExpiresOn(event.target.value)} />
            </label>
            <label>
              Qualification Notes
              <input value={qualificationNotes} onChange={(event) => setQualificationNotes(event.target.value)} />
            </label>
          </>
        ) : null}
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

function SettingsView({
  accounts,
  loading,
  settings,
  onChanged
}: {
  accounts: Account[];
  loading: boolean;
  settings: CompanySettings;
  onChanged: () => void;
}) {
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
    <>
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

      <section className="panel">
        <div className="panelHeader">
          <h2>Chart of Accounts Setup</h2>
          <span>{accounts.length} accounts</span>
        </div>
        <ChartOfAccountsTools onChanged={onChanged} />
        <div className="printArea">
          <div className="printHeader">
            <h2>Chart of Accounts</h2>
            <span>Generated {today()}</span>
          </div>
          <AccountsTable accounts={accounts} loading={loading} />
        </div>
      </section>
    </>
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
  const [extractingReceiptId, setExtractingReceiptId] = useState<number | null>(null);

  if (loading) return <div className="empty">Loading transactions...</div>;
  if (!transactions.length) return <div className="empty">No operational transactions yet.</div>;

  async function post(id: number) {
    await api.postTransaction(id);
    onPost?.();
  }

  async function extract(receiptId: number) {
    setExtractingReceiptId(receiptId);
    try {
      await api.extractReceipt(receiptId);
      onPost?.();
    } finally {
      setExtractingReceiptId(null);
    }
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
              <div className="rowActions">
                {transaction.receipt ? (
                  <button
                    className="smallButton"
                    disabled={extractingReceiptId === transaction.receipt.id}
                    onClick={() => void extract(transaction.receipt!.id)}
                    type="button"
                  >
                    {extractingReceiptId === transaction.receipt.id ? "Extracting" : "Extract"}
                  </button>
                ) : null}
                {transaction.status !== "posted" ? (
                  <button className="smallButton" onClick={() => void post(transaction.id)} type="button">
                    Post
                  </button>
                ) : null}
              </div>
            </div>
          ) : null}
          {!compact && transaction.receipt?.extraction ? <ReceiptExtractionSummary extraction={transaction.receipt.extraction} /> : null}
        </article>
      ))}
    </div>
  );
}

function ReceiptExtractionSummary({ extraction }: { extraction: NonNullable<OperationalTransaction["receipt"]>["extraction"] }) {
  if (!extraction) return null;
  if (extraction.status !== "completed") {
    return <div className="receiptExtraction error">{extraction.error_message ?? `Extraction ${extraction.status}.`}</div>;
  }

  return (
    <div className="receiptExtraction">
      <div className="receiptExtractionHeader">
        <strong>{extraction.merchant_name ?? "Unknown merchant"}</strong>
        <span>{extraction.receipt_date ?? "No date"}</span>
        <span>{extraction.total ? formatMoney(extraction.total) : "No total"}</span>
      </div>
      {extraction.line_items.length ? (
        <div className="receiptLineItems">
          {extraction.line_items.slice(0, 4).map((item) => (
            <div key={item.id}>
              <span>{item.description}</span>
              <span>{item.amount ? formatMoney(item.amount) : ""}</span>
            </div>
          ))}
        </div>
      ) : null}
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
            <span>{contact.type === "vendor" || contact.type === "both" ? qualificationLabel(contact.vendor_qualification_status) : "Not a vendor"}</span>
            <span>{contact.payment_terms ? `Default ${contact.payment_terms}` : "No default terms"}</span>
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
