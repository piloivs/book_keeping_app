# Codex Primary Project Instructions

## Project Name

IntelliArtAI SME Operating Framework  
Initial module: Bookkeeping and Financial Operations Core

## Purpose

Build this application first for IntelliArtAI’s internal use, but design it from the beginning so it can later be productized for SMEs.

This is not merely a bookkeeping app. It is intended to become the financial and operational backbone of IntelliArtAI’s broader SME AI automation ecosystem.

The bookkeeping module is Module 1 of a larger operating framework that will eventually connect:

- Finance
- Sales
- Procurement
- HR
- Operations
- Documents
- Approvals
- Dashboards
- AI agents

The system should act as the “glue” that binds future IntelliArtAI AI modules together.

## Strategic Product Positioning

The application should be designed as:

> An SME financial operations and business control platform that connects bookkeeping, documents, workflows, approvals, reporting, and AI-assisted finance modules.

For external SME positioning, avoid presenting the app as a simple accounting tool. The stronger positioning is:

> A practical SME operating framework where bookkeeping, documents, approvals, dashboards, and AI agents work from the same trusted business data.

The system should support accountant-ready bookkeeping, financial visibility, workflow control, and future AI-assisted automation.

## Core Design Philosophy

The accounting ledger must be the trusted system of record.

All operational modules and AI modules should connect back to structured business data, source documents, user permissions, approval workflows, and audit trails.

Key principle:

```text
AI observes → AI recommends → user approves → system posts → audit trail records
```

AI should assist and recommend, but it should not silently create, modify, or post accounting records without user approval.

## Compliance Orientation

Design the system to support GAAP/SFRS-aligned bookkeeping principles, especially for Singapore SMEs.

The app should support:

- Double-entry accounting
- Accrual accounting
- Proper chart of accounts
- Source document retention
- Audit trails
- Period locking
- Accountant-ready reporting
- GST-capable transaction structure
- Exportable records
- No silent modification of posted transactions

Do not describe the product as automatically “GAAP compliant.” A better internal standard is:

> Designed to support GAAP/SFRS-aligned bookkeeping through double-entry accounting, audit trails, source-document retention, period controls, and accountant-ready reporting.

Compliance ultimately depends on correct setup, proper use, accountant review, and the applicable reporting framework.

## Accounting Engine Requirements

The core system must be a double-entry general ledger.

Every financial transaction must eventually post to the ledger. Invoices, bills, payments, journals, adjustments, bank transactions, and tax entries must all flow through the accounting engine.

Non-negotiable accounting rule:

```text
Total debits must equal total credits.
Assets = Liabilities + Equity.
```

The system must not allow an unbalanced journal entry to be posted.

## Required Accounting Entities

At minimum, include these accounting concepts:

- Company
- Financial year
- Accounting period
- Chart of accounts
- Account types
- Journal entry header
- Journal entry lines
- Customers
- Suppliers
- Sales invoices
- Supplier bills
- Payments received
- Payments made
- Bank accounts
- Bank transactions
- Reconciliation records
- Tax codes
- Documents and attachments
- Audit logs
- Users
- Roles
- Permissions

## Suggested Core Tables

The exact schema can evolve, but the system should include entities similar to the following.

### Company and User Layer

```text
companies
users
roles
permissions
user_roles
company_users
```

### Master Data Layer

```text
customers
suppliers
products_or_services
projects
currencies
tax_codes
```

### Accounting Layer

```text
chart_of_accounts
accounting_periods
journal_entries
journal_lines
sales_invoices
sales_invoice_lines
supplier_bills
supplier_bill_lines
payments
payment_allocations
bank_accounts
bank_transactions
bank_reconciliations
```

### Document and Workflow Layer

```text
documents
document_links
approval_requests
approval_steps
audit_logs
notifications
```

### AI Governance Layer

```text
ai_suggestions
ai_actions
ai_extraction_results
ai_review_queue
```

The AI-related tables are important because the system must preserve what the AI suggested, what the user approved or rejected, and what was finally posted or changed.

## Journal Entry Design

Journal entries should have a header and lines.

Suggested journal entry fields:

