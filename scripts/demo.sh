#!/usr/bin/env bash
# SENTINEL demo smoke: register → execute → trace. Requires running backend on :8000.
set -e
API=http://localhost:8000/api/v1
TOKEN=$(curl -s -X POST $API/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"password123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
echo "token: ${TOKEN:0:12}…"
curl -s -X POST $API/executions -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"objective":"Research agentic AI and summarize","mode":"supervised"}' | python3 -m json.tool
echo "--- health ---"
curl -s http://localhost:8000/health
