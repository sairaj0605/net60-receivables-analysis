"""Small deterministic fixtures exercising business boundaries in the actual SQL."""
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parent
AS_OF = '2026-10-21'


def fixture(folder):
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    connection.executescript((ROOT / 'schema.sql').read_text())
    blocks = (ROOT / 'analysis.sql').read_text().split('-- name: ')[1:]
    sql = dict(block.split('\n', 1) for block in blocks)
    return connection, {k.strip(): v for k, v in sql.items()}


class BusinessBoundaries(unittest.TestCase):
    def test_receivables_multiple_and_future_payments(self):
            c, q = fixture('02-net60-receivables')
            self.addCleanup(c.close)
            c.execute("INSERT INTO customers VALUES(1,'Independent')")
            c.executemany('INSERT INTO invoices VALUES(?,?,?,?,?)',
                          [(1,1,'2026-08-22','2026-10-21',10000),
                           (2,1,'2026-07-23','2026-09-21',10000),
                           (3,1,'2026-07-22','2026-09-20',10000)])
            c.executemany('INSERT INTO payments VALUES(?,?,?,?)',
                          [(1,2,'2026-10-01',2000),(2,2,'2026-10-02',3000),
                           (3,2,'2026-10-22',5000),(4,3,'2026-10-01',10000)])
            r = {x['invoice_id']: dict(x) for x in c.execute(q['invoice_ageing'], {'as_of': AS_OF})}
            self.assertEqual(r[1]['ageing_bucket'], 'Not overdue')
            self.assertEqual(r[2]['ageing_bucket'], '1-30 days')
            self.assertEqual(r[2]['outstanding_paise'], 5000)
            self.assertEqual(r[3]['ageing_bucket'], 'Paid')
            exposure = dict(c.execute(q['customer_exposure'], {'as_of': AS_OF}).fetchone())
            self.assertEqual(exposure['outstanding_paise'], 15000)
            self.assertEqual(exposure['overdue_paise'], 5000)

if __name__ == "__main__":
    unittest.main(verbosity=2)
