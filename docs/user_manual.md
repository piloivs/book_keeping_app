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

## Add a Transaction

Use the New Transaction form to create a balanced journal entry.

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

Click Add to save the transaction. The app will update the summary cards, account balances, and recent entries.

## Double-Entry Rule

Every transaction must balance:

```text
Total debits = Total credits
```

The current prototype form creates a simple two-line balanced entry: one debit and one credit for the same amount.

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
- Customers and vendors
- Invoices
- Bills
- Bank imports
- Attachments
- Formal financial statement screens
- Multi-user permissions