```text
journal_entries
- id
- company_id
- entry_date
- posting_date
- source_type
- source_id
- reference_number
- description
- status
- created_by
- created_at
- posted_by
- posted_at
- reversed_entry_id
```

Suggested journal line fields:

```text
journal_lines
- id
- journal_entry_id
- account_id
- debit_amount
- credit_amount
- currency
- exchange_rate
- tax_code_id
- project_id
- customer_id
- supplier_id
- description
```

Important rule:

- A journal entry can have many lines.
- The total debit amount must equal the total credit amount.
- Use decimal-safe money fields.
- Do not use floating-point numbers for money.

## Immutability and Auditability

Posted accounting records must be immutable.

Do not allow users to silently edit or delete posted transactions.

Use these patterns instead:

| Situation | Required treatment |
|---|---|
| Posted invoice needs correction | Create adjustment or reversal |
| Posted journal needs correction | Create reversal and new entry |
| User wants to delete a posted transaction | Void/cancel while preserving record |
| Closed period needs correction | Post adjustment in an open period unless an authorized override is used |
| AI suggestion is rejected | Preserve the rejected suggestion for auditability |

Every meaningful change must create an audit trail.

Audit logs should capture:

- User
- Timestamp
- Action
- Entity affected
- Previous value where relevant
- New value where relevant
- Reason for change where relevant
- Source module
- AI involvement, if any

## Accrual Accounting Requirements

The system should support accrual accounting, not only cash tracking.

Example: sales invoice issued.

```text
Dr Accounts Receivable
    Cr Revenue
    Cr GST Output Tax, if applicable
```

Example: customer payment received.

```text
Dr Bank
    Cr Accounts Receivable
```

Example: supplier bill received.

```text
Dr Expense or Asset
Dr GST Input Tax, if applicable
    Cr Accounts Payable
```

Example: supplier payment made.

```text
Dr Accounts Payable
    Cr Bank
```

## GST-Ready Design

Not all SMEs are GST-registered, but the system should be GST-capable from the data model stage.

Include:

- Company GST registration setting
- Tax codes
- Tax rates
- Tax amount per transaction line
- Output tax account
- Input tax account
- GST report structure
- Linkage between GST report and source transactions

Common tax-related fields:

```text
tax_code_id
tax_rate
tax_amount
tax_account_id
is_tax_inclusive
```

Do not hard-code GST logic in a way that prevents future expansion.

## Required Reports

The reporting layer must be generated from the ledger, not only from invoice or bill tables.

Minimum reports:

- Profit and Loss Statement
- Balance Sheet
- Trial Balance
- General Ledger
- Accounts Receivable Ageing
- Accounts Payable Ageing
- Cash Flow Summary
- Bank Reconciliation Report
- GST Report, if GST is enabled
- Project or client profitability report
- Expense analysis
- Revenue trend report

The Trial Balance must prove that total debits equal total credits.

## SME-Focused Management Dashboard

The app should help SME owners answer practical questions quickly.

Dashboard should eventually show:

- Current bank/cash position
- Monthly revenue
- Monthly expenses
- Net profit
- Overdue receivables
- Upcoming payables
- Top customers
- Top expenses
- Client/project profitability
- Cash flow outlook
- Missing documents
- Unreconciled bank transactions
- AI-detected anomalies or alerts

Design reports and dashboards for non-accountant business owners, while still keeping accountant-grade records underneath.

## Internal IntelliArtAI Use Cases

The first production use case is IntelliArtAI itself.

The system should support:

- Client billing
- Project milestone invoicing
- Retainer invoicing
- Supplier and software subscription bills
- Contractor costs
- Hosting and cloud costs
- Marketing expenses
- Cash flow tracking
- Receivables tracking
- Project profitability
- Document attachment
- Monthly management reporting

This internal use case should later become a credible product reference:

> Built and used internally by IntelliArtAI to manage consulting operations, client billing, project costs, cash flow, and financial reporting.

## Productization Requirements

Although internal use comes first, avoid building the app in a way that blocks future SME use.

Design for future:

