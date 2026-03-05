#!/bin/bash
# Portugal New Companies - Data Enrichment
# Usage: ./enrich.sh

set -e
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"

uv run python enrich.py
