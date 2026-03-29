set shell := ["bash", "-c"]

default:
  @just --list

build:
  cmake --preset debug && cmake --build --preset debug

test:
  ctest --preset debug --output-on-failure

lint:
  ./scripts/lint.sh

format:
  ./scripts/format.sh

format-check:
  ./scripts/format.sh --check

coverage:
  cmake --preset coverage && cmake --build --preset coverage && ./scripts/coverage.sh

clean:
  rm -rf build install

ci:
  cmake --preset ci && cmake --build --preset ci && ctest --preset ci