- Multi-company support
- User roles
- Accountant access
- Multi-currency
- Subscription billing
- Data export
- Data import
- Backup and restore
- Onboarding wizard
- Configurable chart of accounts
- Configurable tax settings
- API-first module integration
- Secure document storage
- Role-based access control

## Modular Architecture

Build this as a modular platform, not a single-purpose app.

Suggested layers:

```text
Layer 1: Core Data Layer
- Companies
- Users
- Customers
- Suppliers
- Products/services
- Projects
- Chart of accounts
- Documents
- Transactions

Layer 2: Accounting and Workflow Layer
- Invoicing
- Bills
- Payments
- Journal entries
- Approvals
- Reconciliation
- Period closing
- Audit trail

Layer 3: AI Agent Layer
- Receipt extraction agent
- Invoice assistant
- Cash flow analyst
- Expense classifier
- Sales follow-up agent
- Procurement assistant
- Management reporting agent

Layer 4: Business Intelligence Layer
- Dashboards
- KPIs
- Forecasts
- Exception alerts
- Plain-English business summaries
```

Each future AI module should connect to shared business data, user permissions, audit trails, documents, and approval workflows.

## AI Module Rules

AI features are allowed and encouraged, but they must be controlled.

AI may:

- Extract data from receipts and invoices
- Suggest expense categories
- Suggest journal entries
- Detect duplicates
- Flag anomalies
- Summarize financial performance
- Answer questions using approved business data
- Draft invoice descriptions
- Suggest collection follow-ups
- Identify missing documents

AI must not:

- Post accounting entries without approval
- Modify posted transactions silently
- Delete records
- Override closed periods
- Invent financial data
- Bypass user permissions
- Hide uncertainty

All AI-generated suggestions should be stored and traceable.

Suggested AI workflow:

```text
Document uploaded
→ AI extracts fields
→ AI suggests transaction or category
→ User reviews
→ User approves or rejects
→ System posts if approved
→ Audit trail records full action
```

## Workflow and Approval Requirements

The platform should include a general workflow engine or approval framework that can later be reused across modules.

Examples:

- Approve supplier bill
- Approve expense claim
- Approve manual journal
- Approve AI-suggested transaction
- Approve invoice write-off
- Approve voided transaction
- Approve payment above threshold

Approval records should include:

- Requester
- Approver
- Status
- Timestamp
- Comments
- Related document or transaction
- Final action taken

## User Roles and Controls

Suggested roles:

| Role | Typical permissions |
|---|---|
| Owner/Admin | Full access |
| Bookkeeper | Create transactions, reconcile bank |
| Accountant | Review, adjust, close periods |
| Sales user | Create invoices and view customers |
| Approver | Approve bills, expenses, or payments |
| Read-only user | View dashboards and reports |

Important controls:

- Role-based access control
- Closed-period lock
- Sequential invoice numbering
- Duplicate transaction detection
- Duplicate invoice detection
- Mandatory reason for voiding
- Audit log for all changes
- Bank reconciliation protection
- Maker-checker approval where appropriate

## Period Closing

The system should support monthly and annual closing.

Minimum period-close process:

- Reconcile bank accounts
- Review AR ageing
- Review AP ageing
- Review uncategorized transactions
- Review missing documents
- Review GST position, if applicable
- Post required adjustments
- Generate reports
- Lock period

Closed periods should not be editable by normal users.

Corrections after close should generally be posted as adjustment entries in an open period.

## Bank Reconciliation

Bank reconciliation is an important SME feature.

The system should allow:

- Bank transaction import
- Matching bank transactions to invoices, bills, or journals
- One-to-one and many-to-one matching
- Reconciliation status
- Prevention of double matching
- Reconciliation report
- Unmatched transaction list

## Document Management

Every financial transaction should be able to link to source documents.

Examples:

- Tax invoice
- Supplier bill
- Receipt
- Contract
- Purchase order
- Delivery order
- Bank statement
- Credit note
- Debit note

Documents should be searchable and linked to their related records.

Do not allow the system to lose the connection between a ledger entry and its supporting document.

## Accountant-Friendly Requirements

The system should support accountants rather than attempt to replace them.

Include:

