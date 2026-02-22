#!/usr/bin/env bash
set -euo pipefail

if command -v brightness >/dev/null 2>&1; then
    echo "brightness command already exists"
    exit 0
elif [[ -d brightness ]]; then
    echo "brightness repo already exists in $(pwd)/brightness"
    exit 0
fi

git clone https://github.com/joshOberhaus/brightness.git
cd brightness
make
sudo make install
