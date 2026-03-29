#!/usr/bin/env bash
set -euo pipefail

cmake --preset debug
cmake --build --preset debug
ctest --preset debug --output-on-failure "$@"
