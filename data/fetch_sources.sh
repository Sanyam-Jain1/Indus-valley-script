#!/usr/bin/env bash
# Download the third-party source corpora used by the analysis into data/raw/.
# Nothing downloaded here is committed (see .gitignore); each source keeps its own licence.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p raw
clone() {  # clone <owner/repo> <dir> <pinned-commit-or-empty>
  if [ ! -d "raw/$2" ]; then git clone -q https://github.com/$1 "raw/$2"; fi
  if [ -n "${3:-}" ]; then git -C "raw/$2" checkout -q "$3"; fi
}
# 1. Yajnadevam's digitisation of the ICIT corpus (GPL-3.0): sequences, sites, object types, motifs.
clone yajnadevam/indus-website indus-website 2434249618b1e74de3f26d28b90dfde093c3dd94
# 2. joyboseroy/indus_decipher: carries a CSV export of Mahadevan's 1977 concordance (M77, 3,573 lines).
clone joyboseroy/indus_decipher indus_decipher cd600349f6d3193a241c3eb87ff80a2a65377efc
echo "sources ready in data/raw/"
