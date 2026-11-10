import os
from pathlib import Path

import duckdb


def connect():
    path = Path(os.environ.get("RECON_DB", "~/lending-demo/lending.duckdb")).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))
