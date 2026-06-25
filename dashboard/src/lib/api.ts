export type AccountType = "asset" | "liability" | "equity" | "revenue" | "expense";
export type ContactType = "customer" | "vendor" | "both";
export type TransactionKind = "expense" | "income" | "deposit";
export type TransactionStatus = "draft" | "reviewed" | "posted";
export type PayrollStatus = "draft" | "posted";
export type EmployeeStatus = "active" | "inactive";
export type CpfProfile = "sc_or_third_year_pr_55_below" | "custom" | "not_applicable";
export type ReceiptExtractionStatus = "not_configured" | "completed" | "failed";
export type VendorQualificationStatus = "pending" | "qualified" | "suspended" | "rejected";
export type PurchaseOrderStatus =
  | "draft"
  | "issued"
  | "partially_received"
  | "received"
  | "billed"
  | "closed"
  | "cancelled";
export type SalesOrderStatus =
  | "draft"
  | "received"
  | "accepted"
  | "partially_invoiced"
  | "fulfilled"
  | "invoiced"
  | "closed"
  | "cancelled";
export type DepositStatus = "not_requested" | "requested" | "invoiced" | "paid" | "applied";
export type SalesInvoiceStatus = "draft" | "issued" | "partially_paid" | "paid" | "voided";
export type CustomerReceiptStatus = "draft" | "posted" | "voided";

export type Account = {
  id: number;
  code: string;
  name: string;
  type: AccountType;
  description: string | null;
  is_active: boolean;
  created_at: string;
  balance: string;
};

export type ChartOfAccountsImportMode = "setup_replace" | "add_only";

export type ChartOfAccountsImportResult = {
  mode: ChartOfAccountsImportMode;
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
};

export type ChartOfAccountsValidationIssue = {
  code: string;
  message: string;
};

export type ChartOfAccountsValidationResult = {
  mode: ChartOfAccountsImportMode;
  can_import: boolean;
  account_count: number;
  errors: ChartOfAccountsValidationIssue[];
  warnings: ChartOfAccountsValidationIssue[];
  info: ChartOfAccountsValidationIssue[];
};

export type JournalLine = {
  id: number;
  account_id: number;
  account_code: string;
  account_name: string;
  debit: string;
  credit: string;
  description: string | null;
};

export type JournalEntry = {
  id: number;
  entry_date: string;
  memo: string;
  reference: string | null;
  created_at: string;
  lines: JournalLine[];
};

export type Summary = {
  cash_balance: string;
  receivables: string;
  payables: string;
  revenue: string;
  expenses: string;
  net_income: string;
  recent_entries: JournalEntry[];
};

export type CompanySettings = {
  id: number;
  company_name: string;
  registration_number: string | null;
  fiscal_year_start_month: number;
  base_currency: string;
  updated_at: string;
};

export type Contact = {
  id: number;
  name: string;
  type: ContactType;
  email: string | null;
  phone: string | null;
  tax_identifier: string | null;
  vendor_qualification_status: VendorQualificationStatus;
  payment_terms: string | null;
  default_expense_account_id: number | null;
  qualification_notes: string | null;
  qualification_expires_on: string | null;
  notes: string | null;
  created_at: string;
};

export type ContactPayload = {
  name: string;
  type: ContactType;
  email?: string;
  phone?: string;
  tax_identifier?: string;
  vendor_qualification_status?: VendorQualificationStatus;
  payment_terms?: string;
  default_expense_account_id?: number;
  qualification_notes?: string;
  qualification_expires_on?: string;
  notes?: string;
};

export type Employee = {
  id: number;
  staff_id: string | null;
  name: string;
  email: string | null;
  phone: string | null;
  job_title: string | null;
  status: EmployeeStatus;
  start_date: string | null;
  monthly_salary: string;
  cpf_profile: CpfProfile;
  employee_cpf_rate: string;
  employer_cpf_rate: string;
  notes: string | null;
  created_at: string;
};

export type EmployeePayload = {
  staff_id?: string;
  name: string;
  email?: string;
  phone?: string;
  job_title?: string;
  status: EmployeeStatus;
  start_date?: string;
  monthly_salary: string;
  cpf_profile: CpfProfile;
  employee_cpf_rate: string;
  employer_cpf_rate: string;
  notes?: string;
};

export type ReceiptLineItem = {
  id: number;
  description: string;
  quantity: string | null;
  unit_price: string | null;
  amount: string | null;
  confidence: string | null;
};

