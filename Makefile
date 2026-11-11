PYTHON ?= python3

.PHONY: run test pipeline recon ui
run:
	$(PYTHON) pipeline.py

test:
	$(PYTHON) -m pytest -q

ui:
	$(PYTHON) -m ui.server

pipeline:
	$(MAKE) -C ../lending-sor-extract run
	$(MAKE) -C ../loan-enrichment run
	$(MAKE) -C ../client-reference-join run
	$(MAKE) run

recon:
	$(PYTHON) recon.py
