# SENTINEL — Testing

39 tests, mocked LLM, no live keys. Run: `cd backend && python3 -m pytest tests -q` (SQLite, no Redis/Postgres needed).

Coverage vs spec §15 (20 scenarios):
1 Multi-step ✅ (test_demo1), 2 Step limit ✅ (test_demo2 + limits unit), 3 Tool-call limit ✅ (unit), 4 Cost limit ✅ (test_demo3 + budget unit), 5 Invalid args ✅ (validator unit), 6 Unauthorized tool ✅ (test_demo4), 7 Injection ✅ (validator unit), 8 LLM timeout ✅ (retry unit), 9 Tool timeout ✅ (retry path), 10 Retry exhaustion ✅, 11 Provider fallback ✅ (get_provider_with_fallback), 12 Approval/reject ✅ (API), 13 Cancel ✅, 14 Resume ✅ (worker + resume endpoint), 15 Duplicate prevention ✅ (idempotency key), 16 Concurrent budget ✅ (reservation logic + DB sums), 17 Redis disconnect ✅ (HotStateStore fallback), 18 DB failure ✅ (rollback handling), 19 Partial results ✅, 20 Cost aggregation ✅ (tracker unit + /cost endpoint).
Security suite: sandbox blocks, allowlist, action-hash binding, risk classification.
CI: `.github/workflows/ci.yml` runs pytest + ruff on push/PR.
