# IntelliArtAI Operations Core User Manual

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

The main navigation tabs are organized by business module:

- Dashboard: read-only operating overview, A/R ageing, operational queue, read-only chart of accounts, and recent journal entries.
- Finance: daily income and expense capture, posted transactions, and receipt extraction.
- Sales: customer master records, sales invoices, customer receipts, client purchase orders, and client history.
- Purchasing: vendor master records, vendor qualification, purchase orders, issuance, and cancellation.
- HR & Payroll: employee master records, salary runs, CPF withholding, employer CPF, payroll posting, and payslip printing.
- Reports: current profit and loss and balance sheet views.
- Settings: company profile, reporting defaults, and controlled chart-of-accounts setup.

## Chart of Accounts

The dashboard shows the chart of accounts as a read-only reference because accounts are fundamental to the ledger and internal app workflows.

Chart-of-accounts setup tools are in Settings under Chart of Accounts Setup. From there you can:

- Download a default template.
- Export the current chart as a CSV backup.
- Import additional accounts with Add Only mode.
- Replace the setup chart with Setup Replace mode when the app still allows it.
- Print the chart.

Add Only is a CSV import mode. It does not manually add a single account when clicked. It adds only account codes that are not already in the app and skips matching existing codes.

Setup Replace can replace the full chart from an imported CSV. Use it only during initial setup. The app blocks setup replacement after accounts are used by transactions, documents, payroll, contacts, or journal lines.

Both Add Only and Setup Replace ask for confirmation when selected. CSV imports are also validated before the app imports them.

Default accounts include:

- 1000 Cash
- 1010 Bank Account
- 1100 Accounts Receivable
- 2000 Accounts Payable
- 2100 CPF Payable
- 2150 Deferred Revenue
- 3000 Owner Equity
- 3900 Retained Earnings
- 4000 Sales Revenue
- 4100 Consulting Revenue
- 5000 Office Supplies
- 5100 Software Expense
- 5200 Professional Fees
- 5300 Salaries and Wages
- 5310 Employer CPF Expense

Each account has a type and a current balance.

## Add an Income or Expense Transaction

Use the Finance tab to record day-to-day business activity.

Transaction fields:

- Type: Expense or Income. Deposit transactions can also appear when a paid sales order deposit is posted from the Sales tab.
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

For paid sales order deposits:

- Debit Bank Account.
- Credit Deferred Revenue.

Only Posted transactions affect the ledger and reports. Draft and Reviewed transactions are saved in the operational queue but do not update account balances until posted.

Receipt files are stored locally under:

```text
data/raw/receipts/
```

Do not manually edit receipt files after upload.

Click Extract beside a receipt-backed transaction to run local Tesseract OCR and local Ollama structured parsing. The app stores a review result with merchant, receipt date, subtotal, tax, total, visible text, and line items. If Tesseract or Ollama is not available, the transaction will show a setup message instead of changing the receipt or ledger.

Receipt extraction currently supports image uploads such as JPG, PNG, or TIFF. It is meant to speed up data entry, not replace review. Check extracted totals and line descriptions before relying on them.

## HR & Payroll

Use the HR & Payroll tab to maintain employee records and record staff salary payments and CPF.

If the employee already exists in the Employee Master section, choose the employee from the Employee field. The payroll form will fill in the employee name, current monthly salary, CPF subject wage, and CPF rates from the employee record. You can still edit the payroll run before saving.

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

Before issuing a PO, create the vendor in the Vendor Master section and set Vendor Qualification to Qualified. The app lets you create draft POs for vendor contacts that are still pending, but it blocks issuing POs unless the vendor is qualified.

Vendor master fields:

- Name.
- Email.
- Phone.
- Tax Identifier.
- Default Payment Terms.
- Vendor Qualification: Pending, Qualified, Suspended, or Rejected.
- Default Expense Account.
- Qualification Expiry.
- Qualification Notes.

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

## Sales

Use the Sales tab to issue customer invoices, record customer receipts, and capture purchase orders received from clients.

Before creating sales records, create the customer in the Customer Master section.

Customer master fields:

- Name.
- Email.
- Phone.
- Tax Identifier.
- Default Payment Terms.

### Sales Invoices

Use Create Invoice to record formal customer invoices. If you save an invoice as Issued, the app posts it to the ledger immediately:

- Debit Accounts Receivable.
- Credit the selected revenue account or accounts.
- Credit GST Output Tax when invoice line tax is present.

Invoice fields:

- Status: Issue Now or Draft.
- Invoice No.: optional. If blank, the app generates a number such as `INV-202606-0001`.
- Customer.
- Optional linked client PO.
- Issue Date.
- Due Date.
- Currency.
- Payment Terms.
- Line descriptions, quantities, unit prices, tax amounts, and revenue accounts.
- Notes.

Draft invoices do not affect the ledger until you click Issue.

### Customer Receipts

Use Record Receipt to post customer payments against open invoices. Receipts must be allocated to an issued invoice. Posted customer receipts create this ledger entry:

- Debit Bank Account.
- Credit Accounts Receivable.

Receipt fields:

- Customer.
- Open invoice.
- Receipt No.: optional. If blank, the app generates a number such as `REC-202606-0001`.
- Receipt Date.
- Amount.
- Bank Account.
- Reference.
- Notes.

The invoice status updates to Partially Paid or Paid after the receipt is posted.

### Client Purchase Orders

The Sales tab can also capture purchase orders received from clients. The app records the customer's PO number and generates an internal sales order number if you leave Sales Order blank.

Client PO fields:

- Status: Draft, Received, or Accepted.
- Sales Order: optional. If blank, the app generates a number such as `SO-202606-0001`.
- Client PO Number: the customer's own PO reference.
- Customer.
- Received Date.
- Expected Delivery.
- Currency.
- Payment Terms.
- Deposit Required, with 5%, 10%, or custom deposit amount.
- Deposit Due date.
- Deposit Status: Requested, Invoiced, Paid, or Applied.
- Line descriptions, quantities, unit prices, tax amounts, and revenue accounts.
- Delivery Instructions.
- Notes.

The current browser workflow supports creating client POs, accepting draft or received client POs, and cancelling open client POs. Deposits marked Requested or Invoiced are tracked as commercial terms only. Deposits marked Paid create a posted deposit transaction.

Paid deposits are treated as advance payments and posted to Deferred Revenue until the related work is earned:

- Debit Bank Account.
- Credit Deferred Revenue.

After a paid deposit is saved, it appears in Finance as a posted deposit transaction and affects Dashboard cash and Balance Sheet liabilities. It does not increase revenue or net income.

Revenue recognition and application of deposits to milestones should happen later when milestone invoicing and revenue workflows are added.

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

Settings also contains Chart of Accounts Setup. This is intentionally separate from the dashboard because changing accounts affects transaction posting, reporting, and future workflows.

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
- Supplier bills
- Bank imports and reconciliation
- Document preview/download from the UI
- PO receiving and PO-to-bill matching
- Milestone billing, deposit application, and deferred revenue release
- Formal financial statement screens
- Multi-user permissions
