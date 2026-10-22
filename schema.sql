CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, segment TEXT NOT NULL);
CREATE TABLE invoices (
 invoice_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
 invoice_date TEXT NOT NULL, due_date TEXT NOT NULL,
 invoice_paise INTEGER NOT NULL CHECK(invoice_paise > 0)
);
CREATE TABLE payments (
 payment_id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL REFERENCES invoices(invoice_id),
 payment_date TEXT NOT NULL, paid_paise INTEGER NOT NULL CHECK(paid_paise > 0)
);
CREATE INDEX payments_invoice ON payments(invoice_id);
