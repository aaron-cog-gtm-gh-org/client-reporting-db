import csv
from collections import Counter
from pathlib import Path

from db import connect

OUT = Path(__file__).resolve().parent / "out/breaks.csv"
HEADER = ["loan_id", "field", "sor_value", "crd_value", "break_type"]


def reconcile(db, output=OUT):
    rows = db.execute("""
        WITH source AS (
            SELECT * FROM sor_loans WHERE status != 'CLOSED'
        ), target AS (
            SELECT c.loan_id, count(*) AS row_count, max(c.balance_usd) AS balance_usd
            FROM crd_loans c
            JOIN source s ON c.loan_id = s.loan_id
            GROUP BY c.loan_id
        ), breaks AS (
            SELECT s.loan_id, 'loan_id' AS field, s.loan_id AS sor_value,
                   '' AS crd_value, 'missing_in_crd' AS break_type
            FROM source s LEFT JOIN target t USING (loan_id)
            WHERE t.loan_id IS NULL
            UNION ALL
            SELECT s.loan_id, 'balance_usd', s.balance_usd::VARCHAR,
                   t.balance_usd::VARCHAR, 'value_mismatch'
            FROM source s JOIN target t USING (loan_id)
            WHERE abs(s.balance_usd - t.balance_usd) > 0.005
            UNION ALL
            SELECT loan_id, 'loan_id', '1', row_count::VARCHAR, 'duplicate_in_crd'
            FROM target WHERE row_count > 1
        )
        SELECT * FROM breaks ORDER BY loan_id, field, break_type, sor_value, crd_value
    """).fetchall()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADER)
        writer.writerows(rows)
    print(f"Breaks: {len(rows)}")
    for (kind, field), count in sorted(Counter((r[4], r[1]) for r in rows).items()):
        print(f"  {kind} / {field}: {count}")
    sor_total = db.execute(
        "SELECT coalesce(sum(balance_usd), 0) FROM sor_loans WHERE status != 'CLOSED'"
    ).fetchone()[0]
    crd_total = db.execute("""
        SELECT coalesce(sum(c.balance_usd), 0) FROM crd_loans c
        WHERE EXISTS (
            SELECT 1 FROM sor_loans s
            WHERE s.loan_id = c.loan_id AND s.status != 'CLOSED'
        )
    """).fetchone()[0]
    print(f"Total balance_usd: SOR={sor_total:.2f} CRD={crd_total:.2f}")
    return rows


if __name__ == "__main__":
    with connect() as db:
        reconcile(db)
