# Database — PostgreSQL

## Schema discipline

- **`NOT NULL`** unless nullable is semantically meaningful. Defaults set explicitly.
- **Foreign keys** with correct `ON DELETE` (`CASCADE`, `SET NULL`, `RESTRICT`) matching the business rule. FKs are not indexed automatically — index every FK used in joins or `WHERE`.
- **Unique constraints** enforce real business invariants: `UNIQUE(user_id, provider, external_id)`.
- **`CHECK` constraints** for domain rules: `CHECK (amount_cents >= 0)`, `CHECK (status IN (...))` — but prefer a proper enum or a lookup table.
- **Timestamps**: `created_at`, `updated_at` as `timestamptz`, defaulted in SQL, not client-provided. Store UTC; format in the app.
- **JSONB** columns have a documented shape and a Zod parser at read time. Don't use JSONB as "schemaless" unless you really mean it.
- **Ownership column** on every user-scoped table (`user_id`). Every query touches it in the `WHERE` clause.

## Indexes (PG docs Ch. 11)

- **B-tree** for equality + range (the default, what you want 90% of the time).
- **GIN** for `@>`, `?`, full-text, JSONB containment, arrays.
- **BRIN** for huge append-only time-series (tiny index, sequential data only).
- **GiST** for ranges / geo / exclusion constraints.
- **Hash** — rarely; B-tree is almost always better.

**Composite index column order**: equality-filter columns first, range last. `INDEX(user_id, status, created_at)` serves `WHERE user_id = ? AND status = ? ORDER BY created_at DESC LIMIT N`.

**Partial indexes** for selective subsets: `CREATE INDEX ... ON jobs (created_at) WHERE status = 'pending';` — tiny and fast for a queue worker's common query.

**Covering indexes** for index-only scans: `CREATE INDEX ... ON t (a, b) INCLUDE (c, d);`.

**Inspect with `EXPLAIN (ANALYZE, BUFFERS)`**. Red flags:
- `Seq Scan` on a large table with a selective `WHERE`.
- `Rows Removed by Filter: >> 0` — index exists but wrong shape; query plans to over-fetch then filter.
- Mismatched `estimated rows vs actual rows` — stale stats (`ANALYZE`), or correlated columns (consider extended statistics).
- `Bitmap Heap Scan` thrashing — tune `random_page_cost` (~1.1 on SSD).

**Monitor**: `pg_stat_user_indexes` (unused indexes — drop them, they cost writes), `pg_stat_statements` (slow queries), bloat views (`pgstattuple`). Indexes cost writes; drop what's unused.

## Transactions and isolation

- **Default is READ COMMITTED.** It's often not enough. Use `REPEATABLE READ` or `SERIALIZABLE` for correctness-sensitive work (money, counters, "unique-by-query").
- **SERIALIZABLE** (Postgres SSI) is correct and usually fast enough. Be ready to retry on `serialization_failure` (SQLSTATE 40001) — this is not an error, it's the contract.
- **Explicit locking**:
  - `SELECT ... FOR UPDATE` — read-then-write on a row.
  - `SELECT ... FOR UPDATE SKIP LOCKED` — queue-table workers.
  - `SELECT ... FOR SHARE` — ensure a row doesn't change while you're validating against it.
- **Never hold a transaction open across a network call to a third party.** That's how you exhaust connections. Commit first, then call; or call first, then transactional write.
- **Session-level timeouts** (set on the role or per-session):
  - `statement_timeout = '5s'` — kills runaways.
  - `idle_in_transaction_session_timeout = '30s'` — no zombie transactions holding locks.
  - `lock_timeout = '2s'` — don't block forever waiting for a lock.

## Writing queries

- One expressive query > N round-trips. Window functions, CTEs, `DISTINCT ON`, `LATERAL`.
- `INSERT ... ON CONFLICT (key) DO UPDATE / DO NOTHING` — upserts and idempotent writes.
- `RETURNING` to get what you wrote without a follow-up `SELECT`.
- Batch: `INSERT ... VALUES (...), (...), (...)` for bulk; `UNNEST($1::int[], $2::text[])` for large parameterized batches.
- **N+1 alarm**: any loop that calls the DB is a problem. Fold into `IN (...)` or a join.
- **Row estimates** — if the planner is wildly off, try `CREATE STATISTICS ON (col_a, col_b) FROM t;` for correlated columns.

## Migrations — expand / contract

