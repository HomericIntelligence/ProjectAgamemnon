#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Configure first to get compile_commands.json
cmake --preset debug -DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF >/dev/null 2>&1 || true

find "${ROOT_DIR}/include" "${ROOT_DIR}/src" "${ROOT_DIR}/test" \
  -name "*.cpp" -o -name "*.hpp" | \
  xargs clang-tidy \
    -p "${ROOT_DIR}/build/debug" \
    --config-file="${ROOT_DIR}/.clang-tidy" \
    "$@"
