#!/bin/bash
set -e
cd "/mnt/c/Users/Manas/Downloads/Total Job Application process flow/projects/agent-task-environment-state-benchmark"
echo "=== pytest ==="
.venv/bin/python -m pytest tests/ -v 2>&1 | tee docs_test_output.tmp
mkdir -p docs
mv docs_test_output.tmp docs/test_output.txt
echo "=== adversarial suite ==="
.venv/bin/python scripts/run_adversarial.py
echo "=== main benchmark (--reset-db) ==="
.venv/bin/python scripts/run_benchmark.py --reset-db
