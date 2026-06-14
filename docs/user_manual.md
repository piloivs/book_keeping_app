# Bookkeeping App User Manual

## Current Version

This manual covers the local single-user prototype.

## Start the App

Open PowerShell in the project folder:

```powershell
cd C:\Users\User\Documents\Projects\book_keeping_app
```

Start the backend API:

```powershell
.venv\Scripts\python.exe -m uvicorn bookkeeping_app.main:app --reload --host 127.0.0.1 --port 8000
```

Open a second PowerShell window and start the frontend:

```powershell
cd C:\Users\User\Documents\Projects\book_keeping_app\dashboard
npm.cmd run dev
```

Open the app in your browser:

```text
http://127.0.0.1:5173
```

The backend API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Dashboard

The top summary cards show:

- Cash: current cash account balance.
- Receivables: customer amounts owed to the business.
- Payables: vendor amounts owed by the business.
- Net income: revenue minus expenses.

Use the refresh button in the top-right corner to reload data from the backend.

The main navigation tabs are:

- Dashboard: account balances, operational queue, and recent journal entries.
- Transactions: daily income and expense capture.
- Contacts: customers and vendors.
- Reports: current profit and loss and balance sheet views.
- Settings: company profile and reporting defaults.

## Chart of Accounts

The chart of accounts lists the accounts currently available for transactions.

Default accounts include:

- 1000 Cash
- 1100 Accounts Receivable
- 2000 Accounts Payable
- 3000 Owner Equity
- 4000 Sales Revenue
- 5000 Office Supplies
- 5100 Software Expense

Each account has a type and a current balance.

## Add an Income or Expense Transaction

Use the Transactions tab to record day-to-day business activity.

Transaction fields:

- Type: Expense or Income.
- Status: Draft, Reviewed, or Posted.
- Date: transaction date.
- Description: short explanation.
- Contact: optional customer or vendor.
- Reference: optional invoice, receipt, or bank reference.
- Account fields: the app changes these based on income vs expense.
- Amount.
- Receipt: optional supporting document.

For expenses:

- Debit an expense account.
- Credit a cash/bank account or accounts payable.

For income:

- Debit a cash/bank or receivable account.
- Credit a revenue account.

Only Posted transactions affect the ledger and reports. Draft and Reviewed transactions are saved in the operational queue but do not update account balances until posted.

Receipt files are stored locally under:

```text
data/raw/receipts/
```

Do not manually edit receipt files after upload.

## Manual Journal Entries

Manual journal entries are still available through the backend API, but the main browser UI now focuses on operational income and expense capture.

Required fields:

- Date
- Memo
- Debit account
- Credit account
- Amount

Optional field:

- Reference

Example: owner contributes cash to the business.

- Date: today's date
- Memo: Owner contribution
- Debit: 1000 Cash
- Credit: 3000 Owner Equity
- Amount: 100.00

Use the API documentation for manual journal entry testing:

```text
http://127.0.0.1:8000/docs
```

## Double-Entry Rule

Every transaction must balance:

```text
Total debits = Total credits
```

The current prototype form creates a simple two-line balanced entry: one debit and one credit for the same amount.

## Contacts

Use the Contacts tab to add customers and vendors.

Supported contact types:

- Customer
- Vendor
- Both

Contacts can be attached to income and expense transactions.

## Reports

The Reports tab currently includes:

- Profit & Loss: revenue, expenses, and net income.
- Balance Sheet: assets, liabilities, equity, retained earnings, and total liabilities plus equity.

These are internal management reports based on posted journal entries. They are intended to support review by IntelliArtAI's corporate secretary or accountant, not to replace formal ACRA/IRAS review.

## Company Settings

Use the Settings tab to maintain:

- Company name
- Registration number
- Fiscal year start month
- Base currency

## Troubleshooting

If the app shows `Failed to fetch`, the frontend cannot reach the backend.

Check that the backend is running:

```text
http://127.0.0.1:8000/health
```

It should return:

```json
{"status":"ok"}
```

If `npm.cmd run dev` says port `5173` is already in use, find the process:

```powershell
netstat -ano | findstr :5173
```

Stop the process using the PID shown in the last column:

```powershell
Stop-Process -Id <PID>
```

Then run:

```powershell
npm.cmd run dev
```

## Data Storage

The local SQLite database is stored at:

```text
data/warehouse/bookkeeping.sqlite3
```

Do not manually edit this file while the app is running.

## Current Limitations

This prototype does not yet include:

- User login
- Invoices and bills
- Bank imports and reconciliation
- Document preview/download from the UI
- Formal financial statement screens
- Multi-user permissions