- General ledger export
- Trial balance export
- Journal entry export
- Chart of accounts export
- Source document access
- Adjustment journals
- Opening balances
- Year-end closing support
- Accountant notes
- CSV/Excel export

Marketing direction should be:

> Keeps SME records clean, organized, and accountant-ready.

Avoid:

> No accountant needed.

## Coding and Implementation Standards

Codex should follow these technical principles:

1. All accounting postings must go through a dedicated posting service.
2. The frontend must not directly create ledger entries.
3. Every journal entry must balance before posting.
4. Posted entries must be immutable.
5. Corrections must use reversals or adjustments.
6. Use decimal-safe money handling.
7. Every transaction must have company, date, source, status, and audit metadata.
8. Closed accounting periods must not be modifiable by normal users.
9. Reports should come from the ledger.
10. AI suggestions must require user review before posting.
11. Use modular services or modules.
12. Use APIs or clean service boundaries between modules.
13. Maintain shared company, user, role, document, and audit models.
14. Write automated tests for accounting logic.
15. Prioritize data integrity over UI convenience.

## Required Automated Tests

Codex must generate automated tests for core accounting scenarios.

Minimum test cases:

```text
- Sales invoice posts correct AR, revenue, and GST entries.
- Customer payment clears AR.
- Supplier bill posts AP and expense/asset entries.
- Supplier payment clears AP.
- Journal entry cannot save if debits do not equal credits.
- Posted transaction cannot be silently edited.
- Posted transaction can be reversed.
- Closed period cannot be modified by normal users.
- Voided invoice creates an appropriate reversal.
- Bank transaction cannot be reconciled twice.
- GST report agrees with tax ledger accounts.
- Trial balance total debits equal total credits.
- User without permission cannot approve or post restricted transactions.
- AI suggestion cannot post without human approval.
```

These tests are mandatory because accounting accuracy is core to the product.

## Recommended MVP Scope

Phase 1 should focus on the bookkeeping core and internal IntelliArtAI use.

MVP modules:

```text
1. Company setup
2. User and role setup
3. Chart of accounts
4. Customers
5. Suppliers
6. Sales invoices
7. Supplier bills
8. Payments received
9. Payments made
10. Manual journal entries
11. Bank account setup
12. Bank transaction import
13. Bank reconciliation
14. Document upload and linking
15. Audit trail
16. Profit and Loss
17. Balance Sheet
18. Trial Balance
19. General Ledger
20. Period lock
```

## Post-MVP Roadmap

After the bookkeeping core works, add:

```text
- GST reporting
- Fixed asset register
- Multi-currency
- Project/client profitability
- Cash flow forecast
- AI receipt extraction
- AI expense categorization
- AI management summary
- Accountant portal
- Approval workflows
- Sales module
- Procurement module
- HR claims module
- Operations/project module
- Management dashboard
```

## Future IntelliArtAI Module Structure

Potential module naming:

```text
IntelliArtAI Core
- Finance Core
- Document Core
- Workflow Core
- AI Agent Modules
- Management Dashboard
```

Possible product/module names:

```text
IntelliBooks
IntelliDocs
IntelliFinance
IntelliSales
IntelliOps
IntelliHR
IntelliBoard
```

These names are placeholders and should not be hard-coded into architecture.

## Important Product Strategy

Do not try to immediately compete feature-for-feature with Xero, QuickBooks, or Zoho Books.

Start with a focused SME segment where IntelliArtAI has credibility:

- Consulting firms
- Professional services firms
- Small engineering or project-based companies
- Agencies
- Contractors
- Service-based SMEs

Initial value proposition:

```text
Bookkeeping + cash flow visibility + project profitability + document control + AI assistance
```

## Final Guiding Principle

Build the first version as a reliable internal bookkeeping and financial operations platform.

But architect it as the foundation of a larger SME operating framework where every future AI module shares:

- Trusted business data
- Proper permissions
- Source documents
- Approval workflows
- Audit trails
- Ledger-connected reporting

The most important architectural decision is:

> Do not build isolated AI tools. Build a common operating framework where every AI module connects to trusted data, permissions, audit trails, documents, workflows, and financial records.