export type ReceiptExtraction = {
  id: number;
  receipt_id: number;
  status: ReceiptExtractionStatus;
  provider: string;
  model: string | null;
  merchant_name: string | null;
  receipt_date: string | null;
  currency: string | null;
  subtotal: string | null;
  tax: string | null;
  total: string | null;
  confidence: string | null;
  raw_text: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  line_items: ReceiptLineItem[];
};

export type Receipt = {
  id: number;
  original_filename: string;
  stored_path: string;
  content_type: string | null;
  size_bytes: number;
  uploaded_at: string;
  extraction: ReceiptExtraction | null;
};

export type OperationalTransaction = {
  id: number;
  kind: TransactionKind;
  status: TransactionStatus;
  transaction_date: string;
  description: string;
  reference: string | null;
  amount: string;
  contact: Contact | null;
  debit_account: Account;
  credit_account: Account;
  receipt: Receipt | null;
  journal_entry_id: number | null;
  created_at: string;
  posted_at: string | null;
};

export type OperationalTransactionPayload = {
  kind: TransactionKind;
  status: TransactionStatus;
  transaction_date: string;
  description: string;
  reference?: string;
  amount: string;
  contact_id?: number;
  debit_account_id: number;
  credit_account_id: number;
  receipt?: {
    filename: string;
    content_type?: string;
    content_base64: string;
  };
};

export type PayrollRun = {
  id: number;
  status: PayrollStatus;
  employee: Employee | null;
  employee_name: string;
  period_start: string;
  period_end: string;
  pay_date: string;
  gross_salary: string;
  cpf_subject_wage: string;
  employee_cpf_rate: string;
  employer_cpf_rate: string;
  employee_cpf: string;
  employer_cpf: string;
  net_pay: string;
  salary_account: Account;
  employer_cpf_account: Account;
  cash_account: Account;
  cpf_payable_account: Account;
  notes: string | null;
  journal_entry_id: number | null;
  created_at: string;
  posted_at: string | null;
};

export type PayrollRunPayload = {
  status: PayrollStatus;
  employee_id?: number;
  employee_name: string;
  period_start: string;
  period_end: string;
  pay_date: string;
  gross_salary: string;
  cpf_subject_wage?: string;
  employee_cpf_rate: string;
  employer_cpf_rate: string;
  salary_account_id: number;
  employer_cpf_account_id: number;
  cash_account_id: number;
  cpf_payable_account_id: number;
  notes?: string;
};

export type PurchaseOrderLine = {
  id: number;
  description: string;
  quantity: string;
  unit_price: string;
  tax_amount: string;
  line_total: string;
  expense_account: Account;
};

export type PurchaseOrder = {
  id: number;
  po_number: string;
  status: PurchaseOrderStatus;
  vendor: Contact;
  issue_date: string;
  expected_delivery_date: string | null;
  currency: string;
  payment_terms: string | null;
  notes: string | null;
  delivery_instructions: string | null;
  subtotal: string;
  tax_total: string;
  total: string;
  lines: PurchaseOrderLine[];
  issued_at: string | null;
  cancelled_at: string | null;
  created_at: string;
};

export type PurchaseOrderPayload = {
  po_number?: string;
  status: PurchaseOrderStatus;
  vendor_id: number;
  issue_date: string;
  expected_delivery_date?: string;
  currency: string;
  payment_terms?: string;
  notes?: string;
  delivery_instructions?: string;
  lines: Array<{
    description: string;
    quantity: string;
    unit_price: string;
    tax_amount: string;
    expense_account_id: number;
  }>;
};

export type SalesOrderLine = {
  id: number;
  description: string;
  quantity: string;
  unit_price: string;
  tax_amount: string;
  line_total: string;
  revenue_account: Account;
};

export type SalesOrder = {
  id: number;
  order_number: string;
  client_po_number: string;
  status: SalesOrderStatus;
  customer: Contact;
  received_date: string;
  expected_delivery_date: string | null;
  currency: string;
  payment_terms: string | null;
  deposit_required: boolean;
  deposit_rate: string;
  deposit_amount: string;
  deposit_due_date: string | null;
  deposit_status: DepositStatus;
  deposit_transaction_id: number | null;
  notes: string | null;
  delivery_instructions: string | null;
  subtotal: string;
  tax_total: string;
  total: string;
  invoiced_total: string;
  paid_total: string;
  unbilled_total: string;
  lines: SalesOrderLine[];
  accepted_at: string | null;
  cancelled_at: string | null;
  created_at: string;
};

