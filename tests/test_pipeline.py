import csv

import duckdb
import pytest

from pipeline import run
from recon import HEADER, reconcile


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / "test.duckdb"
    monkeypatch.setenv("RECON_DB", str(path))
    with duckdb.connect(str(path)) as db:
        db.execute("""
            CREATE TABLE sor_loans (
                loan_id VARCHAR, balance_usd DECIMAL(18,3), status VARCHAR
            )
        """)
        db.execute("CREATE TABLE rpt_loans (loan_id VARCHAR, balance_usd DECIMAL(18,3))")
    return path


def test_load_schema_and_idempotency(database):
    with duckdb.connect(str(database)) as db:
        db.execute("INSERT INTO rpt_loans VALUES ('L1', 125.25)")
    run()
    run()
    with duckdb.connect(str(database)) as db:
        assert db.execute("SELECT * FROM crd_loans").fetchall() == db.execute("SELECT * FROM rpt_loans").fetchall()
        assert db.execute("DESCRIBE crd_loans").fetchall() == db.execute("DESCRIBE rpt_loans").fetchall()


def test_empty_recon(database, tmp_path):
    run()
    with duckdb.connect(str(database)) as db:
        output = tmp_path / "out/breaks.csv"
        assert reconcile(db, output) == []
        assert list(csv.reader(output.open())) == [HEADER]


def test_recon_categories_threshold_and_closed_scope(database, tmp_path, capsys):
    with duckdb.connect(str(database)) as db:
        db.execute("""
            INSERT INTO sor_loans VALUES
                ('L1', 100, 'ACTIVE'), ('L2', 200, 'ACTIVE'),
                ('L3', 300, 'ACTIVE'), ('L4', 400, 'CLOSED'),
                ('L5', 500, 'ACTIVE'), ('L6', 600, 'ACTIVE'),
                ('L7', 700, 'CLOSED')
        """)
        db.execute("""
            INSERT INTO rpt_loans VALUES
                ('L2', 201), ('L3', 300), ('L3', 300),
                ('L5', 500.005), ('L6', 600.006),
                ('L7', 701), ('L7', 701)
        """)
    run()
    with duckdb.connect(str(database)) as db:
        output = tmp_path / "breaks.csv"
        rows = reconcile(db, output)
        assert [(r[0], r[1], r[4]) for r in rows] == [
            ('L1', 'loan_id', 'missing_in_crd'),
            ('L2', 'balance_usd', 'value_mismatch'),
            ('L3', 'loan_id', 'duplicate_in_crd'),
            ('L6', 'balance_usd', 'value_mismatch')]
        first = output.read_bytes()
        reconcile(db, output)
        assert output.read_bytes() == first
    assert "SOR=1700.00 CRD=1901.01" in capsys.readouterr().out


def test_missing_upstream(database):
    with pytest.raises(duckdb.CatalogException):
        with duckdb.connect(str(database)) as db:
            reconcile(db)
    with duckdb.connect(str(database)) as db:
        db.execute("DROP TABLE rpt_loans")
    with pytest.raises(duckdb.CatalogException):
        run()
