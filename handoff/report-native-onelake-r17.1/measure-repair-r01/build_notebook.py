"""Package the readable repair cell; no Fabric calls."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
code = (ROOT / "REPAIR TEST FEED.py").read_text()
compile(code, "REPAIR TEST FEED.py", "exec")
notebook = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {"kernelspec": {"display_name": "Synapse PySpark",
                              "language": "python", "name": "synapse_pyspark"}},
    "cells": [{"cell_type": "markdown", "id": "about", "metadata": {}, "source": [
        "# Repair inherited feed syntax on the existing R17.1 TEST only\n",
        "Backs up the current definition privately, moves terminal displayFolder metadata,\n",
        "and checks model and cloud-connection preservation. No explicit refresh or publication.\n"]},
        {"cell_type": "code", "id": "repair-test-only", "metadata": {},
         "execution_count": None, "outputs": [], "source": code.splitlines(keepends=True)}]}
(ROOT / "ForecastMaster TEST Feed Repair R01.ipynb").write_text(
    json.dumps(notebook, ensure_ascii=False, indent=1) + "\n")
print("Packaged one readable TEST repair cell:", len(code.encode()), "bytes")
