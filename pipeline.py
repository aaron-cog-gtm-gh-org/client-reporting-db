from db import connect


def run():
    with connect() as db:
        db.execute("CREATE OR REPLACE TABLE crd_loans AS SELECT * FROM rpt_loans")


if __name__ == "__main__":
    run()
