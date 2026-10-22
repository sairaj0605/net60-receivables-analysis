from pathlib import Path
import sqlite3
import random
import json
from datetime import date, timedelta
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parent
DATA = ROOT
OUT = ROOT
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
AS_OF = '2026-10-21'

def database(tables):
    conn = sqlite3.connect(ROOT / 'analysis.sqlite')
    # Rebuild in reverse dependency order. Foreign keys stay enabled for inserts.
    conn.execute('PRAGMA foreign_keys = OFF')
    for name in reversed(list(tables)):
        conn.execute(f'DROP TABLE IF EXISTS "{name}"')
    conn.executescript((ROOT / 'schema.sql').read_text())
    conn.execute('PRAGMA foreign_keys = ON')
    for name, frame in tables.items():
        frame.to_csv(DATA / f'{name}.csv', index=False)
        frame.to_sql(name, conn, if_exists='append', index=False)
    violations = conn.execute('PRAGMA foreign_key_check').fetchall()
    assert not violations, violations
    return conn

def queries(conn):
    # Every block starts with -- name: <output_name> and contains one SQL statement.
    text = (ROOT / 'analysis.sql').read_text()
    results = {}
    for block in text.split('-- name: ')[1:]:
        name, sql = block.split('\n', 1)
        frame = pd.read_sql_query(sql.strip(), conn, params={'as_of': AS_OF})
        results[name.strip()] = frame
        frame.to_csv(OUT / f'{name.strip()}.csv', index=False)
    return results

def parity(actual, expected, key, columns):
    a = actual.sort_values(key)[columns].reset_index(drop=True)
    b = expected.sort_values(key)[columns].reset_index(drop=True)
    assert_frame_equal(a, b, check_dtype=False, check_exact=False, atol=1e-7, rtol=1e-7)

def chart(frame, x, y, title, ylabel):
    plt.rcParams.update({'font.size': 10})
    fig, ax = plt.subplots(figsize=(9, 4.8), layout='constrained')
    ax.bar(frame[x].astype(str), frame[y], color='#24658b')
    ax.set(title=title, ylabel=ylabel)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(axis='x', rotation=30)
    fig.savefig(OUT / 'summary.png', dpi=160)
    plt.close(fig)

def finish(text, checks):
    (OUT / 'findings.md').write_text(text, encoding='utf-8')
    (OUT / 'validation.json').write_text(json.dumps({'status': 'passed', 'checks': checks}, indent=2) + '\n')
    print(text)

def bucket(days, balance):
    if balance == 0: return 'Paid'
    if days <= 0: return 'Not overdue'
    if days <= 30: return '1-30 days'
    if days <= 60: return '31-60 days'
    if days <= 90: return '61-90 days'
    return '90+ days'

def main():
    rng = random.Random(73)
    cutoff = date.fromisoformat(AS_OF)
    customers = pd.DataFrame([{'customer_id': i, 'segment': rng.choice(['Independent','Regional','National'])}
                              for i in range(1,121)])
    invoices, payments = [], []
    for i in range(1,1801):
        issued = cutoff - timedelta(days=rng.randint(0,240))
        amount = rng.randint(100000,2000000)
        invoices.append({'invoice_id': i,'customer_id': rng.randint(1,120), 'invoice_date': str(issued),
                         'due_date': str(issued + timedelta(days=60)), 'invoice_paise': amount})
        mode = rng.choice(['none','partial','full'])
        if mode != 'none':
            first = issued + timedelta(days=rng.randint(5,100))
            part = amount // 2
            payments.append({'payment_id':len(payments)+1,'invoice_id':i,'payment_date':str(first),'paid_paise':part})
            if mode == 'full':
                payments.append({'payment_id':len(payments)+1,'invoice_id':i,
                                 'payment_date':str(first+timedelta(days=rng.randint(1,30))), 'paid_paise':amount-part})
    invoices, payments = pd.DataFrame(invoices), pd.DataFrame(payments)
    conn = database({'customers':customers,'invoices':invoices,'payments':payments})
    result = queries(conn)
    paid = payments[payments.payment_date <= AS_OF].groupby('invoice_id').paid_paise.sum()
    expected = invoices.merge(paid.rename('paid_paise'), on='invoice_id',how='left').fillna({'paid_paise':0})
    expected['outstanding_paise'] = expected.invoice_paise - expected.paid_paise
    expected['days_past_due'] = (pd.Timestamp(AS_OF) - pd.to_datetime(expected.due_date)).dt.days
    expected['ageing_bucket'] = [bucket(d,b) for d,b in zip(expected.days_past_due,expected.outstanding_paise)]
    parity(result['invoice_ageing'],expected,'invoice_id',['invoice_id','paid_paise','outstanding_paise','days_past_due','ageing_bucket'])
    overdue = expected[expected.days_past_due > 0].groupby('customer_id').outstanding_paise.sum()
    exposure = customers.merge(expected.groupby('customer_id').outstanding_paise.sum(),on='customer_id',how='left')
    exposure = exposure.merge(overdue.rename('overdue_paise'),on='customer_id',how='left').fillna(0)
    parity(result['customer_exposure'],exposure,'customer_id',['customer_id','outstanding_paise','overdue_paise'])
    assert expected.outstanding_paise.min() >= 0
    assert int(expected.outstanding_paise.sum()) == int(invoices.invoice_paise.sum() - paid.sum())
    assert [bucket(x,100) for x in [0,1,30,31,60,61,90,91]] == ['Not overdue','1-30 days','1-30 days','31-60 days','31-60 days','61-90 days','61-90 days','90+ days']
    assert bucket(100,0) == 'Paid'
    order=['Not overdue','1-30 days','31-60 days','61-90 days','90+ days']
    ageing=expected[expected.outstanding_paise > 0].groupby('ageing_bucket').outstanding_paise.sum().reindex(order,fill_value=0).reset_index()
    ageing['outstanding_inr']=ageing.outstanding_paise/100
    ageing.to_csv(OUT/'ageing_summary.csv',index=False)
    chart(ageing,'ageing_bucket','outstanding_inr','Net 60 open receivables | synthetic data','INR')
    total=expected.outstanding_paise.sum()/100
    late=expected.loc[expected.days_past_due > 0,'outstanding_paise'].sum()/100
    finish(f"# Receivables findings\n\nAs of {AS_OF}; synthetic demonstration.\n\n"
           f"- Reviewed {len(invoices):,} Net 60 invoices for {len(customers)} customers.\n"
           f"- Open receivables: INR {total:,.2f}; overdue: INR {late:,.2f} ({late/total:.1%} of open balance).\n"
           f"- Largest overdue customer balance: INR {result['customer_exposure'].overdue_paise.max()/100:,.2f}.\n\n"
           "## Recommended action\nUse ranked customer balances to prioritise statement review and follow-up. "
           "Confirm payment allocations and disputes before escalation.\n\n"
           "## Limits\nThis monitors trade receivables; it is not consumer credit scoring or an underwriting model. "
           "No write-offs, credits, disputed invoices or foreign currencies are included. "
           "Due today is not overdue. Future-dated payments are deliberately excluded from the as-of balance.\n",
           ['SQL/Pandas invoice and customer parity','invoice less payments reconciles to open balance',
            'ageing bucket boundaries checked','future payments excluded','no overallocated invoice','foreign keys checked'])
    conn.close()

if __name__ == '__main__':
    main()
