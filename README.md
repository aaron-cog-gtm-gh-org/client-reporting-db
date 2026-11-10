# client-reporting-db
Reads: rpt_loans; recon reads sor_loans and crd_loans.
Writes: crd_loans and out/breaks.csv.
Owns: Wealth reporting CRD load and reconciliation.
Run: pip install -r requirements.txt; make run; make test. Shared DB: $RECON_DB (default ~/lending-demo/lending.duckdb); make pipeline then make recon orchestrates siblings.