Forward-only. Idempotent. Large tables migrate **online** using expand/contract (also called "parallel change"):

1. **Expand** — add the new shape without breaking the old:
   - New column is nullable, no default (defaulting an existing column rewrites the table on older PG; in PG 11+ non-volatile defaults are metadata-only, but still be careful).
   - `CREATE INDEX CONCURRENTLY` — non-blocking, but cannot run inside a transaction and must be watched (`REINDEX` if it fails partway).
2. **Backfill** — populate the new shape in batches:
   ```sql
   UPDATE t SET new_col = derive(old_col)
    WHERE id IN (SELECT id FROM t WHERE new_col IS NULL ORDER BY id LIMIT 1000 FOR UPDATE SKIP LOCKED);
   ```
   Chunked (1k–10k rows), resumable (`WHERE new_col IS NULL` — naturally resumes), rate-limited, monitored. A good backfill has a progress counter and a pause/resume switch.
3. **Dual-write** — app writes both old and new columns. Deploy this; bake for one release cycle.
4. **Contract** — once the new column is complete and the app reads from it everywhere:
   - Drop the old column in a separate migration, after the code that reads it is gone.
   - `ALTER TABLE ... SET NOT NULL` and add a `DEFAULT` in a separate step if needed.

**Destructive migrations** (`DROP COLUMN`, `DROP TABLE`) require this sequence: deploy code that stops reading/writing → wait → deploy the migration. **Never in one step.**

**Rename discipline** — don't rename columns in a live system. Add the new column, dual-write, migrate reads, drop the old.

## Backfills

- **Chunked and resumable.** Never a single `UPDATE t SET ...` on a large table — that's a long exclusive lock and a long transaction.
- **Monitor progress.** Write progress to a `migration_jobs` row, or log `processed=N, remaining=M` every chunk.
- **Throttle** if the DB is hot — sleep between chunks, watch replication lag, pause during peak.
- **Idempotent query** — `WHERE new_col IS NULL` or `WHERE migrated_at IS NULL` so a failed/restarted backfill just resumes.
- **Read your writes from the primary** during a backfill if you have read replicas.

## Connection pooling

- **PG connections are expensive** — each one is a real process. Don't open a new one per request.
- **App pool size = concurrent-request ceiling.** Small web app: 5–20. Large: measure. Too many connections = PG CPU dies on context switches.
- **PgBouncer** in front of PG for high-concurrency apps:
  - **Transaction pooling** — safe for stateless apps; incompatible with session-level features (prepared statements, `SET LOCAL`, advisory locks on session scope, `LISTEN/NOTIFY`). Use `pg_advisory_xact_lock`.
  - **Session pooling** — safe with all PG features, less multiplexing benefit.
- **Neon / serverless PG** pool on the driver side; the lazy-pool proxy in `src/lib/db.ts` handles the hot/cold path difference.
- **Prepared statements** are per-connection — on transaction-pooled connections they can leak or be useless. The `pg` driver caches; be deliberate.
- **Healthcheck connections** — separate tiny pool, or use `statement_timeout=1s` for them. A hung healthcheck shouldn't eat app capacity.

## Partitioning (when rows run into hundreds of millions)

- Declarative partitioning (PG 11+): by range (time-series) or by list (tenant).
- Partition pruning — the planner only touches relevant partitions when the query filters on the partition key.
- Indexes are per-partition. Global uniqueness must include the partition key.
- Retention is a partition detach + drop, not a long `DELETE`.

## Costing a query

Always ask: what does this query cost per call?
- Rows scanned (from `EXPLAIN ANALYZE`).
- Bytes in/out (cache warmth matters; `BUFFERS` tells you shared-hit vs read).
- Locks held and for how long (watch for `RowExclusiveLock` duration on hot rows).
- Frequency × cost = production cost. A 2ms query called 10k/s costs 20s/s of DB time.

If your endpoint's DB cost > the value of the endpoint, rethink.

## Multi-tenancy (if this becomes B2B)

- **Shared schema, `tenant_id` column everywhere** — simplest. Ownership in `WHERE`. Row-level security (RLS) for defense in depth.
- **Schema-per-tenant** — better isolation, harder migrations (N schemas), good for a few dozen tenants.
- **DB-per-tenant** — hardest isolation story; compliance/regulated workloads only.

Pick the simplest model that meets your isolation needs. Changing later is expensive.
