-- name: invoice_ageing
-- Aggregate payment lines BEFORE joining to avoid invoice duplication.
WITH paid AS (
 SELECT invoice_id, SUM(paid_paise) AS paid_paise
 FROM payments WHERE payment_date <= date(:as_of) GROUP BY invoice_id
), balances AS (
 SELECT i.*, COALESCE(p.paid_paise,0) AS paid_paise,
        i.invoice_paise - COALESCE(p.paid_paise,0) AS outstanding_paise,
        CAST(julianday(:as_of) - julianday(i.due_date) AS INTEGER) AS days_past_due
 FROM invoices i LEFT JOIN paid p USING(invoice_id)
 WHERE invoice_date <= date(:as_of)
)
SELECT *, CASE WHEN outstanding_paise = 0 THEN 'Paid'
               WHEN days_past_due <= 0 THEN 'Not overdue'
               WHEN days_past_due <= 30 THEN '1-30 days'
               WHEN days_past_due <= 60 THEN '31-60 days'
               WHEN days_past_due <= 90 THEN '61-90 days'
               ELSE '90+ days' END AS ageing_bucket
FROM balances ORDER BY invoice_id;

-- name: customer_exposure
WITH paid AS (
 SELECT invoice_id, SUM(paid_paise) AS amount FROM payments
 WHERE payment_date <= date(:as_of) GROUP BY invoice_id
), exposure AS (
 SELECT c.customer_id, c.segment,
 COALESCE(SUM(i.invoice_paise - COALESCE(p.amount,0)),0) AS outstanding_paise,
 COALESCE(SUM(CASE WHEN i.due_date < date(:as_of)
 THEN i.invoice_paise - COALESCE(p.amount,0) ELSE 0 END),0) AS overdue_paise
 FROM customers c LEFT JOIN invoices i
 ON i.customer_id = c.customer_id AND i.invoice_date <= date(:as_of)
 LEFT JOIN paid p ON p.invoice_id = i.invoice_id GROUP BY c.customer_id, c.segment
)
SELECT *, DENSE_RANK() OVER(ORDER BY overdue_paise DESC) AS overdue_rank
FROM exposure ORDER BY overdue_paise DESC, customer_id;
