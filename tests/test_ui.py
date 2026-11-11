import duckdb
import pytest

from ui.server import render


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / "ui.duckdb"
    monkeypatch.setenv("RECON_DB", str(path))
    with duckdb.connect(str(path)) as db:
        db.execute("CREATE TABLE crd_loans (loan_id VARCHAR, client_id VARCHAR, product_name VARCHAR, currency VARCHAR, balance DECIMAL(18,2), balance_usd DECIMAL(18,2), rm_id VARCHAR, segment VARCHAR, client_name VARCHAR)")
        db.execute("INSERT INTO crd_loans VALUES ('L1','C01','Mortgage','GBP',1000,1270,'RM01','Private','Client <One>'), ('L1','C01','Mortgage','GBP',1000,1270,'RM90','Private','Client <One>')")
    return path


def test_pages_and_release_connection(database):
    for url, text in [("/", "Your clients"), ("/loan?id=L1", "2 rows"), ("/client?id=C01", "2,540.00")]:
        status, html = render(url)
        assert status == 200
        assert text in html
        assert 'charset="utf-8"' in html
    with duckdb.connect(str(database)) as db:
        db.execute("UPDATE crd_loans SET balance_usd=1300 WHERE loan_id='L1'")
    assert "1,300.00" in render("/loan?id=L1")[1]


@pytest.mark.parametrize("url", ["/loan?id=absent", "/client?id=absent"])
def test_absent_record(database, url):
    status, html = render(url)
    assert status == 200
    assert "No records found" in html


def test_missing_table_and_missing_database(tmp_path, monkeypatch):
    path = tmp_path / "missing.duckdb"
    monkeypatch.setenv("RECON_DB", str(path))
    assert render("/")[0] == 503
    assert not path.exists()
    with duckdb.connect(str(path)):
        pass
    status, html = render("/")
    assert status == 503
    assert "Data refreshing" in html
    assert "Run the pipeline" in html


def test_locked_database(database, monkeypatch):
    def locked(*args, **kwargs):
        assert kwargs["read_only"] is True
        raise duckdb.IOException("locked")
    monkeypatch.setattr("ui.server.duckdb.connect", locked)
    assert render("/loan?id=L1")[0] == 503


def test_empty_table_and_unknown_page(database):
    with duckdb.connect(str(database)) as db:
        db.execute("DELETE FROM crd_loans")
    assert "No records found" in render("/")[1]
    assert render("/unknown")[0] == 404


def test_every_stored_row_and_escape(database):
    status, html = render("/loan?id=L1")
    assert status == 200
    assert "RM01" in html and "RM90" in html
    assert html.count("1,270.00") == 2
    assert "Client &lt;One&gt;" in html
    assert "<One>" not in html
