# client-reporting-db
Reads: rpt_loans; recon reads sor_loans and crd_loans.
Writes: crd_loans and out/breaks.csv.
Owns: Wealth reporting CRD load and reconciliation.
Run: pip install -r requirements.txt; make run; make test. Shared DB: $RECON_DB (default ~/lending-demo/lending.duckdb); make pipeline then make recon orchestrates siblings.

## Client Reporting UI
Run `make ui` and open http://127.0.0.1:8102. Open a client for lending holdings
and the total USD, or find a loan by ID to see every stored row. This read-only
UI reads only `crd_loans` from `$RECON_DB` (same default as above), with a
short-lived connection per request. Run `make pipeline` first; refresh the page
after a load. If data is unavailable or refreshing, the page asks you to retry.
Stop the server with Ctrl-C.
