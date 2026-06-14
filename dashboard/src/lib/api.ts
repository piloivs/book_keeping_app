export type AccountType = "asset" | "liability" | "equity" | "revenue" | "expense";

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
  summary: () => request<Summary>("/summary"),
  journalEntries: () => request<JournalEntry[]>("/journal-entries"),
  createJournalEntry: (payload: JournalEntryPayload) =>
    request<JournalEntry>("/journal-entries", {
      method: "POST",
      body: JSON.stringify(payload)
    })
};