export type SalesOrderPayload = {
  order_number?: string;
  client_po_number?: string;
  status: SalesOrderStatus;
  customer_id: number;
  received_date: string;
  expected_delivery_date?: string;
  currency: string;
  payment_terms?: string;
  deposit_required: boolean;
  deposit_rate: string;
  deposit_amount?: string;
  deposit_due_date?: string;
  deposit_status: DepositStatus;
  notes?: string;
  delivery_instructions?: string;
  lines: Array<{
    description: string;
    quantity: string;
    unit_price: string;
    tax_amount: string;
    revenue_account_id: number;
  }>;
};

export type SalesInvoiceLine = {
  id: number;
  description: string;
  quantity: string;
  unit_price: string;
  tax_amount: string;
  line_total: string;
  revenue_account: Account;
};

export type SalesInvoice = {
  id: number;
  invoice_number: string;
  status: SalesInvoiceStatus;
  customer: Contact;
  sales_order: SalesOrder | null;
  issue_date: string;
  due_date: string;
  currency: string;
  payment_terms: string | null;
  notes: string | null;
  subtotal: string;
  tax_total: string;
  total: string;
  amount_paid: string;
  amount_due: string;
  journal_entry_id: number | null;
  lines: SalesInvoiceLine[];
  issued_at: string | null;
  voided_at: string | null;
  created_at: string;
};

export type SalesInvoicePayload = {
  invoice_number?: string;
  status: SalesInvoiceStatus;
  customer_id: number;
  sales_order_id?: number;
  issue_date: string;
  due_date: string;
  currency: string;
  payment_terms?: string;
  notes?: string;
  lines: Array<{
    description: string;
    quantity: string;
    unit_price: string;
    tax_amount: string;
    revenue_account_id: number;
  }>;
};

export type CustomerReceiptAllocation = {
  id: number;
  invoice: SalesInvoice;
  amount: string;
};

export type CustomerReceipt = {
  id: number;
  receipt_number: string;
  status: CustomerReceiptStatus;
  customer: Contact;
  receipt_date: string;
  currency: string;
  amount: string;
  bank_account: Account;
  reference: string | null;
  notes: string | null;
  journal_entry_id: number | null;
  allocations: CustomerReceiptAllocation[];
  posted_at: string | null;
  voided_at: string | null;
  created_at: string;
};

export type CustomerReceiptPayload = {
  receipt_number?: string;
  status: CustomerReceiptStatus;
  customer_id: number;
  receipt_date: string;
  currency: string;
  amount: string;
  bank_account_id: number;
  reference?: string;
  notes?: string;
  allocations: Array<{
    invoice_id: number;
    amount: string;
  }>;
};

export type ProfitAndLoss = {
  revenue: string;
  expenses: string;
  net_income: string;
  revenue_accounts: Account[];
  expense_accounts: Account[];
};

export type BalanceSheet = {
  assets: string;
  liabilities: string;
  equity: string;
  retained_earnings: string;
  total_liabilities_and_equity: string;
  asset_accounts: Account[];
  liability_accounts: Account[];
  equity_accounts: Account[];
};

export type AccountsReceivableAgeingRow = {
  customer_id: number | null;
  customer_name: string;
  current: string;
  days_31_60: string;
  days_61_90: string;
  days_over_90: string;
  total: string;
};

export type AccountsReceivableAgeing = {
  as_of: string;
  current: string;
  days_31_60: string;
  days_61_90: string;
  days_over_90: string;
  total: string;
  rows: AccountsReceivableAgeingRow[];
};

export type ClientHistoryEntry = {
  customer: Contact;
  ordered_total: string;
  invoiced_total: string;
  paid_total: string;
  receivable_total: string;
  unbilled_total: string;
  sales_orders: SalesOrder[];
  sales_invoices: SalesInvoice[];
  customer_receipts: CustomerReceipt[];
};

export type ClientHistory = {
  ordered_total: string;
  invoiced_total: string;
  paid_total: string;
  receivable_total: string;
  unbilled_total: string;
  clients: ClientHistoryEntry[];
};

export type JournalEntryPayload = {
  entry_date: string;
  memo: string;
  reference?: string;
  lines: Array<{
    account_id: number;
    debit?: string;
    credit?: string;
    description?: string;
  }>;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    },
    ...init
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    if (typeof errorBody.detail === "string") {
      throw new Error(errorBody.detail);
    }
    if (Array.isArray(errorBody.detail)) {
      throw new Error(errorBody.detail.join(" "));
    }
    throw new Error("Request failed");
  }

  return response.json() as Promise<T>;
}

async function requestText(path: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(response.statusText || "Request failed");
  }
  return response.text();
}

