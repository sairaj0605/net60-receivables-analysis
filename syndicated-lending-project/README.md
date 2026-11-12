# Syndicated Lending Operations & Credit Risk Analytics

**Portfolio case study | Synthetic data only | Not a live bank system**

A reproducible loan-agency / middle-office analytics case study simulating 48 syndicated credit facilities and 336 servicing events (drawdowns, repayments, interest payments and fees). Built to demonstrate operational controls, borrower concentration, maturity monitoring and transaction-exception analysis relevant to middle-office operations.

> All records, counterparties, values and metrics are generated for learning. This project was developed as an independent portfolio exercise; it is not an actual University of Exeter assessed project or Goldman Sachs work.

## Business questions
1. How much total commitment and utilisation does the loan portfolio carry?
2. Which borrowers and industries drive funded-exposure concentration?
3. Which servicing events are late, unreconciled or missing documentation?
4. Which facilities mature within 12 months?
5. Where should middle-office analysts prioritise investigations?

## Architecture
```
data/facilities.csv + data/servicing_events.csv
      -> Python validation and joins (src/analyze.py)
      -> output/summary.json + output/facility_risk.csv + output/exception_queue.csv
      -> matplotlib report (output/portfolio_dashboard.png)
SQL companion queries: sql/loan_operations.sql
```

## Quick start
```bash
python -m pip install -r requirements.txt
python src/analyze.py
python -m unittest discover -s tests -v
```
Run from the repository root. Generated outputs are ignored by Git; no proprietary banking files are included.

## Data dictionary
**facilities.csv**: facility_id; borrower; industry; commitment_usd; utilisation_pct; risk_rating (1 = strongest, 5 = weakest); spread_bps; maturity_date.

**servicing_events.csv**: event_id; facility_id; event_type; due_date; settlement_date (blank = pending); expected_usd; actual_usd (blank = pending); docs_complete (0/1).

## Control definitions
- **Cash mismatch:** absolute actual minus expected > $1, for settled transactions.
- **Late settlement:** settlement_date after due_date.
- **Overdue open:** unsettled with due_date before 2026-11-12 (fixed analysis date for deterministic results).
- **Documentation exception:** docs_complete = 0.
- **Maturing 12 months:** maturity date from 2026-11-12 through 2027-11-12.
- **Funded exposure:** commitment × utilisation_pct / 100; **not** a regulatory EAD or credit-loss estimate.

A single event may have multiple exception flags. Exception counts should not be added together as if mutually exclusive.

## Limits
No legal agreements, borrower real-world data, agent notices, multicurrency FX, daily rate resets, amortisation schedules, RFR conventions, covenant packages, participation allocations or Loan IQ integration. This is **portfolio analytics**, not an operational loan-servicing platform or validated credit model.

## Sample interview framing
"I constructed a synthetic syndicated-loan operations dataset, built SQL and Python controls for settlement timeliness, cash reconciliation and documentation completeness, and created a borrower-concentration and exception dashboard. The project helped me understand middle-office workflows, but I have not processed live syndicated loans."

## License
MIT License.