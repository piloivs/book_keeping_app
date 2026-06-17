import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  ArrowDownUp,
  BookOpenCheck,
  Building2,
  CircleDollarSign,
  ClipboardList,
  FileText,
  Landmark,
  Plus,
  Printer,
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
  CpfProfile,
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

type View = "dashboard" | "transactions" | "purchasing" | "payroll" | "employees" | "contacts" | "reports" | "settings";

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
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [transactions, setTransactions] = useState<OperationalTransaction[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [payrollRuns, setPayrollRuns] = useState<PayrollRun[]>([]);
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
      const [accountData, settingsData, contactData, employeeData, transactionData, purchaseOrderData, payrollData, summaryData, entryData, pnlData, bsData] =
        await Promise.all([
          api.accounts(),
          api.companySettings(),
          api.contacts(),
          api.employees(),
          api.transactions(),
          api.purchaseOrders(),
          api.payroll(),
          api.summary(),
          api.journalEntries(),
          api.profitAndLoss(),
          api.balanceSheet()
        ]);
      setAccounts(accountData);
      setSettings(settingsData);
      setContacts(contactData);
      setEmployees(employeeData);
      setTransactions(transactionData);
      setPurchaseOrders(purchaseOrderData);
      setPayrollRuns(payrollData);
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
        <TabButton active={view === "purchasing"} icon={<ClipboardList size={16} />} label="Purchasing" onClick={() => setView("purchasing")} />
        <TabButton active={view === "payroll"} icon={<Landmark size={16} />} label="Payroll" onClick={() => setView("payroll")} />
        <TabButton active={view === "employees"} icon={<Users size={16} />} label="Employees" onClick={() => setView("employees")} />
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
      {view === "purchasing" ? (
        <PurchasingView
          accounts={accounts}
          contacts={contacts}
          loading={loading}
          purchaseOrders={purchaseOrders}
          onChanged={() => void loadData()}
        />
      ) : null}
      {view === "payroll" ? (
        <PayrollView
          accounts={accounts}
          employees={employees}
          loading={loading}
          payrollRuns={payrollRuns}
          settings={settings}
          onChanged={() => void loadData()}
        />
      ) : null}
      {view === "employees" ? <EmployeesView employees={employees} loading={loading} onChanged={() => void loadData()} /> : null}
      {view === "contacts" ? <ContactsView accounts={accounts} contacts={contacts} loading={loading} onChanged={() => void loadData()} /> : null}
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

type PurchaseOrderDraftLine = {
  description: string;
  quantity: string;
  unit_price: string;
  tax_amount: string;
  expense_account_id: number | "";
};

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
  return (
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

function PayrollView({
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

function ContactForm({ accounts, onCreated }: { accounts: Account[]; onCreated: () => void }) {
  const expenseAccounts = accounts.filter((account) => account.type === "expense");
  const [name, setName] = useState("");
  const [type, setType] = useState<ContactPayload["type"]>("vendor");
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
        payment_terms: isVendor ? paymentTerms || undefined : undefined,
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
          Phone
          <input value={phone} onChange={(event) => setPhone(event.target.value)} />
        </label>
        <label>
          Tax Identifier
          <input value={taxIdentifier} onChange={(event) => setTaxIdentifier(event.target.value)} />
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
              Default Payment Terms
              <input value={paymentTerms} onChange={(event) => setPaymentTerms(event.target.value)} />
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
