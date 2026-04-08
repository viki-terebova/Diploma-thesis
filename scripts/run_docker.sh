#!/usr/bin/env bash
set -eu

cd "$(dirname "$0")/.."
docker compose up --build