function downloadText(filename: string, text: string, contentType = "text/csv") {
  const blob = new Blob([text], { type: contentType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export const api = {
  accounts: () => request<Account[]>("/accounts"),
  downloadAccountsTemplate: async () => {
    const csv = await requestText("/accounts/template.csv");
    downloadText("chart-of-accounts-template.csv", csv);
  },
  downloadAccountsExport: async () => {
    const csv = await requestText("/accounts/export.csv");
    downloadText("chart-of-accounts.csv", csv);
  },
  importAccounts: (mode: ChartOfAccountsImportMode, csvText: string) =>
    request<ChartOfAccountsImportResult>("/accounts/import", {
      method: "POST",
      body: JSON.stringify({ mode, csv_text: csvText })
    }),
  validateAccounts: (mode: ChartOfAccountsImportMode, csvText: string) =>
    request<ChartOfAccountsValidationResult>("/accounts/validate", {
      method: "POST",
      body: JSON.stringify({ mode, csv_text: csvText })
    }),
  companySettings: () => request<CompanySettings>("/company-settings"),
  updateCompanySettings: (payload: Omit<CompanySettings, "id" | "updated_at">) =>
    request<CompanySettings>("/company-settings", {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  contacts: () => request<Contact[]>("/contacts"),
  createContact: (payload: ContactPayload) =>
    request<Contact>("/contacts", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  employees: () => request<Employee[]>("/employees"),
  createEmployee: (payload: EmployeePayload) =>
    request<Employee>("/employees", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  transactions: () => request<OperationalTransaction[]>("/transactions"),
  createTransaction: (payload: OperationalTransactionPayload) =>
    request<OperationalTransaction>("/transactions", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  postTransaction: (id: number) =>
    request<OperationalTransaction>(`/transactions/${id}/post`, {
      method: "POST"
    }),
  extractReceipt: (id: number) =>
    request<ReceiptExtraction>(`/receipts/${id}/extract`, {
      method: "POST"
    }),
  payroll: () => request<PayrollRun[]>("/payroll"),
  createPayroll: (payload: PayrollRunPayload) =>
    request<PayrollRun>("/payroll", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  postPayroll: (id: number) =>
    request<PayrollRun>(`/payroll/${id}/post`, {
      method: "POST"
    }),
  purchaseOrders: () => request<PurchaseOrder[]>("/purchase-orders"),
  createPurchaseOrder: (payload: PurchaseOrderPayload) =>
    request<PurchaseOrder>("/purchase-orders", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  issuePurchaseOrder: (id: number) =>
    request<PurchaseOrder>(`/purchase-orders/${id}/issue`, {
      method: "POST"
    }),
  cancelPurchaseOrder: (id: number) =>
    request<PurchaseOrder>(`/purchase-orders/${id}/cancel`, {
      method: "POST"
    }),
  salesOrders: () => request<SalesOrder[]>("/sales-orders"),
  createSalesOrder: (payload: SalesOrderPayload) =>
    request<SalesOrder>("/sales-orders", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  acceptSalesOrder: (id: number) =>
    request<SalesOrder>(`/sales-orders/${id}/accept`, {
      method: "POST"
    }),
  cancelSalesOrder: (id: number) =>
    request<SalesOrder>(`/sales-orders/${id}/cancel`, {
      method: "POST"
    }),
  salesInvoices: () => request<SalesInvoice[]>("/sales-invoices"),
  createSalesInvoice: (payload: SalesInvoicePayload) =>
    request<SalesInvoice>("/sales-invoices", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  issueSalesInvoice: (id: number) =>
    request<SalesInvoice>(`/sales-invoices/${id}/issue`, {
      method: "POST"
    }),
  linkSalesInvoiceToOrder: (invoiceId: number, salesOrderId: number) =>
    request<SalesInvoice>(`/sales-invoices/${invoiceId}/link-sales-order`, {
      method: "POST",
      body: JSON.stringify({ sales_order_id: salesOrderId })
    }),
  customerReceipts: () => request<CustomerReceipt[]>("/customer-receipts"),
  createCustomerReceipt: (payload: CustomerReceiptPayload) =>
    request<CustomerReceipt>("/customer-receipts", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  profitAndLoss: () => request<ProfitAndLoss>("/reports/profit-and-loss"),
  balanceSheet: () => request<BalanceSheet>("/reports/balance-sheet"),
  clientHistory: () => request<ClientHistory>("/reports/client-history"),
  accountsReceivableAgeing: () => request<AccountsReceivableAgeing>("/reports/accounts-receivable-ageing"),
  summary: () => request<Summary>("/summary"),
  journalEntries: () => request<JournalEntry[]>("/journal-entries"),
  createJournalEntry: (payload: JournalEntryPayload) =>
    request<JournalEntry>("/journal-entries", {
      method: "POST",
      body: JSON.stringify(payload)
    })
};
