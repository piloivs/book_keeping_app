# Bookkeeping App User Manual

## Current Version

This manual covers the local single-user prototype.

## Start the App

Open PowerShell in the project folder:

```powershell
cd C:\Users\User\Documents\Projects\book_keeping_app
```

Start the app:

```powershell
.\start-app.cmd
```

This starts both the backend API and the frontend dashboard. Press Ctrl+C in that terminal to stop both.

If you want to run the two parts manually, start the backend API:

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
- Purchasing: vendor purchase order creation, issuance, and cancellation.
- Payroll: salary runs, CPF withholding, employer CPF, and payroll posting.
- Employees: staff master records, current salary, and CPF profile.
- Contacts: customers and vendors.
- Reports: current profit and loss and balance sheet views.
- Settings: company profile and reporting defaults.

## Chart of Accounts

The chart of accounts lists the accounts currently available for transactions.

Default accounts include:

- 1000 Cash
- 1100 Accounts Receivable
- 2000 Accounts Payable
- 2100 CPF Payable
- 3000 Owner Equity
- 4000 Sales Revenue
- 5000 Office Supplies
- 5100 Software Expense
- 5300 Salaries and Wages
- 5310 Employer CPF Expense

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

Click Extract beside a receipt-backed transaction to run local Tesseract OCR and local Ollama structured parsing. The app stores a review result with merchant, receipt date, subtotal, tax, total, visible text, and line items. If Tesseract or Ollama is not available, the transaction will show a setup message instead of changing the receipt or ledger.

Receipt extraction currently supports image uploads such as JPG, PNG, or TIFF. It is meant to speed up data entry, not replace review. Check extracted totals and line descriptions before relying on them.

## Payroll

Use the Payroll tab to record staff salary payments and CPF.

If the employee already exists in the Employees tab, choose the employee from the Employee field. The payroll form will fill in the employee name, current monthly salary, CPF subject wage, and CPF rates from the employee record. You can still edit the payroll run before saving.

Payroll fields:

- Status: Draft or Posted.
- Employee.
- Employee Name.
- Period Start and Period End.
- Pay Date.
- Gross Salary.
- CPF Subject Wage.
- Employee CPF %.
- Employer CPF %.
- Salary Expense account.
- Employer CPF Expense account.
- Paid From account.
- CPF Payable account.
- Notes.

The default CPF fields use the common 2026 full-rate case for a Singapore Citizen or third-year-and-above Singapore Permanent Resident who is age 55 or below: 20% employee CPF and 17% employer CPF. CPF rules vary by citizenship or PR year, age group, wage band, Ordinary Wage ceiling, Additional Wage ceiling, and rounding rules, so review the CPF fields before posting each payroll run.

When payroll is posted, the app creates a journal entry like this:

- Debit Salaries and Wages for gross salary.
- Debit Employer CPF Expense for employer CPF.
- Credit Bank Account for net pay to the employee.
- Credit CPF Payable for employee CPF plus employer CPF.

Example for a $5,000 gross monthly salary at 20% employee CPF and 17% employer CPF:

- Gross salary: $5,000.00
- Employee CPF withheld: $1,000.00
- Employer CPF expense: $850.00
- Net pay to employee: $4,000.00
- CPF payable: $1,850.00.

To print a salary slip:

1. Save the payroll run as Posted, or post a Draft payroll run.
2. In Payroll Runs, click Print.
3. Review the salary slip.
4. Click Print in the salary slip window.

The salary slip includes the employer name, employee name, pay date, salary period, gross salary, employee CPF deduction, net salary paid, employer CPF, and total CPF payable. MOM requires itemised pay slips for employees covered by the Employment Act, and pay slips can be soft or hard copy.

## Purchasing

Use the Purchasing tab to prepare and issue purchase orders to vendors.

Before issuing a PO, create the vendor in Contacts and set Vendor Qualification to Qualified. The app lets you create draft POs for vendor contacts that are still pending, but it blocks issuing POs unless the vendor is qualified.

Purchase order fields:

- Status: Draft or Issued.
- PO Number: optional. If blank, the app generates a number such as `PO-202606-0001`.
- Vendor.
- Issue Date.
- Expected Delivery.
- Currency.
- Payment Terms from the proposal or accepted quote.
- Line descriptions, quantities, unit prices, tax amounts, and expense accounts.
- Delivery Instructions.
- Notes.

PO statuses currently supported by the backend are draft, issued, partially received, received, billed, closed, and cancelled. The current browser workflow supports creating draft or issued POs, issuing draft POs, and cancelling open POs.

Purchase orders do not affect the ledger or reports yet. They represent a purchasing commitment. Accounting should happen later when a supplier invoice or bill is recorded from the PO.

## Employees

Use the Employees tab to store staff information used by payroll.

Employee fields:

- Staff ID.
- Status: Active or Inactive.
- Name.
- Job Title.
- Email.
- Phone.
- Start Date.
- Current Monthly Salary.
- CPF Profile.
- Employee CPF %.
- Employer CPF %.
- Notes.

CPF Profile options:

- SC / 3rd-year PR, 55 and below: defaults to 20% employee CPF and 17% employer CPF.
- Custom rates: lets you enter CPF percentages manually.
- Not applicable: sets CPF percentages to 0%.

The current version stores the employee's current salary directly on the employee record. A future salary history feature should be added before using this for long-term historical payroll records with salary changes.

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

Vendor contacts also include qualification details used by Purchasing:

- Vendor Qualification: Pending, Qualified, Suspended, or Rejected.
- Default Payment Terms.
- Default Expense Account.
- Qualification Expiry.
- Qualification Notes.

Only qualified vendor contacts can receive issued purchase orders.

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
- PO receiving and PO-to-bill matching
- Formal financial statement screens
- Multi-user permissions
