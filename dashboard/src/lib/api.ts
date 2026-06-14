export type AccountType = "asset" | "liability" | "equity" | "revenue" | "expense";
export type ContactType = "customer" | "vendor" | "both";
export type TransactionKind = "expense" | "income";
export type TransactionStatus = "draft" | "reviewed" | "posted";

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
  notes: string | null;
  created_at: string;
};

export type ContactPayload = {
  name: string;
  type: ContactType;
  email?: string;
  phone?: string;
  tax_identifier?: string;
  notes?: string;
};

export type Receipt = {
  id: number;
  original_filename: string;
  stored_path: string;
  content_type: string | null;
  size_bytes: number;
  uploaded_at: string;
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
    throw new Error(typeof errorBody.detail === "string" ? errorBody.detail : "Request failed");
  }

  return response.json() as Promise<T>;
}

export const api = {
  accounts: () => request<Account[]>("/accounts"),
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
  profitAndLoss: () => request<ProfitAndLoss>("/reports/profit-and-loss"),
  balanceSheet: () => request<BalanceSheet>("/reports/balance-sheet"),
  summary: () => request<Summary>("/summary"),
  journalEntries: () => request<JournalEntry[]>("/journal-entries"),
  createJournalEntry: (payload: JournalEntryPayload) =>
    request<JournalEntry>("/journal-entries", {
      method: "POST",
      body: JSON.stringify(payload)
    })
};
