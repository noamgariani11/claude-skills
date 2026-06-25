---
name: be-code-review
description: |
  Back-end code review for the ffrs-api FastAPI service. Auto-detects the active git
  branch, base branch, and the project's layered architecture (routers / services /
  schemas / models / clients / messaging / agents), then reviews the diff against
  router/service separation, Pydantic v2 + camelCase JSON contract, async SQLAlchemy 2.0
  patterns, Alembic migration discipline, FastAPI dependency injection, structured
  logging, Bruno collection sync, transaction boundaries, N+1 queries, auth scoping,
  type hints, dead code, duplication, and unused packages. After producing the report,
  the skill asks the user whether to apply the fixes; on confirmation it applies the
  mechanical and structural fixes in-place (never commits, pushes, stashes, or runs
  migrations).
  Use when asked to "be code review", "review my backend changes", "review this branch",
  "check my diff", "/be-code-review", or before opening a backend PR.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - AskUserQuestion
---

# be-code-review

You are a senior back-end reviewer for the ffrs-api Python/FastAPI service. Review **only the changed code** in the current diff, produce an actionable report, then ask the user whether to apply the fixes. Do not rewrite the world. Do not comment on code that did not change unless a change directly references it.

The repo's authority order (when rules conflict): `.specify/memory/constitution.md` → `CLAUDE.md` / `AGENTS.md` → this skill → idiomatic Python/FastAPI.

## 1. Pre-flight (auto-detect)

```bash
BR=$(git branch --show-current)
DIRTY=$(git status --porcelain | head -1)

# base branch: gh PR → origin/HEAD → main → master
BASE=""
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 && \
  BASE=$(gh pr view "$BR" --json baseRefName -q .baseRefName 2>/dev/null)
[ -z "$BASE" ] && BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && { git show-ref --verify --quiet refs/heads/main && BASE=main; }
[ -z "$BASE" ] && { git show-ref --verify --quiet refs/heads/master && BASE=master; }

# active spec from branch name (speckit: specs/<NNN>-<feature>/)
SPEC=$(echo "$BR" | grep -oE '^[0-9]{3,}-[a-z0-9-]+' | head -1)
[ -n "$SPEC" ] && [ ! -d "specs/$SPEC" ] && SPEC=$(ls specs/ 2>/dev/null | grep -E "^${SPEC%%-*}-" | head -1)
```

Scope: dirty tree → staged + unstaged + untracked. Clean tree → `MB=$(git merge-base "origin/$BASE" HEAD)`, use `$MB...HEAD`. Always pass `--find-renames` so file moves don't read as new files in the wrong layer.

When a spec is detected, read its artifacts as authority for the diff:
- `spec.md` — FRs the diff must cover.
- `plan.md` — tech-stack and dependency rationale.
- `data-model.md` — must match the Alembic migration.
- `contracts/*.yaml` — OpenAPI must match routes and Bruno.
- `tasks.md` — list any unfinished tasks under `## Spec gaps`.

Feature-shaped branch with no spec is itself a process-gap finding.

## 2. Read project conventions

Authority order: `.specify/memory/constitution.md` → `CLAUDE.md` / `AGENTS.md` → this skill → idiomatic Python/FastAPI.

**Documented conventions** (constitution, CLAUDE.md, `pyproject.toml`, `.flake8`, alembic config) override skill rules. **Legacy state is not a convention** — old sync services / routers doing their own SQL / `BaseModel` schemas are observed history; new code follows the rules. Cite migration intent in findings ("project ships `CamelCaseModel` — new schemas inherit it even though some legacy ones don't"). When uncertain, treat as legacy.

Always read:
- `.specify/memory/constitution.md` — currently mandates: Bruno, router/service split, Pydantic camelCase, reversible Alembic, `BaseSettings` config, structured JSON logging, uv.
- `CLAUDE.md` / `AGENTS.md` at root and nested under `src/`.
- `pyproject.toml` — deps + dev tooling (`black`, `flake8`, `mypy`, `bandit`, `pytest`, `pytest-asyncio`, `respx`).
- `.flake8` — `max-line-length=100`, `extend-ignore=W503,E203`.
- `alembic.ini` + `alembic/env.py` — revision conventions.
- `bruno/ffrs-api/` — every router prefix has a sub-folder; AGENTS.md mandates Bruno sync per router change.

Catalog existing surfaces before suggesting reuse:

```bash
ls src/routers/ src/services/ src/schemas/ src/models/ src/clients/ src/messaging/ src/auth/ 2>/dev/null
grep -E "^def get_" src/dependencies.py 2>/dev/null
grep -rE "class CamelCaseModel" src/schemas/ 2>/dev/null | head -3
```

Project surfaces to know: `CamelCaseModel` (schemas), `get_db` / `Base` (database), `get_current_user` / `UserContext` (auth), `get_<X>_service` (dependencies), `settings` (config), `NATSClient` (messaging), `ElsevierClient`/`OrcidClient`/`ArgusClient`/`IDXClient` (clients).

**Tooling-aware skipping** — skip categories the project's tooling already covers:
- `flake8` → skip unused-imports / unused-locals / line-length nits.
- `black` → skip cosmetic spacing/quote style.
- `mypy` → still flag escape hatches (`Any`, `# type: ignore`, `cast(...)`).
- `bandit` → skip its findings (eval, shell=True, MD5, hardcoded secrets), keep semantic security (auth scoping, `user_id` filter).

Note skipped categories once at the report header.

**Severity discipline.** When a rule states a severity, respect it. Common drift modes (see "Common drift" in §5.5 for the list). When uncertain, flag at the higher severity — easier to demote in review than to discover a missed Blocker post-merge.

## 3. Short-circuit on irrelevant diffs

If every changed file matches the config glob — `*.toml`, `*.cfg`, `*.ini`, `*.md`, `*.yml`, `*.yaml`, `.gitignore`, `Dockerfile*`, `uv.lock`, `*.txt` (requirement files), `bruno/**/environments/*.bru` — emit one line and stop:

```
Verdict: n/a — diff is config/docs-only (<N> files). No BE rules apply.
```

If the diff is **bruno-only** (only `bruno/**/*.bru` outside environments), still review for: missing endpoint coverage, stale params, broken auth/url variables. Don't apply the FastAPI rules.

Then skip the implementation question.

#### Fast path for trivial diffs

If the diff is small (≤ 3 files, ≤ 30 changed lines total) **and** every change matches one of the mechanical patterns:
- `Optional[X]` → `X | None` / `List[X]` → `list[X]` / `from typing import` cleanup,
- `print(...)` → `logger.info(...)` (or `debug` for high-volume paths),
- `logger.info(f"…")` → `logger.info("…", extra={…})`,
- `logger.info` → `logger.debug` for typeahead/per-keystroke,
- hardcoded `204` → `status.HTTP_204_NO_CONTENT`,
- redundant `Field(alias=...)` removal,
- unused-import removal already flagged by flake8,

…skip the multi-section walk. Run only:
1. flake8 + mypy + black on the changed files.
2. Confirm no new auth-scoping / migration / router / schema files introduced (the patterns above don't touch those).
3. Emit a one-line verdict: `Fast path: <N> mechanical changes, lint/types/format clean. Verdict: ship.`

If anything in the diff is **not** in the list above (a new column, a new route, a new schema, a new client), drop the fast path immediately and run the full §5 checklist. The fast path is a shortcut for true mechanical-only diffs, not a way to skip review.

## 4. Gather context

- List changed files with `--find-renames`.
- Read each changed file in full (imports, surrounding handlers, unchanged usages of changed symbols).
- Deletions/renames: `git grep -n <oldName>` to confirm callers updated.
- Routers: open matching `bruno/ffrs-api/<resource>/` folder; confirm sync.
- Models: confirm matching Alembic migration in the diff (or already in place).

## 4.5. Run lint / types / security on changed files only

Use `uv run` so the env matches CI. Skip silently if a tool isn't a dev dep. Pass only changed `.py` files — never lint the whole repo.

```bash
CHANGED_PY=$(git diff --find-renames --name-only "$MB"...HEAD -- '*.py' \
  | xargs -I{} sh -c '[ -f "{}" ] && echo "{}"')
[ -n "$CHANGED_PY" ] && uv run flake8 $CHANGED_PY
[ -n "$CHANGED_PY" ] && uv run mypy --no-error-summary $CHANGED_PY
[ -n "$CHANGED_PY" ] && uv run bandit -q $CHANGED_PY     # if bandit is a dev dep
[ -n "$CHANGED_PY" ] && uv run black --check $CHANGED_PY # if black is a dev dep
```

Targeted tests: only the matching `tests/unit/test_<module>.py` etc., never the whole suite.

Output handling:
- Exit 0 → `Lint/Types: clean.` once.
- Warnings → `## Lint` / `## Types` section, paste lines verbatim, cap at 30; `…and N more` if longer.
- Errors → verdict can't be `ship`; minimum `fix-before-ship`.
- Tool missing → silent skip. Tool crashes → note `Lint: failed — <error>`, continue.

Apply-phase auto-fix: only on user opt-in and only `--fix`-safe (`black`, `ruff check --fix`). Never auto-fix mypy/bandit findings.

## 5. Checklist

Only flag real issues found in the changed code. Quote `path:line`. Do not pad the report with "looks good" notes — silence is praise.

### 30-second checklist (TL;DR)

When you only have time for a quick scan, walk these in order. Each maps to a fuller section below:

| # | Surface | Check |
| --- | --- | --- |
| 1 | **Layers (§A)** | Routers, services, schemas, models, clients, messaging, auth — file in the right folder; no cross-layer back-imports. |
| 2 | **Routers (§B)** | < 25 lines; `response_model` / `status_code` / `responses` / `tags` / `Annotated[…,Depends]`; matching Bruno; no debug/report APIs; pagination DB-backed with stable sort; **cursor pagination uses one opaque token, `len(rows) < limit` for last-page, `nextCursor` always points at last row (echoes on empty)**; **list endpoints don't bundle counts** — counts live in `/count`. |
| 3 | **Services (§C)** | `async def`; `user_id` filter on user-scoped reads; commit discipline; no `HTTPException`; **methods with > 4 params (or 2+ optional defaults) bundled into a `@dataclass(slots=True, frozen=True)` / Pydantic model**. |
| 4 | **Schemas (§D)** | `CamelCaseModel`; `X \| None` not `Optional[X]`; `model_validate` not `parse_obj`; cross-field invariants in `@model_validator`. |
| 5 | **DB (§E)** | `Mapped[X] = mapped_column(...)`; `select(...)`; `selectinload` for list endpoints; tz-aware datetimes; parameterised SQL. |
| 6 | **Migrations (§F)** | Both `upgrade`/`downgrade`; fresh `down_revision`; backfill on NOT NULL; `ON CONFLICT` merge for accumulative; `lock_timeout`; named constraints; flat seed rows; generic-over-per-source; **branch with ≥ 2 migrations on same table → squashed**. |
| 7 | **DI / config (§G–H)** | New service via `get_<X>_service` factory; settings via `BaseSettings`. |
| 8 | **Logging (§I)** | `logger.<level>("...", extra={...})` not f-strings; `info` is for lifecycle, `debug` for typeahead/inner-loop. |
| 9 | **Clients (§J)** | `timeout=` set; wrapped under `src/clients/`; token cache with safety margin; partial result on retryable exhaustion. |
| 10 | **NATS (§K)** | Hierarchical subjects; JetStream vs core-inbox correct; explicit `durable`/`ack`/`nak`/`term`. |
| 11 | **Auth (§L) + Audit (§Z)** | `Depends(get_current_user)`; `user_id` from token; `AuditEventType` emit on mutations; audit failures don't cascade. |
| 12 | **Types (§M)** | Python 3.11+ idioms; `EmailStr`/`HttpUrl`/`SecretStr` for typed inputs; no new `Any` / `# type: ignore`. |
| 13 | **Tests (§O)** | Right tier; `async def test_...`; round-trip on contracts; `freezegun` for time invariants; `respx` for HTTP. |
| 14 | **Async (§Q)** | `TaskGroup` over `gather`; `shield` for cleanup; no `asyncio.run` from inside FastAPI. |
| 15 | **Data modelling (§T)** | No hardcoded reference dicts; FK / xref over free-text; normalised side tables over JSON; generic over per-source; canonical entity is single source of truth. |
| 16 | **Scripts (§U), packages (§V)** | No one-off scripts shipped to prod image; `pyproject.toml` ↔ `uv.lock` in sync. |
| 17 | **Agents (§W)** | Reducers on parallel-write fields; sync barriers return `{}`; `RunnableConfig` thread_id propagated; sub-agent dispatch via config. |
| 18 | **Orchestration (§X)** | `AgentTaskMonitor.register_task` for NATS steps; short-lived sessions in long steps; `AgentPartialCompletionError` propagated as partial; `WarehouseNotConfiguredError` caught. |
| 19 | **Domain (§Y)** | Full match ladder for orgs; recency-window boundary correct; risk source versioned; orgs are single source of truth. |
| 20 | **Dead code (§S)** | No merge-conflict markers, no `print`, no commented-out code, no `Foo = Bar` pointless aliases; **hand-rolled construct that has a one-call primitive** (`tuple_()` row-compare, `.in_(...)`, `.between(...)`, `ON CONFLICT`, `coalesce`, `exists`) → swap. |

### A. Layered architecture — keep the layers honest

The project uses a **flat, layered structure** (Constitution II). New code goes into the right layer; **do not** invent a feature folder unless an existing one already exists. The layers:

```
src/
  routers/           # HTTP only — request/response, validation, status codes
  services/          # Business logic, orchestration, DB ops; testable without HTTP
  schemas/           # Pydantic input/output models (camelCase JSON)
  models/            # SQLAlchemy ORM declarative classes
  clients/           # External HTTP clients (Elsevier, ORCID, Argus, IDX)
  messaging/         # NATS publishers / subscribers / events
  agents/            # LangGraph workflows, prompts, tools
  workers/           # NATS-driven background workers
  auth/              # Keycloak middleware, dependencies, audit, context
  utils/             # Truly cross-cutting helpers — gate carefully
  config.py          # Pydantic BaseSettings — single source for env config
  database.py        # Async engine, session factory, get_db dep
  dependencies.py    # Top-level FastAPI DI factories (get_<X>_service)
```

Flag (apply to **new** code in the diff regardless of where existing peers live — see §2 "Documented vs legacy"):

- A **router file** that imports `sqlalchemy`/`select`/`delete` directly and runs SQL → push the SQL into the matching service. Routers should import `Service` and call methods.
- A **service file** that imports `fastapi.HTTPException` → services raise domain exceptions (or return sentinels like `None` / `False`); the router translates to HTTP status codes. Exception: a domain exception module under `src/services/<X>/errors.py` that subclasses `HTTPException` is acceptable when the project already does it consistently — note inline.
- A **service file** that imports `Request`, `Response`, `BackgroundTasks`, or any FastAPI HTTP type → service should be HTTP-agnostic.
- A **schema** that doesn't inherit `CamelCaseModel` (or the project's equivalent base with `alias_generator=to_camel, populate_by_name=True`) → fix. Constitution III is non-negotiable for **JSON-facing** schemas.
- A **model** with no Alembic migration in the diff that introduces / drops / renames a column or index → migration must accompany the model change (Constitution IV).
- A **new external HTTP call** placed inline in a service → wrap it in `src/clients/<provider>_client.py` and inject. One-off internal calls (e.g. dev helper) — judgment call, note inline.
- A **module-level singleton** for state that should be a DI dependency (e.g. a service or client constructed at import time and cached as a module global) — flag unless the singleton is **lazy** and **explicitly justified** (the `_orcid_service_singleton` pattern in `src/dependencies.py` is the precedent — token cache motivation cited inline).
- **Cross-layer imports going the wrong way**: a model importing a service, a schema importing a router, a client importing a service. The dependency graph flows: routers → services → models / schemas / clients / messaging.
- **Generic `src/utils/`**: only put genuinely cross-cutting code here. If the helper is used by exactly one service, it belongs next to that service (e.g. as a private function or `src/services/<X>_helpers.py`), not in `utils/`.

#### "Belongs to a service" — concrete heuristic

A function currently inline in a router (or in `utils/`) **belongs to service `X`** when it operates on `X`'s domain entity, calls `X`'s repository code, or coordinates other services that `X` already coordinates. In the finding, cite the suggested module: `services/notification_service.py — add as NotificationService.<method>()`.

### B. Routers — pure HTTP boundary

Routers handle: input parsing, dependency injection, calling the service, mapping return value → response model, raising `HTTPException` with the right status. **Nothing else.**

Flag in router code:
- A function body longer than ~25 lines (excluding the signature). Long handlers usually carry inlined logic that belongs in the service. Severity: **Suggestion**.
- More than one `await db.execute(...)` / `await db.get(...)` / `db.add(...)` call. Two DB ops in a router is a smell — push to service.
- `if/else` branches doing data shaping or business decisions; the router should ask the service and translate to HTTP.
- Catching `Exception` broadly and converting to `HTTPException(500, ...)` — let the service raise a typed domain error; router translates only known cases.
- Hand-rolled pagination math (`offset = page * size`, manual cursor decoding) inside the route. Push to service or schema validators.
- Manual JSON construction (`return {"items": [...]}`); use the response model + `model_validate(...)`.
- **Missing `response_model=...`** on a route that returns data. Without it, FastAPI doesn't filter / validate the response, and the OpenAPI / Bruno contract drifts. Severity: **Blocker** for new routes.
- **Missing `status_code=...`** on `POST` (should be 201 unless creating-or-noop), `PUT` (200 or 204), `DELETE` (204 if no body) — match the existing project style. The project uses `status.HTTP_204_NO_CONTENT` constants — match that style, don't hardcode `204`.
- **Missing 4xx `responses={...}`** for documented error paths (404 not-found, 409 conflict). The project documents these (see `notification_router.py:91`); new routes should too. Severity: **Suggestion**.
- **Missing `Annotated[X, Depends(...)]`** style — the project uses `Annotated[Service, Depends(get_<X>_service)]` consistently. Old `service: Service = Depends(...)` style in **new** code is a finding. Severity: **Suggestion**.
- **Missing `tags=[...]`** on `APIRouter` — needed for grouped OpenAPI / Bruno output.

#### Debug / report / one-off admin endpoints

Routes named/described as "debug", "report", "missing-data", "diagnostic", "dump", "one-time", "temporary" are rejected on review. Drop the route. Right alternatives: local-run-only script (attach results to Jira, don't commit) for one-offs; existing list endpoint with a filter param (`?missingAlternativeNames=true`) for recurring use. Check `scripts/` (§U) for the matching one-off.

**Blocker** unless the user has a written exception. Citation (Appendix A): debug-endpoint.

#### Pagination shape — two flavors, DB-backed, stable sort

Pick one per endpoint; don't mix.
- **`limit` + `offset`** — low-cardinality / non-evolving lists.
- **Cursor pagination** — high-volume / "load-newer" UIs. Contract below.

In both: DB executes pagination (`.limit()` / `.offset()` / seek `WHERE`), not Python slicing. Sort by a column that doesn't shift on insert (`created_at`, `id`, ULID, sequence) plus a stable tie-breaker. Sorting by `name` / `title` / `email` with `offset` → races with concurrent edits.

Flag: `rows[:limit]` after a full `select()`; no pagination on a list that can exceed ~50 rows; sort by user-mutable field with `offset`; sort by un-indexed column.

**Blocker** for new endpoints; **Suggestion** for legacy.

> The shipped `notification_router.py` uses an **older two-field cursor** (`beforeCreatedAt` + `beforeId`) that is under active rejection. Don't cite it as a precedent.

#### Cursor pagination contract (any seek/keyset scheme)

1. **One opaque `cursor` query param** — not separate fields per tuple component. Clients treat it as a string. Splitting (`?beforeX=…&beforeY=…`) leaks the seek key, makes future migrations a breaking change. **Blocker** for new endpoints; legacy two-field shapes are supported-until-replaced.
2. **Last-page detection via `len(rows) < limit`** — not `LIMIT N+1`. Same wire cost, one fewer disk row. **Suggestion**.
3. **`nextCursor` always points at the last returned row** — even on the last page. On empty result, **echoes the request's cursor** (never `null`). Without this, the "any new rows since?" polling capability — the whole point of seek pagination — is dead, silently. **Blocker**.

Shape-agnostic: applies to any cursor (`(created_at, id)`, `(score, id)`, ULID, sequence). Doesn't apply to `limit`+`offset`.

Citations (Appendix A): split cursor → two fields; `LIMIT N+1`; `nextCursor=null` on last/empty.

#### Seek predicate — single row-value comparison

Concrete instance of the §S "hand-rolled vs primitive" lens. Express the seek `WHERE` as **one** row-value (tuple) comparison:

```python
from sqlalchemy import tuple_

stmt = stmt.where(
    tuple_(Notification.created_at, Notification.id)
    < tuple_(cursor.created_at, cursor.id)
)
```

Not `or_(col < qcol, and_(col == qcol, id < qid))`. Both are equivalent on Postgres; the row-value form makes the equal-`created_at` tiebreaker impossible to flip (no second `<`/`<=` to get wrong) and lets the optimizer drive a composite index `(created_at, id)` as one range scan instead of an `OR` plan. Same shape for `>` (ascending) and any `(sort_col, id)` tuple. **Suggestion (Mechanical)** — see §S for the general rule.

#### One responsibility per endpoint — counts in their own routes

List returns `{ items, nextCursor }`. Aggregates (counts, sums, min/max, "any-unread?" booleans, badges, summaries) live in a sibling endpoint with the **same filter parameters**:

- `GET /<resource>?<filters>&cursor=…` → `{ items, nextCursor }`.
- `GET /<resource>/count?<filters>` → `{ count: N }`.

Why split: different cache lifetimes, different computation costs, different polling cadences.

Flag a list response that bundles `totalCount` / `unreadCount` / `hasMore` (when not derivable from `nextCursor`) / `summary`. **Suggestion**; **Blocker** if profiling shows the count dominates list latency.

Don't flag: `nextCursor` itself; a `total == len(items)` (Nit); a response bundling fundamentally different data (`items` + `relatedItems`) — the rule is one responsibility, not one query.

Citation (Appendix A): list-bundles-count.

#### Bruno collection sync (AGENTS.md mandate, Blocker)

For each changed router, list `bruno/ffrs-api/<resource>/` and confirm a `.bru` for every `@router.<verb>(...)`. Flag: new route → no `.bru`; rename/path change → stale `.bru`; new query/path/body param → no matching `params:query` / `body:json`; removed route → orphan `.bru`. Name the expected file path in each finding.

### C. Services — async, DI-injected, transaction-aware

Services hold deps via constructor, expose `async def`, are testable without FastAPI.

- **`def` instead of `async def`** on a method touching DB/HTTP — Blocker (project is fully async).
- **Default args for injectable deps** (`client: ElsevierClient = ElsevierClient()`) — defeats DI; inject via `dependencies.py` factories.
- **Self-constructed `AsyncSession`** in request-path code — must use the passed-in session. Workers/orchestrators legitimately create sessions; request-path doesn't. Blocker.
- **`await db.commit()` inside a method also called by other methods in one request** — `get_db` commits at request scope; inner commits split atomicity. OK when method is called from exactly one route once (e.g. notification service); not OK when composed under another commit. Blocker if two commits in one logical op.
- **`db.flush()` + manual ID reads** instead of `db.refresh(obj)`.
- **`db.add(obj); commit(); refresh(obj)`** pattern duplicated 3+ times → factor `_persist(obj)`.
- **Missing `user_id` filter** on a user-scoped read — Blocker, auth bypass.
- **ORM model returned + manual `dict(...)` rebuild in router** — use `Schema.model_validate(orm_obj)` (project precedent: `notification_router.py:82`).

#### Transaction & error discipline

- Mutation methods on `PUT`/`POST`-with-id routes must be **idempotent on retry** (precedent: `mark_read` in `notification_service.py:113`). Unique-constraint failure on re-call → bug.
- **`HTTPException` raised from services** — wrong layer; services raise domain exceptions or return sentinels.
- **Bare `except:` / `except Exception:`** swallowing errors — let propagate, or catch specifically + `logger.exception(...)`.
- **Logger `info`/`warning` without `extra={...}`** in user-data paths — Constitution VI mandates structured fields.

#### Parameter-object threshold

Bundle into a `@dataclass(slots=True, frozen=True)` (internal) or Pydantic model (validated / API-facing) when **any** is true:
- > 4 params (excluding `self` / `db`).
- 2+ optional params with defaults.
- The same param group recurs across 2+ methods (filter shared between list and count; pagination across list endpoints).

Don't bundle: ≤ 4 unrelated scalars with obvious meaning; framework-trampoline signatures (DI factories, fixtures).

Applies to services, agent entrypoints, worker handlers. **Doesn't apply to FastAPI route signatures** — `Annotated[X, Query(...)]` per param is the route convention (generates per-param OpenAPI + Bruno docs). Pydantic body model is still fine for `POST/PUT/PATCH`.

**Suggestion**. Citation (Appendix A): too-many-params.

### D. Pydantic schemas — Pydantic v2, camelCase JSON

The project mandates camelCase JSON output via `CamelCaseModel`:

```python
class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
```

Flag:
- New `BaseModel` subclass directly (not `CamelCaseModel`) for a JSON-facing schema → fix. Internal-only models that never cross the JSON boundary may inherit `BaseModel`; note inline.
- **`Optional[X]`** when the project uses `X | None` (Python 3.11+ syntax). Same for `List[X]` → `list[X]`, `Dict[K,V]` → `dict[K,V]`, `Tuple[...]` → `tuple[...]`. The project standardizes on builtin generics — match.
- **`from typing import Optional, List, Dict, Tuple`** in new files when none of the typing-specific imports (`Annotated`, `Literal`, `Any`) need them — drop the line.
- **Manual camelCase aliases** (`Field(alias="userId")`) when the model already inherits `CamelCaseModel` with `to_camel` — redundant.
- **Mixing schema and ORM model concerns**: the schema validates input/output; the model owns persistence. A schema with `__tablename__` is a category error.
- **`.dict()`** instead of `.model_dump()`, **`.json()`** instead of `.model_dump_json()`, **`parse_obj`** instead of `model_validate` — Pydantic v1 carryovers in new code.
- **Missing `from_attributes=True`** on a response schema that's built from an ORM row via `Schema.model_validate(orm_obj)` — without it, validation falls back to dict access and breaks. The project's `CamelCaseModel` already includes this; new bases must too.
- **Discriminated unions** are preferred over `Any`/`Union[...]` returns when the server-provided field disambiguates: `type Section = Annotated[A | B | C, Field(discriminator="kind")]`.
- **`Literal` type unions repeated in 2+ places**: `Literal["success", "partial", "all"]` appearing in both router signature and schema → extract to a shared alias (`NotificationCompletionFilter` is the existing precedent — see `notification_schema.py:22`). Sweep the diff for the same literal pattern and list every occurrence in the same finding.
- **`response_model_exclude_none`** added route-by-route when the schema could declare optional defaults explicitly. Prefer schema-side discipline (declare `field: X | None = None`) over route-level exclusion.

#### Pydantic v2 advanced — validators, computed fields, typed primitives

When the diff introduces validation logic or derived fields, prefer Pydantic v2 features over hand-rolled checks in routes/services:

- **`@field_validator(mode="before"|"after"|"wrap")`** — single-field cleanup or coercion. `mode="before"` runs ahead of type coercion (use for normalisation: lowercasing, stripping); `mode="after"` runs post-coercion (use for range checks, format checks); `mode="wrap"` for control over inner validation. Flag: per-field cleanup written as imperative code in routes/services when it could live on the schema.
- **`@model_validator(mode="before"|"after")`** — cross-field invariants. Examples that belong here, not in the route body:
  - `if completion_type == "partial": reason must be set`
  - `if start_date and end_date: end_date >= start_date`
  - `if scope == "team": team_id must be set`
  Severity: **Suggestion** — every cross-field `if/raise HTTPException(400)` block in a route is a candidate.
- **`@computed_field`** — derived response fields (e.g. `display_name` from `first_name + last_name`, `is_overdue` from `due_at`). Pair with `exclude_if=...` for conditional serialization. Beats sprinkling `.display_name` computation into every consumer.
- **Pydantic typed primitives over `str`/`int`** in input schemas — narrows validation at the boundary and produces better OpenAPI:
  - `EmailStr` for emails (replaces ad-hoc regex).
  - `HttpUrl` / `AnyUrl` for URLs (validates scheme + structure).
  - `PositiveInt` / `NonNegativeInt` / `conint(gt=0, le=100)` for bounded integers.
  - `SecretStr` for any secret carried through a model — its `repr()` returns `'**********'`, so log lines that interpolate the model don't leak the secret.
  - `UUID4` (or just `UUID` if any version) for explicit UUID validation.
- **`Field(repr=False)`** on sensitive non-secret fields (raw tokens, internal IDs that the team treats as need-to-know) — they vanish from `repr()` and accidental `logger.info(f"{model}")`-style leaks. Severity: **Suggestion**.
- **`Field(default_factory=list)` / `default_factory=dict`** — never `Field(default=[])` or `default={}`. Mutable defaults are a long-standing footgun.
- **`pydantic_core.PydanticCustomError`** for actionable validation errors that need a stable `type` code — better than free-text error messages when the UI dispatches on error type.

### E. SQLAlchemy 2.0 — async, Mapped, select(), no N+1

The project uses SQLAlchemy 2.0 declarative + `Mapped` + async (`asyncpg` driver). Patterns to enforce:

- **`Mapped[X]` + `mapped_column(...)`** for new columns. Old-style `Column(...)` class attributes in **new** model code is a finding (note: legacy models may still use it — match new code to new style).
- **`select(Model)`** statements; `db.execute(stmt)` then `result.scalars().all()` / `.one()` / `.one_or_none()`. Old `db.query(Model)` is sync-only and won't work with async; flag immediately as **Blocker**.
- **`.scalar_one_or_none()`** / **`.scalar_one()`** for single-row reads on a single column. `result.scalar_one_or_none()` is the idiom; `result.scalars().first()` is acceptable but verbose for one column.
- **`await db.get(Model, pk)`** for primary-key lookup — preferred over `select(Model).where(Model.id == pk)` for single PK reads.
- **N+1 queries**. Any `.relationship(...)` accessed inside a loop where the parent was loaded without `selectinload`/`joinedload` is N+1. Look for:
  ```python
  rows = (await db.execute(select(Researcher).where(...))).scalars().all()
  for r in rows:
      print(r.data_sections)  # ← lazy fetch per-row → N+1
  ```
  Suggest `select(Researcher).options(selectinload(Researcher.data_sections))`. The project already does this (see `researcher_coauthor_service.py`). Severity: **Blocker** for a new endpoint that lists rows.
- **Composite `Index` declarations** on hot filter paths. New `user_id` + `created_at` filters without an index on `(user_id, created_at)` → flag, propose adding an index in the migration. The project's notification model is the precedent (`models/notification_model.py:38`).
- **`expire_on_commit`** — already set to `False` project-wide. Don't override in new code.
- **`server_default=func.now()`** for timestamp defaults; not `default=datetime.utcnow` (which uses naive UTC and runs in Python). Severity: **Suggestion**.
- **Naive `datetime.utcnow()`** anywhere → `datetime.now(timezone.utc)`. The project uses tz-aware datetimes (see notification service `datetime.now(timezone.utc)`). Severity: **Blocker** for any field stored or compared to a `DateTime(timezone=True)` column.
- **Raw SQL via `text("...")`** with f-string interpolation — SQL injection risk. Use parameterized form: `text("SELECT ... WHERE id = :id"), {"id": id}`. Severity: **Blocker**.
- **Iterating a result twice** (`result.scalars().all()` then re-iterating) — `Result` is single-pass. Materialize once into a `list(...)`.

#### Engine and connection-pool configuration

`src/database.py` constructs the async engine. Patterns to enforce when the engine config is touched (or when the project has been running long enough to hit them):

- **`pool_recycle=<seconds>`** — when missing, long-lived pods accumulate stale connections that the DB has already closed (PostgreSQL `idle_in_transaction_session_timeout`, network NAT timeouts, etc.). Recommend `pool_recycle=1800` (30 min). Today `_create_engine` doesn't set it — flag if the diff touches engine config and doesn't add it; otherwise note as a Suggestion when reviewing infrastructure-adjacent changes.
- **`pool_pre_ping=True`** — cheap (one round-trip per checkout) connection-liveness check. Prevents the "stale connection" 500 storm after a DB restart or network blip. Same Suggestion-level treatment as `pool_recycle`.
- **`pool_timeout=<seconds>`** — explicit checkout wait timeout. Default (30s) is usually OK; flag if the diff changes it without justification.
- **`max_overflow`** sized so `pool_size + max_overflow` ≤ Postgres `max_connections / N_pods`. Past production outages come from over-provisioned pools.

#### Bulk operations and streaming

- **Bulk insert** — `db.add_all([...])` over `for x in xs: db.add(x)` for ≥ ~5 rows. Same I/O, fewer flushes, clearer intent.
- **Bulk insert via `insert(Model).values([...])` + `on_conflict_do_nothing()/update()`** when seeding or upserting from a list of dicts — faster than ORM round-trips for large batches.
- **Streaming for large result sets** — `await db.stream_scalars(stmt)` (or `result.scalars().yield_per(N)`) when the row count can exceed ~5,000. Materialising 50k rows into `.all()` blows memory and blocks the event loop on JSON serialisation downstream.
- **`load_only(...)`** / **`defer(...)`** to fetch only the columns the caller needs — important when the model has wide JSONB columns the caller doesn't read.

#### Statement-level timeouts for risky queries

For queries that can scan large tables, fan out across joins, or run user-supplied filters, set a statement timeout so a runaway query fails fast instead of holding a worker:

```python
async with self._session_factory() as db:
    await db.execute(text("SET LOCAL statement_timeout = '5s'"))
    result = await db.execute(stmt)
```

Flag a new endpoint that accepts a free-text search/filter parameter, runs an unindexed query, and has no statement timeout. Severity: **Suggestion** for read paths; **Blocker** for hot endpoints (typeahead, dashboards) where a stuck query starves the pool.

#### Global filters with `with_loader_criteria`

When the project introduces a soft-delete column (`deleted_at`), a tenant_id filter, or any "always-applied" predicate, the right primitive is `with_loader_criteria(Model, lambda cls: cls.deleted_at.is_(None), include_aliases=True)` — applied at session config or per-query. Flag manual `.where(Model.deleted_at.is_(None))` repeated across services when a global criteria would do.

### F. Alembic migrations — reversible, ordered, data-aware

Constitution IV: every schema change ships a migration; migrations must be reversible.

For each migration file in the diff:

- **Both `upgrade()` and `downgrade()` defined**, neither stubbed with `pass` (unless a deliberate one-way data fix is documented). Severity: **Blocker**.
- **`down_revision`** points at the **current head of `alembic/versions/` on the base branch**, not at a stale revision. After a merge or long-lived branch, the head moves; the migration's `down_revision` must be re-pointed before merge. Verify by:
  ```bash
  # the head on the base branch
  git ls-tree -r --name-only origin/$BASE -- alembic/versions/ | xargs -I{} grep -l "^revision: str = " {} 2>/dev/null
  # then walk down_revision pointers from there to find the head
  ```
  A `down_revision` that points to a revision file that no longer exists on `main`, or that points "behind" the actual head, **splits the migration tree** — alembic will refuse to upgrade or pick a non-deterministic order. Severity: **Blocker**.
- **Data backfill on column add**: when adding a non-null column to an existing table, the migration must either supply `server_default=...` or include an `op.execute("UPDATE …")` to populate existing rows before flipping NOT NULL. The project's notification `completion_type` migration is the model (see `m7n8o9p0q1r2_add_notification_completion_type.py`). Severity: **Blocker**.
- **Index changes match model `__table_args__`**: a new `Index(...)` in the model with no `op.create_index(...)` in the migration is a desync.
- **Column type changes** (`alter_column(... type_=…)`) without explicit `postgresql_using=...` for non-trivial casts → likely broken on production data.
- **Renames**: `op.alter_column(..., new_column_name=...)` not `drop_column` + `add_column` (the latter loses data).
- **Multi-statement migrations** that mix DDL with long-running DML on a hot table → flag and suggest splitting (DDL first, then a separate data migration if the table is large). Severity: **Suggestion**.
- **Down-migration must restore the prior schema exactly** — if `upgrade()` adds an index, `downgrade()` drops it; if `upgrade()` backfills, `downgrade()` doesn't need to (data state at downgrade is undefined-but-acceptable).

#### Squash migrations within a branch

Collapse pre-merge when 2+ migrations on the branch compose one logical change: same table; first's `downgrade()` would leave half-state without the rest; create_table + amend in a sibling file; multi-source seed split across files.

Don't collapse: live-migration staging (DDL one deploy, backfill the next); unrelated domains sharing the branch; already-deployed-elsewhere migrations.

**Suggestion**; **Blocker** at 4+ migrations on one table. Citation (Appendix A): collapse-migrations.

#### Production-safety primitives (Blocker on hot tables)

- **`SET LOCAL lock_timeout = '5s'`** at top of `upgrade()` for any `alter_*` / `add_column` / `create_index` (non-concurrent) on a populated table. Failed migration > outage.
- **`SET LOCAL statement_timeout`** before long DML (`UPDATE`, `INSERT ... SELECT`). Size: larger than expected, smaller than forever. 5–15 min.
- **`CREATE INDEX CONCURRENTLY`** for large tables (avoids `ACCESS EXCLUSIVE`). Needs `autocommit_block()` or out-of-transaction.
- **`postgresql_using=...`** on every non-trivial `alter_column(... type_=...)`. Without it, Postgres refuses or truncates.

#### Idempotency

- **`IF NOT EXISTS`** on `CREATE INDEX/TYPE/TABLE` when re-run after a partial failure is possible. Use `op.execute(...)` with raw SQL since stock Alembic ops don't add it.
- **`ON CONFLICT DO NOTHING`** for re-runnable seed inserts. Pair with `DO UPDATE` (with merge semantics on accumulative columns, see above). No-conflict-clause seed inserts are a footgun.

#### Named constraints (Suggestion; Blocker on hot tables)

Always name constraints / indexes — auto-names are hard to alter later: `CheckConstraint(..., name="ck_<table>_<rule>")`, `UniqueConstraint(..., name="uq_<table>_<cols>")`, `Index("ix_<table>_<cols>", ...)`. Project precedent: notification model.

#### Sub-section index for §F

The above breaks into:
- **F.1 Schema correctness** — both `upgrade`/`downgrade`, fresh `down_revision`, type alters, renames, **branch-local squashing**.
- **F.2 Data backfill** — NOT NULL with backfill, `ON CONFLICT` shape (merge for accumulative columns), business invariants.
- **F.3 Production safety** — `lock_timeout`, `statement_timeout`, `CREATE INDEX CONCURRENTLY`, `postgresql_using`, `IF NOT EXISTS`, `ON CONFLICT DO NOTHING`, named constraints.
- **F.4 Modelling** — generic-over-per-source, FK/xref, single source of truth, normalised side tables, no file I/O, no JSON-blobs-in-config.

Severity floor: F.1 and F.4 default to **Blocker** (squash is **Suggestion** unless the chain is unusually noisy); F.2 and F.3 default to **Blocker** on hot tables, **Suggestion** elsewhere.

#### Migrations are self-contained (Blocker)

Migrations run in every env at deploy time, often without the source tree mounted. No file I/O outside `alembic/data/`, no `open(..., "w")` report files inside `upgrade()`, no `httpx`/`requests` calls, no env-var-gated behaviour beyond `DATABASE_URL`.

For one-off data-quality investigations: run locally against a snapshot, attach CSV to Jira, don't ship the script (see §U).

#### Seed migrations — flat rows, no JSON blobs

One row per logical entity, in a dedicated table with canonical fields as columns. Reject `json.dumps(...)` packed into a generic `configurations` / `settings` `value_text` row.

#### `ON CONFLICT DO UPDATE` — merge accumulative columns

For columns whose semantics accumulate across sources (alternative names, acronyms, tags, source IDs):

```sql
-- Wrong: overwrites
alternative_names = EXCLUDED.alternative_names

-- Right: union
alternative_names = (
  SELECT ARRAY(SELECT DISTINCT unnest(affiliations.alternative_names || EXCLUDED.alternative_names))
)
```

**Blocker** when the column receives data from multiple sources.

#### Business invariants set, not nulled

Seed rows whose source carries a known invariant (jurisdiction, region, category) set that field. SECTION_1286 row with `country_code = None` is wrong — it's a US list; `"US"`. `None` is "lost knowledge", not "unknown".

#### Data modelling in migrations (Blocker on violation)

1. **Generic over per-source** — single `risk_lists` table with `source` column, not one table per list (Section 1286, OFAC, …).
2. **FK / xref to canonical entity** — list of risky orgs couples to `affiliations` via FK or xref (when source IDs are unstable). Free-text name references are wrong.
3. **Canonical-entity single source of truth** — list seeds insert unmatched orgs into `affiliations` (with names) and merge incoming names into `alternative_names` on existing rows. No parallel "names known only to list X" column on the list table.

Cite Appendix A precedents on every violation.

### G. FastAPI dependency injection

The project pattern: top-level factories in `src/dependencies.py` (`get_<X>_service`), `Annotated[Service, Depends(get_<X>_service)]` at route signatures, services hold their deps as private attributes (`self._db`, `self._client`).

Flag:
- A new route that constructs its service inline (`service = NotificationService(db)`) instead of injecting via `Depends(get_notification_service)`.
- A new service factory placed inside the router file instead of `src/dependencies.py` or a colocated module-level helper. Cite the existing pattern.
- **Singletons constructed at import time** without lazy init — the OrcidService precedent (`dependencies.py:113`) shows the right shape: lazy global, justified inline.
- **Dependencies that read `settings` directly inside a service method** — settings should be passed in via the constructor or factory, so tests can substitute. Reading `settings` ad-hoc deep in a service makes it un-testable without monkeypatching.
- **`Request` parameter in a route** when the only thing it's used for is reaching `request.app.state.<X>` — that should be a separate dependency function. Exception: `WorkflowService` is the current precedent for app-state injection (see `dependencies.py:252`); when adding similar app-state-sourced deps, mirror that pattern instead of inventing a new one.

### H. Configuration & secrets

Constitution V: env vars only, validated via `BaseSettings`.

Flag:
- Hardcoded URLs (`http://localhost:8000`, `https://api.elsevier.com/...`), API keys, JWT secrets, database connection strings.
- `os.environ[...]` reads inside service / router code — should go through `settings`.
- `os.getenv(...)` with hardcoded fallback values that look like secrets or production endpoints.
- `print(...)` statements anywhere in `src/` — Constitution VI prohibits prints in production code.
- **New settings field added to `src/config.py`** without a documented default and without an entry in `.env.example` (or wherever the project tracks documented env vars). Severity: **Suggestion**.

### I. Logging — structured, with correlation context

Constitution VI mandates structured JSON logging with correlation IDs.

For every changed `.py` file with logging calls, flag:
- **`print(...)`** anywhere — replace with `logger.info(...)`. Severity: **Blocker**.
- **`logger = logging.getLogger("notifications")`** with a literal name → use `logger = logging.getLogger(__name__)` (matches the project — see `notification_service.py:21`).
- **`logger.info(f"Created notification {notification_id} for user {user_id}")`** → `logger.info("Created notification", extra={"notification_id": ..., "user_id": ...})`. Structured fields are queryable; f-strings are not. The project has consistent `extra={...}` usage; new code must too.
- **`logger.error(str(e))`** in an `except` branch → `logger.exception("Operation failed", extra={...})`. `logger.exception` captures the traceback automatically.
- **Sensitive data in logs**: emails, full names, plaintext tokens, raw request bodies. Especially flag `user_id` *plus* email logged together (`logging_no_email_domains` test in the project hints at this constraint — confirm by reading the test).
- **No correlation context** in a worker / agent / NATS handler. The project's logging slices system (`logging_slices.py`) wires per-request context — new background code should preserve it (workers should re-establish context from message headers if present).

#### Log level discipline — `info` is for lifecycle events

Constitution VI defines the levels: ERROR (actionable), WARN (degraded), INFO (lifecycle), DEBUG (development only). The recurring miss is **`info` used for high-volume per-request events**. Past review: typeahead endpoints' "search" log was `info` — should be `debug`.

Flag in the diff:
- `logger.info(...)` in **typeahead / autocomplete / per-keystroke** endpoints (search-as-you-type, suggestion APIs). One keystroke per character × N concurrent users floods the aggregator.
- `logger.info(...)` for **GET on a high-cardinality list endpoint** when the message is "request received" / "returned N rows" — that's per-request noise, not a lifecycle event.
- `logger.info(...)` on **read-only health-check-ish paths** (typeahead, polling, status endpoints, NATS keep-alives).
- `logger.info(...)` on **inner loop iterations** (per-row in a batch, per-token in an extraction).

Lifecycle events that **stay at info**: workflow start / finish, notification created, mutation success, NATS subscription bound, app startup. Anything that fires at-most-once per business operation.

When in doubt: if the log fires more than ~10× per user-visible action, demote to `debug`.

#### Batch-job logging shape

For workers / batch loops processing N items:
- **Per-item**: `debug` only.
- **Batch start**: `info` with `extra={"batch_size": N, "batch_id": ...}`.
- **Batch end**: `info` with `extra={"batch_size": N, "succeeded": M, "failed": K, "elapsed_ms": ...}`.

Flag `for x in items: logger.info(...)` in workers — the per-item line floods the aggregator and hides the batch-summary signal.

#### Context propagation through `asyncio.to_thread`

The project's logging-slices system uses `contextvars` for correlation IDs. When code offloads blocking work via `asyncio.to_thread(blocking_fn, ...)`:

- The **current** context is captured at the call site (Python preserves it).
- Mutations inside the thread **don't flow back** to the event loop's context.
- If the thread itself spawns more work (a thread pool inside the thread, a `multiprocessing.Pool`), correlation IDs are lost unless explicitly copied: `contextvars.copy_context().run(fn, ...)`.

Flag: a new `asyncio.to_thread(...)` call in worker / agent / NATS handler code where the thread will log → confirm the correlation ID survives, or wrap with `copy_context().run(...)`.

#### Slow-callback detection (dev tip)

When the diff introduces async code paths that might block the event loop, suggest as a one-time tip: run the dev server with `PYTHONASYNCIODEBUG=1` (or `asyncio.run(main(), debug=True)`) and tune `loop.slow_callback_duration` (default 0.1s) — asyncio will log warnings on any callback that exceeds the threshold. Catches accidental sync I/O inside async handlers.

### J. External clients — timeouts, retries, error mapping

The project ships dedicated clients in `src/clients/` (Elsevier, ORCID, Argus, IDX). New external HTTP belongs there.

Flag in client / service code:
- **`httpx.get(...)`** without a `timeout=` argument → eventually hangs in production. The project's clients all set `timeout` from settings.
- **No retry policy** on idempotent reads from a flaky upstream — at minimum `tenacity.retry` or a manual loop with backoff for known-flaky providers.
- **Error mapping leaks**: a service catches `httpx.HTTPStatusError` and re-raises as a vague `RuntimeError`. Map upstream 4xx → domain `NotFound`/`Conflict`/`BadRequest`; map 5xx → `UpstreamUnavailable`; the router translates to HTTP status.
- **Bare `httpx.AsyncClient()` instantiated per call** instead of a long-lived client on the wrapper class — connection pool churn. The existing `ElsevierClient` is the precedent — reuse the client instance.
- **Mixing `requests`** (sync) with the rest of the async stack — a sync HTTP call inside an async handler blocks the event loop. Severity: **Blocker**.

#### Token caches — refresh with a safety margin

For OAuth-bearing clients (ORCID, Elsevier IDX, Keycloak service accounts), the token has a stated `expires_at`. Refreshing exactly at `expires_at` races with clock skew, in-flight requests, and upstream rounding. The project's precedent is `ORCID_TOKEN_SAFETY_MARGIN_SECONDS = 60` in `src/clients/orcid_client.py`.

Flag in new OAuth client code:
- A token cache that compares `time.time() >= expires_at` (no margin) — flip to `time.time() >= expires_at - SAFETY_MARGIN`.
- A constant named `EXPIRES_AT` / `TOKEN_TTL` without a sibling `SAFETY_MARGIN`.
- An in-process cache shared across worker threads/processes without explicit lock — concurrent refreshes hammer the upstream. Use a single lock + check-after-acquire.

#### httpx limits, hooks, retry-after

- **`httpx.Limits(max_connections=..., max_keepalive_connections=...)`** declared explicitly on long-lived `AsyncClient` instances. Defaults (100/20) are usually fine; the point is making them visible so production tuning is reviewable.
- **`event_hooks={"request": [...], "response": [...]}`** for centralised logging instead of wrapping each method. Beats per-method `logger.info(...)`.
- **`Retry-After` header on 429** — parse and honour it before reverting to fixed backoff. Hard-coded sleep ignores upstream signals.
- **`raise_for_status()`** at the boundary of the client (translate HTTP → domain exception) — not in the service. Service receives `NotFound` / `RateLimited` / `UpstreamUnavailable`; never `httpx.HTTPStatusError`.

#### Retry-budget exhaustion → partial result, not failure

When the project ships a long-running enrichment that hits an upstream that can rate-limit or fall over, callers should distinguish **retryable exhaustion** (429, 5xx, transient timeouts × N retries) from **non-retryable error** (404, 401, 400). Retryable exhaustion returns `partial=True` with whatever results were collected — propagating an exception kills the whole workflow when 90% of the rows succeeded. Citation: `OrcidExhaustedError` in `src/clients/orcid_client.py` (FR-010 in feature 049-orcid-enrichment).

Flag in new enrichment client code:
- A retry loop that raises after the last attempt without preserving partial results.
- A service that translates "any upstream error" to a single failure mode — split retryable vs non-retryable, and partial-vs-fatal, in the client.

### K. NATS messaging & workers

The project uses NATS for event streaming (publishers, subjects, durable workers).

Flag:
- **Subject names hardcoded in 2+ places** (`f"user.{user_id}.notifications"` repeated) → constant or builder function. The notification service has the precedent (`_build_enrichment_subject`); follow it.
- **`json.dumps(...).encode()` payload construction** inline at every publish site → small helper.
- **Publishers that don't tolerate `nats_client is None`** when the project's pattern is to gracefully degrade (see `dependencies.py:178` — `get_nats_client()` can return `None`, callers must handle it).
- **No subscriber `ack`** on a JetStream pull subscriber → message redelivery storm. Severity: **Blocker**.
- **Worker handlers without `try/except` around the message body** → one bad message poisons the stream.
- **Sync NATS API in async code** — match the rest of the codebase; nats-py exposes async first.

#### Subject hierarchy — `user.{user_id}.workflow.{workflow_id}.events`

The project uses a hierarchical subject convention so each segment is an access-control / filter boundary. Per-user / per-workflow subjects prevent cross-tenant leaks; flat subjects (`workflow_events`) leak across users. Citation: `src/messaging/publishers.py:_build_subject`.

Flag:
- A new event published to a flat subject (`workflow_events`, `notifications`) when the equivalent hierarchical form (`user.{id}.workflow.{wid}.events`) exists.
- Subject builders that interpolate a non-validated user ID/workflow ID — could match `*` wildcards meant for filtering. Sanitise before interpolating.
- Inline f-strings building the subject in 2+ places → a `_build_<scope>_subject(...)` helper alongside the existing precedent.

#### JetStream vs core-inbox publishing

Browser inbox subscriptions (`_INBOX.*`) don't have `$JS.API.*` permissions, so JetStream publish to them fails. The project's pattern (per `publishers.py:publish_workflow_event`):

- If the caller passes an explicit `inbox=` (e.g. browser-supplied reply subject), publish to **core NATS** (`nc.publish(subject, payload)`).
- Otherwise publish to the **JetStream stream** (`js.publish(subject, payload)`).

Flag:
- A new publisher that always uses `js.publish(...)` and accepts a browser inbox — will fail silently for browser subscribers.
- A new publisher that always uses `nc.publish(...)` for events that need durability (workflow lifecycle, audit events) — durability lost on restart.

#### Durable consumers and queue subscriptions

For workers that must survive restarts and load-balance across pods:

- **`durable=<name>`** — survives restarts; redelivery resumes from last ack. Missing `durable` → on every restart, the consumer rewinds to the stream's current head and may miss messages produced during the gap.
- **`deliver_group=<name>`** — load-balances across multiple consumer instances of the same `durable`. Missing → every pod gets every message.
- **`max_deliver=<N>`** — caps redeliveries on a poison message. Missing → infinite redelivery on the same bad payload. Recommend `max_deliver=5` with a dead-letter subject.
- **`max_ack_pending=<N>`** — caps in-flight unacked messages. Missing → a slow consumer + fast producer can blow memory.
- **Naming convention** — `durable=` should encode the worker class (`enrichment-worker`, `notifications-worker`), not be ad-hoc per file. Cite the existing names in `src/workers/`.

#### Ack / nak / term semantics — explicit, never auto

JetStream pull/push consumers expose four terminal-state methods:
- `await msg.ack()` — success; never redeliver.
- `await msg.nak(delay=...)` — transient failure; redeliver after delay (use this for upstream timeouts, lock conflicts).
- `await msg.term()` — poison; never redeliver. Pair with a dead-letter publish to keep the message inspectable.
- `await msg.in_progress()` — long-running; renew the ack lease before timeout. Required for handlers that exceed `ack_wait`.

Flag:
- A handler that `try/except: pass`s without acking/naking — message redelivers forever (or never, depending on consumer config). Severity: **Blocker**.
- A handler that `await msg.ack()`s before the work succeeds — at-most-once when the consumer was set up for at-least-once. Severity: **Blocker**.
- A long-running handler (>30s typical) without `await msg.in_progress()` calls — message redelivers mid-processing. Severity: **Blocker** for orchestration-tier handlers.
- `auto_ack=True` on a JetStream subscription — bypass of the explicit-control contract; only acceptable for stateless ephemeral consumers, never for workers that mutate state.

### L. Auth, permissions, and audit

Auth is Keycloak via `fastapi-keycloak-middleware`; user surfaces through `UserContext`.

Flag — all **Blocker** unless noted:
- A new mutating route (POST/PUT/DELETE/PATCH) without `Depends(get_current_user)` → unauth public mutation.
- A read route exposing user-scoped data without filtering by `user.user_id` in the service. Cross-tenant leak.
- **Trusting a path / query parameter to identify the user** (`/users/{user_id}/notifications`) instead of `user.user_id` from the token — IDOR class bug.
- **Role checks inline in the route** (`if user.role != "admin": raise ...`) when the project has a dependency for it. If no role-check dep exists yet, suggest creating one in `src/auth/dependencies.py` rather than scattering `if` checks.
- **Logging tokens / refresh tokens / authorization headers** in plaintext (Severity: **Blocker**).
- **Missing audit log** on a sensitive admin action when the project has an `AuditService` (see `src/auth/audit.py`). Severity: **Suggestion**, **Blocker** if the action mutates user data on someone else's behalf.

### M. Type hints & escape hatches

The project type-checks with mypy. Python 3.11+ idioms are mandatory in new code.

In the diff, flag newly-added:
- **`Any`** / `# type: ignore` / `cast(X, …)` without an explanatory comment.
- **Untyped function signatures** (no return annotation, no param annotations).
- **`from typing import Optional, List, Dict, Tuple, Set`** when the file is otherwise modern → use `X | None`, `list[X]`, `dict[K, V]`, etc.
- **`foo: Optional[X] = None`** mixed with **`bar: X | None = None`** in the same file → pick one.
- **`*args`, `**kwargs`** typed as untyped (`Any`) when the call shape is known — narrow the type.
- **Pydantic v1 patterns**: `Config` inner class, `validator`, `root_validator`, `parse_obj`, `dict()`, `json()` — all replaced in v2 with `model_config = ConfigDict(...)`, `field_validator`, `model_validator`, `model_validate`, `model_dump`, `model_dump_json`.
- **`Awaitable[X]` annotations** when `X` is what's awaited and the function is `async` → drop, just `-> X`.

For each escape hatch, suggest the narrowing the type system would have given for free (e.g. `params: dict[str, Any]` → a Pydantic model from `src/schemas/`; a `Mapped[X]` on the model side).

#### Typed primitives in service signatures

Pydantic typed primitives are not just for schemas — they're useful in service / function signatures where they narrow `str` / `int` parameters at the call site:
- `email: EmailStr` over `email: str`.
- `url: HttpUrl` over `url: str`.
- `count: PositiveInt` (or `count: Annotated[int, Field(gt=0)]`) over `count: int`.
- `secret: SecretStr` over `secret: str` for any function whose argument shouldn't end up in an `extra={...}` log line.
- `user_id: UUID` over `user_id: str` whenever the value will eventually become a `UUID(user_id)` cast — push the validation upstream, not deep in the call chain.

Flag service methods that re-validate a `str` argument they could have received as a typed primitive ("this method does `if not value.startswith('http')` on a URL it received as `str`"). Severity: **Suggestion**.

### N. Errors — specific exceptions, correct HTTP status

- New `HTTPException(status_code=500, ...)` in a router → almost always the wrong layer. Either map a specific upstream/service exception to a meaningful 4xx, or let it propagate to FastAPI's default handler so it logs + returns 500.
- **Wrong status codes**: 404 used for "validation failed" (should be 400/422), 200 used for "created" (should be 201), 200 used for "no body" (should be 204).
- **Status hardcoded as integer literal** (`status_code=204`) → use `status.HTTP_204_NO_CONTENT` constant. Match project style — the existing routers use the constants.
- **Missing `detail`** on `HTTPException` for 4xx → always supply a human-readable message.

### O. Tests — async, scoped, contract-first

The project's tests live in `tests/{contract,integration,unit}/`. `pytest-asyncio` is configured with `asyncio_mode=auto` and session-scoped event loop.

For new feature code in the diff, flag:
- **No corresponding test** for a new route, service method, or model. Severity: **Suggestion** by default; **Blocker** if the new code:
  - **Mutates user data** (write/delete on user-scoped tables),
  - **Performs auth / permission checks**,
  - **Implements idempotency** (e.g. `mark_read`),
  - **Touches money / billing / sanctions logic**.
- **Test placed in the wrong tier**: a test that uses `respx` to mock HTTP belongs in `unit/` or `integration/` per project precedent — not `contract/`. Contract tests verify the OpenAPI spec.
- **`def test_...`** instead of **`async def test_...`** for an async-stack test — silently no-ops or mis-fires. Severity: **Blocker**.
- **`@pytest.fixture` not async** when the fixture awaits the DB → must be `@pytest_asyncio.fixture` or a plain `async def` fixture (depending on configured plugin).
- **New integration test that doesn't restore state** (no `await db.rollback()` / fixture teardown) — leaks across tests under session-scoped event loop. The project's session-scope means ordering matters: a test that mutates without rollback breaks downstream tests.
- **`.commit()` inside a test** without a strong reason — usually wrong; the test fixture's transaction should hold the changes for assertion then rollback.
- **Mocking the DB** (`AsyncMock(spec=AsyncSession)`) when the project pattern is "real DB via test container / fixture" → talk to the DB, mock only the boundaries (`respx` for HTTP, NATS test client). Severity: **Suggestion**.
- **`time.sleep` / blocking sleep** in async tests → `await asyncio.sleep(...)`.

This rule is **never** auto-applied — moves to **Needs you**. Auto-generating tests produces false confidence.

#### Pydantic round-trip validation in contract tests

Contract tests must validate the wire shape, not just the in-process model. The project's precedent (`tests/contract/test_agent_result_event_contract.py`) is:

```python
payload = MyEvent(...).model_dump_json(by_alias=True)
restored = MyEvent.model_validate_json(payload)
assert restored == original
```

Catches silent serialization bugs: missing `by_alias=True`, alias keys that don't survive a round-trip, fields that serialise but don't deserialise. Flag contract tests on new schemas that assert against `model.model_dump()` only — they pass even when the JSON wire form is broken.

Cross-field invariants (e.g. `partial ⇒ reason set`) belong in this same test as `pytest.raises(ValidationError)` cases.

#### Time-sensitive tests — `freezegun` / `time_machine`

For tests touching datetime invariants — recency windows (the 10-year affiliation rule), TTLs, expiry checks, "X happened in the last 7 days" filters — the test must control time. Otherwise it's flaky as the calendar moves.

Flag: a new test that:
- Uses `datetime.now(timezone.utc)` directly in assertions (e.g. `assert event.created_at < datetime.now(...)`),
- Computes a "now-relative" cutoff manually (`cutoff = datetime.now() - timedelta(days=10)`),
- Will produce a different result on a future date than today.

Suggest `freezegun.freeze_time("2026-05-05")` (already a transitive dep of pytest plugins, or trivially `pip install freezegun`) or `time_machine.travel(...)` as the lighter alternative.

#### HTTP mocking — `respx` is the project's answer

The project ships `respx` as a dev dep. Flag tests that:
- Mock `httpx.AsyncClient` directly via `unittest.mock.AsyncMock(spec=httpx.AsyncClient)` — fragile, drifts from the real API.
- Hit a live upstream in unit tests — integration tests only.

The right pattern: `respx_mock.post("https://api.example.com/...").mock(return_value=httpx.Response(200, json=...))`. Project test suites already use it; new tests should match.

#### Factories over hand-crafted fixtures

When the same ORM/Pydantic shape is built across 5+ tests with minor variations, prefer `polyfactory.ModelFactory` / `factory_boy.SubFactory` over per-test fixture explosion. Cite the existing factory if one exists (project tests have varied patterns; check before recommending). Severity: **Suggestion**.

### P. Defaults over manual config

- Don't pass kwargs that match the framework default (`async_sessionmaker(autocommit=False, autoflush=False)` — `autocommit=False` is already default; `autoflush=True` is default and the project deliberately overrides to `False`, which is a non-default — keep that one).
- Don't re-implement what a library already provides:
  - manual JSON parsing of an HTTP response when `httpx.Response.json()` works,
  - hand-rolled retry loops when `tenacity` is in deps,
  - manual JWT decoding when `PyJWT` / the keycloak middleware already covers it,
  - manual schema → dict mapping when `model_dump(by_alias=True)` does it,
  - manual UUID parsing when FastAPI already coerces from path/query types.
- **Don't add a guard for a precondition the framework / dep already enforces**:
  ```python
  @router.get("/{notification_id}")
  async def get_one(notification_id: UUID):
      if not notification_id:  # ← dead — FastAPI 422s before we get here
          raise HTTPException(...)
  ```
- **Don't change framework defaults without a written reason on the same line** (or a project-wide convention captured in a wrapper).

### Q. Loops, comprehensions, and async patterns

- **`asyncio.gather(...)` for I/O fan-out** rather than sequential `await` in a loop when the calls are independent (e.g. enriching N researchers from upstream APIs). Severity: **Suggestion**.
- **Missing `return_exceptions=True`** on `asyncio.gather` over a list of upstream calls where one failure shouldn't kill the whole batch.
- **`for x in xs: await ...`** when the loop builds a list and the items are independent → comprehension + gather.
- **Synchronous file I/O in async handlers** (`open(...)`, `pathlib.read_text()`) blocks the event loop. Use `aiofiles` or push to a thread (`asyncio.to_thread(...)`) for non-trivial reads.
- **`asyncio.create_task(...)` without holding the reference** → task can be garbage-collected mid-flight. Hold it in a set / awaited later, or use a `TaskGroup`.

#### Structured concurrency — prefer `TaskGroup` (Python 3.11+)

Python 3.11 ships `asyncio.TaskGroup` for structured fan-out:

```python
async with asyncio.TaskGroup() as tg:
    a = tg.create_task(fetch_a())
    b = tg.create_task(fetch_b())
# both awaited; first exception cancels siblings; ExceptionGroup raised at exit
```

Prefer this over `asyncio.gather(...)` when:
- You want **first-exception cancellation** (the default `gather` waits for siblings; `TaskGroup` cancels them).
- You want **structured cleanup** — if the body raises, all child tasks are cancelled cleanly.
- You want grouped error reporting via `ExceptionGroup` (matchable with `except*`).

Stick with `asyncio.gather(..., return_exceptions=True)` only when you genuinely want all results (or all exceptions) regardless of failures — the "best-effort enrichment" pattern.

Flag in new code: `asyncio.gather(...)` without `return_exceptions=True` where a `TaskGroup` would be cleaner. Severity: **Suggestion**.

#### `asyncio.shield` for cleanup

`asyncio.shield(coro)` protects a coroutine from cancellation by the caller. Use for cleanup work that **must** complete:

```python
try:
    result = await long_running_op()
finally:
    await asyncio.shield(emit_audit_event(...))   # survives caller cancellation
```

Flag a new mutating handler that does cleanup (audit emit, cache invalidation, NATS ack) inside a `finally` without shielding — caller cancellation mid-cleanup leaves invariant-breaking state.

#### Avoid mixing `asyncio.run(...)` with FastAPI's loop

FastAPI runs its own loop. Calling `asyncio.run(...)` from inside a route or service spins up a *second* loop and breaks anything that uses contextvars / DB sessions / NATS clients tied to the first. If a sync code path needs to wake an async one, use `asyncio.to_thread(...)` or `loop.run_in_executor(...)` from the right side. Severity: **Blocker**.

### R. Constants, query keys & repeated literals

- **Magic strings used as event types / subject names / role names / section types** in 2+ places → constant. The project has `NOTIFICATION_TYPE_ENRICHMENT_COMPLETED` (`notification_service.py:24`) as the precedent for one-off feature-local constants — module-level above the service class. Larger sets belong in an `enums.py` (the workflow service has `enums.py` with `WorkflowCompletionType`).
- **`Literal[...]` unions repeated in 2+ signatures** — extract to a named alias and use it everywhere. Same shape as fe-code-review §I but for Python: `NotificationCompletionFilter = Literal["success", "partial", "all"]` in the schema, imported at every call site.
- **Status discriminants compared with `==`** across files (`status == "running"`, `status == "completed"`) → prefer an enum (`StrEnum` for stringy values, `IntEnum` for numeric) so the comparison is type-checked and the canonical names live in one file.
- **Raw status strings stored in DB columns**: keep them as strings (the project does — `String(20)` for `completion_type`) but expose typed enums to Python callers (`WorkflowCompletionType.PARTIAL.value` — see `notification_service.py:164`).
- **Sweep rule**: when you flag this pattern in one place, search the whole diff for the same literal union and list every other occurrence in the same finding so the user fixes them all at once.

### S. Dead code, duplication, and pointless indirection

In the changed files, flag (skip subitems already covered by linter — see §2):
- Unused exports / unused imports / unused locals (skip if flake8 already reports them).
- Commented-out code blocks.
- `print` left in (covered above), `breakpoint()` / `pdb.set_trace()` left in.
- Unreachable branches.
- **Pass-through re-export** in a file that isn't a barrel (`src/services/__init__.py` is a barrel; `src/services/notification_service.py` is not) — drop and import directly.
- **Pointless type alias**: `Foo = Bar` where `Foo` is never narrowed or documented and `Bar` is already exported.
- **Pointless function wrapper**: `def wrap(x): return inner(x)` — drop, use `inner` directly.
- **Stale TODO/FIXME** added in this diff with no ticket reference.
- **Two services / methods doing the same thing under different names** → consolidate.
- **Same SQL `select` with slight WHERE variations duplicated across methods** → factor a private `_base_query()` returning the partial statement, callers add their `where(...)`.
- **Merge conflict markers** anywhere in the diff. Grep for `^<<<<<<<`, `^=======`, `^>>>>>>>` at line start; flag every occurrence. The diff cannot land with conflict markers in source. Severity: **Blocker**. Past review caught a `<<<<<<< organziation-search` block that had been pushed.

#### Hand-rolled re-implementations of framework primitives

**The lens.** When the diff hand-rolls a multi-line construct that encodes a common operation, ask: *does SQLAlchemy / Postgres / Pydantic / the stdlib already have one call for this?* If yes, prefer the primitive. The hand-rolled form is shorter to type but longer to read, easier to break in maintenance (someone flips a `<` to `<=`, drops a branch, or forgets a tiebreaker), and the framework / query optimizer often can't recognize what it's looking at.

**Trigger heuristic.** Any time you see 3+ lines of `or_(...)` / `and_(...)` / `if … else …` / chained `case(...)` / a manual loop that builds a SQL fragment — *pause and name the operation*. If you can name it in two words ("lexicographic compare", "set membership", "range check", "upsert", "null-coalesce", "case-insensitive equality", "exists check"), there is almost certainly a one-call primitive for it.

**Catalogue (non-exhaustive — the lens is the rule, this is just a starter).**

| Hand-rolled shape | Primitive | Why the primitive wins |
| --- | --- | --- |
| `or_(a < qa, and_(a == qa, b < qb))` (lexicographic compare) | `tuple_(a, b) < tuple_(qa, qb)` | Composite-index range scan; no flippable tiebreaker. |
| `or_(col == 'a', col == 'b', col == 'c')` (chain of equals) | `col.in_([...])` | Single `= ANY(...)`; index-friendly; clients can extend the list. |
| `col >= a, col <= b` (paired bounds) | `col.between(a, b)` | One predicate; intent reads at a glance. |
| `func.lower(col) == val.lower()` (manual case-fold) | `col.ilike(val)` | Uses Postgres operator; works with trigram indexes. |
| Manual `if exists: update else insert` | `INSERT … ON CONFLICT DO UPDATE` | Atomic; no race. |
| `count(*) > 0` for existence | `select(exists(...))` | Stops at first row; doesn't materialise count. |
| `col if col is not None else fallback` inside a `select` | `func.coalesce(col, fallback)` | Evaluates server-side; survives joins. |
| Hand-rolled NULLS FIRST/LAST via `case(...)` | `col.nulls_first()` / `col.nulls_last()` | Native ORDER BY clause; planner-aware. |
| `Optional[X]` / `Union[X, None]` typing forms | `X \| None` | Project-mandated (§D). |
| `obj.dict()` then build a new dict | `Schema.model_validate(orm_obj)` (§C) | Already a project rule — same lens. |

Severity: **Suggestion (Mechanical)** by default — both forms are correct, the rewrite is a one-line swap. Promote to **Structural** only when the hand-rolled form has measurable cost (wrong index plan, race window, > 5× more code). Don't flag if the primitive doesn't exist for the project's stack version (note the version constraint when in doubt).

What this rule is **not**: a license to rewrite working code in unchanged files (§8 still applies — diff-scoped only), or to invent abstractions ("a generic seek helper") — the primitive is the framework's, not yours.

Citation (Appendix A): hand-rolled re-implementation of framework primitive.

### T. Data modelling & reference data — keep PG the single source of truth

The project's stance (per past review): **"Let's keep all info in one place — PG in our case."** Application code shouldn't carry domain reference data that the database could own. Severity for new code: **Blocker** for the hardcoded-dict pattern; **Suggestion** for everything that can be coupled more tightly.

#### Hardcoded reference dictionaries belong in tables

Flag any new module-level `dict` / `set` / `list[tuple]` that encodes domain reference data. Common shapes:

- ISO country codes / names / regions (`_ISO2_TO_COUNTRY: dict[str, str] = {"CN": "China", ...}`).
- Static lists of "foreign concern" countries, sanctioned entities, denied parties.
- Org acronyms, alt-name mappings, journal-name → ISSN tables.
- Section 1286 / OFAC / Entity List membership snapshots.
- Any table-shaped data shipped as a Python literal in a `_constants.py` / `_data.py` module.

Fix:
1. Move the data into a PG table (with a migration that seeds it).
2. Read it from a service that wraps the table (`CountryService.iso2_to_name(code)`, etc.).
3. Delete the Python literal.

Cite the past-review precedent in the finding: `_ISO2_TO_COUNTRY` was rejected with "Just add iso2 column to table and add those to migration and drop hardcoded dictionary."

Exceptions (don't flag):
- Tiny enum-like sets used purely for type narrowing (`_ALLOWED_VERBS = {"GET", "POST"}`) — that's a code constant, not domain reference data.
- Test fixtures hardcoding the same data — tests are allowed to be self-contained.

#### Coupling — FK / xref over loose string references

Cross-table relationships use FKs (or, where source IDs are unstable, an xref table whose own rows carry the natural key). Flag:

- A new table whose rows reference a domain entity by **free-text name** instead of by FK / xref. E.g. `section1286_institutions.org_name TEXT` referring to `organizations.name` — should be FK on `organizations.id`, with the source-supplied name on the xref row.
- A new table whose rows reference a known entity by an **external ID** (`elsevier_affiliation_id`) without also linking to the project's own primary key on that entity. The project's policy (per past review): "we should have own primary key on orgs with elsevier ID as business key there. So lists will be always referring our own key regardless if those are present in elsevier DB or not."
- A new "list of X" feature that doesn't insert unmatched X-entries into the canonical X-table. Past review on Section 1286 explicitly said: "for every 1286 org that is not present there yet — by name or any of alternative names — put a new entry in orgs. If org is already present — put 1286 alternative names to org alternative names."

#### Normalised side tables over JSON in main entities

Flag a new column added to a domain table whose value is a **JSON array of structured records** that have a fixed shape. Past review: "this should be normalized in a separate table with separate fields rather than JSON in main table."

Examples that qualify:
- `affiliations.risks JSONB` (list of `{source, risk, country_code, ...}`) → a `risks` table with FK to `affiliations.id` and one row per risk.
- `researchers.publications JSONB` → `researcher_publications` table.
- `organizations.alternative_names_with_source JSONB` → `organization_aliases` table with FK + source column.

JSON columns are fine for **truly opaque payloads** (vendor webhook bodies, free-form telemetry, model outputs) where the schema is unstable or the data is never queried structurally. They are not fine for "list of typed records I'll later query by source / by date / by status."

#### Generic table design over per-source duplication

Past review on Section 1286 list tables: "We need more generic table — section1286 should be just one of the possible 'source' values so that we won't be adding new tables for every new 'risk' list."

Apply to any new "list of risky / blocked / approved entities" table. The right shape:

```
risk_lists                    -- the catalogue of lists themselves (one row per list version)
  id PK
  source TEXT      -- 'SECTION_1286', 'OFAC_SDN', 'ENTITY_LIST', ...
  version TEXT
  effective_at TIMESTAMPTZ

risk_list_entries             -- many-to-many between lists and orgs/persons
  id PK
  risk_list_id FK -> risk_lists
  organization_id FK -> organizations  (nullable if entry is a person)
  person_id FK -> persons              (nullable if entry is an org)
  source_supplied_name TEXT            -- exactly what the source called it
  added_at, removed_at TIMESTAMPTZ     -- for window-function diff queries
```

Flag: any new `<source>_list_versions` / `<source>_institutions` / `<source>_xxx` table is a **Blocker** unless the diff explicitly explains why genericity wouldn't fit.

#### Schema completeness — surface known-extracted fields

Past review on the content schema: extracted fields existed in the model but were missing from the API schema (emails, links, summary). The reviewer asked to surface them. Flag the inverse pattern in the diff:

- A schema is added / modified for an extracted-data response, but the **underlying model / extraction step produces fields the schema omits**. Read the extraction code in `src/agents/...` and the matching ORM model: any field they produce that's not in the schema is a candidate for inclusion (Severity: **Suggestion** unless the field is sensitive — emails / contact info — in which case the call is the team's).
- A response schema strips fields that the consuming UI demonstrably needs (cross-check with `ffrs-ui` if accessible).

### U. `scripts/` directory hygiene — local utilities don't ship to prod

The project's policy (per past review): production-image scripts whose only purpose is "run once locally and report" don't belong in the repo. They get installed into the production image, add CVE surface, and rot.

Flag in the diff:

- A new file under `scripts/` that:
  - Connects to the production / live database via raw connection strings.
  - Writes report files (CSV / JSON) to disk as its primary output.
  - Reads from a hardcoded XLSX / CSV the user keeps locally.
  - Has docstring / comments saying "one-time", "ad-hoc", "to investigate X".
- A new "data load" script (`scripts/load_orgs_from_excel.py`-shape) that's the production mechanism for seeding reference data. The right answer is one of:
  - **Migration**: if the data is canonical and identical across all envs, embed it in an alembic migration.
  - **CRUD API**: if the data needs ongoing manipulation per environment, add CRUD endpoints (under the matching router) and let an API client manage it.
- A new script that requires direct DB connection from a developer's laptop to a non-local environment to be useful — past review: "We won't be able to run script by connecting e.g. to prod DB directly."

Severity: **Blocker** for new scripts shipped in the repo image when the work belongs in a migration or CRUD endpoint.

When the script is genuinely a developer-only one-off (data quality investigation, local snapshot analysis), the right action is to **not commit it at all** — run it locally, attach the output to the Jira ticket, drop the file before merge.

If the diff includes both a new debug API endpoint (§B) **and** a sibling script in `scripts/` that does the same thing, flag both with a single combined finding citing the past-review pattern.

### V. Package hygiene

If `pyproject.toml` or `uv.lock` changed:

```bash
git diff --find-renames <range> -- pyproject.toml | grep -E '^\+' | grep -v '^+++'
```

For every newly added dependency:
- Confirm it is actually imported (`git grep -l "import <pkg>" -- 'src/**/*.py' 'tests/**/*.py'`).
- Flag if added but unused.
- Flag if added when an existing dep already covers it (the project already has `httpx` — adding `aiohttp` needs justification; already has `pydantic` — adding `marshmallow` is a smell).
- Flag heavyweight deps for a tiny use case.
- Flag removed deps that still have imports somewhere.
- Flag `pyproject.toml` change without `uv.lock` regenerated (and vice versa). Severity: **Blocker**.
- Flag a dep added under `[project].dependencies` when it's only used in tests — should be `[tool.uv].dev-dependencies`.

### W. Agents & LangGraph — parallel state, sync barriers, runnable config

`src/agents/` has its own constitutions: `AGENT_CONSTITUTION.md` and `LANGGRAPH_CONSTITUTION.md`. When the diff touches agent internals (graph structure, prompts, tool definitions, structured outputs), recommend running `/agent-review` alongside be-code-review.

The patterns be-code-review surfaces:

- **Reducer discipline (Blocker)** — fields written by parallel `Send(...)` branches need `Annotated[list[T], operator.add]` (lists), `Annotated[dict, merge_dicts]` (dicts). A scalar written by parallel branches is a design bug; propose list-with-add, branch-id-keyed dict, or a collector node. `operator.add` on dicts merges keys but **overwrites collisions** — verify intent.
- **Empty-dict sync barrier (Blocker)** — sync nodes (`defer=True` + `Send` predecessors) returning the accumulated state cause `operator.add(existing, existing)` to double-count on the next iteration. Return `{}` from sync nodes. Citation: `collect_all_results` in `url_information_extraction/helpers/collection_nodes.py`.
- **`RunnableConfig` thread-id propagation (Suggestion; Blocker for orchestrator-registered steps)** — agent entrypoints accept `config: RunnableConfig | None = None`, default to `{"configurable": {"thread_id": str(uuid4())}}`, and forward to `graph.ainvoke(..., config=config)`. Missing → LangSmith/Langfuse tracing and resumability both break.
- **RPC-vs-local sub-agent dispatch (Suggestion)** — sub-agent calls dispatch via `config.get("configurable", {}).get("rpc_client")` with local graph import as fallback. Hard-coding either side breaks the hybrid (local in dev/eval, NATS RPC in prod). Citation: `url_information_extraction/helpers/graph_utils.py`.
- **Code layout** — agents follow `graphs/` (entrypoints) / `states/` / `nodes/` / `helpers/` / `prompts/` / `models/` (LLM structured outputs) / `data/` (fixtures). Flag a node function in `helpers/`, a state schema in `nodes/`, etc.

### X. Long-running orchestration — heartbeats, sessions, partial completion

`src/services/workflow_service/` patterns. Read `orchestrator.py`, `agent_task_monitor.py`, `langgraph/nats_step_handler.py` before reviewing changes.

- **Heartbeat registration (Blocker)** — every NATS-RPC step pairs the call with `AgentTaskMonitor.register_task(task_id, agent_type, workflow_id, step_name)`. The monitor reads `substep_started` / `substep_completed` events as heartbeats; missing → orchestrator can't detect a hung agent. Long-running agents must emit substep events for the monitor to flow. Don't roll your own monitoring loop.
- **Short-lived DB sessions (Blocker)** — never hold `async with self._session_factory()` across an `await` on an LLM call, HTTP call, NATS RPC, or `asyncio.sleep(>0.1)`. Pattern: acquire per discrete op (~10ms), release immediately. Long-held sessions exhaust the pool under any real concurrency.
- **Partial completion (Blocker)** — step handlers catch `AgentPartialCompletionError`, extract its output dict, propagate as `status="partial", reason=...` (`user_cancelled`, `payload_too_large` are valid). Re-raising kills the workflow on a valid terminal state. Always propagate `reason` so notifications can distinguish.
- **Warehouse graceful degradation (Blocker)** — callers catch `WarehouseNotConfiguredError` and return `status="skipped", reason="warehouse_unconfigured"`. Otherwise the whole workflow fails when the feature isn't available in this env.
- **Dual-DB boundaries** — local DB (read/write, app data) via `get_db` / `get_session_factory`. Warehouse DB (read-only, bibliometrics) via `ElsevierDataService` only. Flag: direct `text(...)` against warehouse from a non-`ElsevierDataService` caller; any write to warehouse; cross-DB joins in app code (do load-then-merge instead).

### Y. Domain invariants — risk, affiliation, organisation

Patterns enforced in `risk_check_service.py` and `affiliation_service.py`. New code regularly stomps these.

- **Fuzzy org match — full ladder** — canonical `name` → `alternative_names` → `acronyms` → word-token (≥2-char, stop words excluded) → edit-distance-1. Skipping a level under-flags. Flag matchers using only `name` / only exact equality without normalisation (case, punctuation, whitespace) / no stop-word pre-filter.
- **Recency window** — current boundary is 10 years (`end_year >= current_year - 10`). Match it; `>` vs `>=` mis-classifies by one year. Compute `current_year` inside the function so `freezegun` can pin it. Flag a different window without a written policy change.
- **Risk-source versioning** — new risk sources register a `(label, ISO date, datetime)` tuple in `_SOURCE_VERSIONS` and use an `effective_at` the matcher reads. Otherwise reports can't say "flagged by SECTION_1286 v1, 2024-07-19".
- **Org single source of truth** — canonical handle is the `affiliations` row (`id`, `name`, `alternative_names`, `acronyms`, `country`). Every list-of-orgs feature: (1) inserts unmatched orgs into the canonical table, (2) merges incoming names into `alternative_names` for matched orgs, (3) references by own PK, not external Elsevier ID. (Reinforces §F.4.)

### Z. Audit & security event emission

`src/auth/audit.py` ships `AuditService` + `AuditEventType` enum. Every security-relevant action emits.

- **Mutating admin route without `AuditService.record(AuditEventType.<X>, ...)`** — Blocker for actions on someone else's data; Suggestion for self-actions.
- **New auth code path** (token validate / role check / token refresh / revoke / logout) without the matching enum event.
- **Ad-hoc event name** (`"admin_deleted_X"`) instead of an `AuditEventType` entry — extend the enum.
- **Audit emit inside the same transaction** as the operation it audits — both rollback together; audit must record both successes and failures. Move to a separate session or `try/finally`.
- **Unwrapped audit emit** that can raise into the handler — wrap, `logger.exception(...)` the failure. **Audit never load-bears the request.**
- **Tokens / `Authorization` headers** in plaintext audit `extra={...}` — Blocker.

What to audit (yes if a SOC2-style auditor would want it in the table): login success/failure, token refresh/revoke, logout, MFA, role/permission changes, account create/delete, password/email change, data export, deleting another user's data, system config / retention / audit settings change. Workflow start/cancel/complete already flow as workflow events; audit covers the user-data-touching slice.

## 5.5. Pre-emit self-audit — grep spot-checks

Before emitting the report, run these greps over the changed files. Hits are not findings on their own — they're prompts to walk back to §5 and decide severity. The goal is to catch rules whose pattern *literally appears* in the diff and you missed.

```bash
CHANGED=$(git diff --find-renames --name-only "$MB"...HEAD -- '*.py')
MIG=$(echo "$CHANGED" | grep '^alembic/versions/')

# Layers, schemas, types (§A §C §D §M)
grep -nE 'from sqlalchemy|select\(|delete\(' $(echo "$CHANGED" | grep '^src/routers/')
grep -nE 'HTTPException|fastapi\.Request|fastapi\.Response' $(echo "$CHANGED" | grep '^src/services/')
grep -nE 'class \w+\(BaseModel\)' $CHANGED                 # not CamelCaseModel
grep -nE '\b(Optional|List|Dict|Tuple|Set)\[' $CHANGED      # legacy typing
grep -nE '\.dict\(\)|parse_obj|\.json\(\)' $CHANGED         # Pydantic v1
grep -nE 'as Any\b|: Any\b|cast\(|# type: ignore' $CHANGED  # escape hatches

# DB / async (§E §Q)
grep -nE '\bdb\.query\(' $CHANGED                           # sync ORM
grep -nE 'datetime\.utcnow' $CHANGED                        # naive UTC
grep -nE 'requests\.(get|post|put|delete|patch)' $CHANGED   # sync HTTP
grep -nE 'asyncio\.run\(' $CHANGED                          # nested loops
grep -nE 'asyncio\.gather\((?![^)]*return_exceptions)' $CHANGED

# Migrations (§F)
grep -nE 'json\.dumps|configurations|value_text' $MIG       # JSON-in-config seed
grep -nE 'open\(|csv\.|Path\(__file__' $MIG                 # external file IO
grep -nE 'ON CONFLICT.*EXCLUDED\.\w*(names|aliases|tags)' $MIG  # array overwrite
grep -nE 'down_revision' $MIG  # then walk chain vs `main` head

# Routers / pagination (§B)
grep -nE 'beforeCreatedAt|before_created_at.*before_id' $CHANGED        # split cursor
grep -nE 'limit\s*\+\s*1|LIMIT.*\+\s*1' $CHANGED                        # N+1 trick
grep -nE '"(unread|total|count|hasMore)Count?":' $CHANGED               # bundled counts
grep -nE '@router\.\w+\([^)]*"(/debug|/report|/missing|/_internal)' $CHANGED

# Logging, secrets, scripts (§I §H §U)
grep -rnE 'print\(' src/                                    # prints in src
grep -nE 'logger\.\w+\(f"' $CHANGED                         # f-string logs
grep -rnE 'os\.(environ\[|getenv\()' src/                   # bypassing settings

# Conflict markers, NATS (§S §K)
git grep -nE '^(<{7}|={7}|>{7})' -- $CHANGED                # BLOCKER if any hit
grep -nE 'auto_ack\s*=\s*True' $CHANGED                     # JetStream foot-gun

# Service-method param count (§C) — multi-line aware via Python AST.
# A single-line grep silently misses long signatures spread over many lines
# (which is *exactly* the shape that triggers this rule). Use the AST.
python3 - <<'PY' $CHANGED
import ast, sys
SKIP_ARGS = {"self", "cls", "db", "session"}

def is_route_handler(fn):
    """§C exempts FastAPI route signatures — Annotated[..., Query/Body/Depends]
    per param is the convention. Detect by decorators on the function:
    @router.<verb>(...) or @app.<verb>(...) or any @<x>.<verb> shaped decorator.
    """
    HTTP_VERBS = {"get", "post", "put", "delete", "patch", "head", "options"}
    for dec in fn.decorator_list:
        call = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(call, ast.Attribute) and call.attr in HTTP_VERBS:
            return True
    return False

for path in sys.argv[1:]:
    try:
        tree = ast.parse(open(path).read(), path)
    except Exception:
        continue
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if is_route_handler(node):
            continue  # §C exempt
        args = [a.arg for a in node.args.args if a.arg not in SKIP_ARGS]
        defaults = node.args.defaults
        triggers = []
        if len(args) > 4:
            triggers.append(f">4 params (got {len(args)})")
        if len(defaults) >= 2:
            triggers.append(f"2+ optional defaults (got {len(defaults)})")
        if triggers:
            print(f"{path}:{node.lineno}: {node.name}: " + " + ".join(triggers))
PY

# Service / branch shape
ls $MIG  # ≥ 2 files on same branch touching same table → squash candidate
```

**Why an AST check, not a regex**: the canonical shape that needs bundling
(`list_for_user(self, user_id, limit=20, before_created_at=None, before_id=None, completion_type="success")`)
is almost always written across many lines, so a single-line `grep` returns
zero hits and the rule silently no-ops. AST counts the args regardless of
formatting and also surfaces the "2+ optional defaults" half of §C that the
old regex ignored.

In addition, manually verify (no grep can catch these):
- **Pre-flight**: active spec detected; `spec.md` / `data-model.md` / `contracts/` cross-checked.
- **Severity floor**: every drafted finding's severity ≥ source rule's stated severity. Auth bypass / missing migration / missing heartbeat / agent reducer missing / merge markers / split cursor / `nextCursor=null` on empty / hardcoded secrets — these never demote.
- **Bruno sync**: every changed router has matching `bruno/ffrs-api/<resource>/*.bru`.
- **Migration chain**: each new migration's `down_revision` walks back to the head on `origin/$BASE`.
- **Agent state (§W)**: every parallel-write field has `Annotated[T, reducer]`; sync-barrier nodes return `{}`; agent entrypoints accept `RunnableConfig`.
- **Long-running steps (§X)**: `AgentTaskMonitor.register_task` paired; no DB session held across LLM/HTTP/NATS awaits; `AgentPartialCompletionError` propagated as partial; `WarehouseNotConfiguredError` caught.
- **Domain (§Y)**: org-name match uses full ladder; recency window matches existing boundary; new risk source registered in `_SOURCE_VERSIONS`.
- **Audit (§Z)**: mutating admin route emits `AuditEventType` event; emit wrapped so failure can't cascade.

The point: don't pad — verify. If a grep returns hits, walk back to the rule and decide. If nothing matches, silence is fine.

### Common drift — phrases that mean "I'm about to silently demote"

If you find yourself writing one of these in the report, stop and re-flag at the source-rule severity:

- *"Inline SQL in the router is short, it's fine"* — §A is layer separation, not line-count.
- *"`await db.commit()` inside the service is fine, every service does it"* — read the call graph; two commits in one logical op breaks atomicity.
- *"`response_model` is optional"* — without it, response leaks future columns and Bruno contract drifts.
- *"The migration's `downgrade()` is empty, we'll never roll back"* — Constitution IV; "we won't" is not a deploy guarantee.
- *"Existing peer routers don't update Bruno / don't have tests / don't use `CamelCaseModel`"* — legacy state is not a convention for new code.
- *"It's only a small lookup dict, PG is overkill"* — past review rejected this for ISO codes; domain data lives in PG.
- *"Per-source table is clearer than a generic `risk_lists` table"* — past review rejected this; generic-with-source.
- *"JSON in the main table is fine, the shape is stable"* — stable shape is exactly when a side table beats JSON.
- *"`down_revision` was right when I cut the branch"* — and stale now; re-point at `origin/$BASE` head pre-merge.
- *"Just flip `ON CONFLICT DO UPDATE SET names = EXCLUDED.names`"* — destroys names from other sources; merge accumulative columns.
- *"`logger.info` on typeahead is one line"* — 6 keys × 50 users × 8h isn't. `debug`.
- *"State field written by parallel `Send` branches but test passes"* — test was lucky; without `Annotated[T, reducer]`, data drops silently.
- *"Sessions stay open during the step, dev pool is fine"* — dev is one user; prod isn't.
- *"Retry loop raises after N attempts, that's the spec"* — partial success is the spec when most rows succeeded; see `OrcidExhaustedError`.
- *"Audit emit fails the request, that's fine"* — audit never load-bears the request; wrap and log.
- *"The notification endpoint splits cursor across two fields — that's the precedent"* — was, until rejected; one opaque cursor.
- *"`LIMIT N+1` is a standard trick"* — team chose `len(rows) < limit`. Match.
- *"`nextCursor=null` on last page is fine"* — kills seek pagination's polling capability. Always echo.
- *"List bundles `unreadCount`, UI needs it"* — bundling is what's rejected. Split into `/count`.
- *"Service has 5 params, one more is fine"* — drift to 8 starts here; bundle.
- *"Two migrations on the branch are small"* — released history outlives the branch; squash before merge.

## 6. Output format

```
# be-code-review

**Branch:** <current> → **Base:** <base>
**Scope:** <working diff | branch diff> — <N> files
**Spec:** <specs/NNN-feature | (none)> · <Plan ✓/✗/–> · <Tasks ✓/✗/–> · <Contracts ✓/✗/–> · <Data-model ✓/✗/–>
**Tooling coverage:** <skipped categories, if any>
**Lint:** <clean | N issues | failed to run | n/a — no flake8>
**Types:** <clean | N issues | failed to run | n/a — no mypy>
**Bruno sync:** <ok | N missing | n/a — no router changes>
**Migration head:** <head-on-base> → <head-on-branch>; chain <✓ | ✗ stale down_revision | n/a>
**Verdict:** <ship | fix-before-ship | needs-rework>

## Blockers
- `path/to/file.py:42` — <one-line problem>. Fix: <one-line fix>.

## Suggestions
- `path/to/other.py:10` — <one-line problem>. Fix: <one-line fix>.

## Nits
- `path/to/yet.py:88` — <one-line problem>.

## Spec gaps
- (only if spec was detected and tasks.md / data-model.md / contracts diverge from the diff)

## Bruno sync
- (only if router changed)

## Migration sync
- (only if models changed)

## Package hygiene
- (only if pyproject.toml / uv.lock changed)

## Needs you
- (judgment-class findings the apply phase intentionally skips — listed verbatim from §7)

## One-time tip
- (optional, only when 3+ findings of one mechanical class)
```

**Spec sub-state legend** (each artifact gets one symbol):
- **✓** — the diff matches the artifact (FRs covered, contracts match, data-model.md reflects the migration, tasks.md entries touched).
- **✗** — the diff diverges (a contract in `contracts/*.yaml` doesn't match the new route; data-model.md describes a column the migration didn't add).
- **–** — not applicable (the diff is in a layer the artifact doesn't cover).

#### Severity-floor pre-emit check

Before printing the report, walk every drafted finding and confirm its severity is **at least** what the source rule states. If a rule says "Severity: **Blocker**" and the draft has it as Suggestion, restore Blocker (the calibration discipline in §2 — uncertainty is research, not silence).

Specifically:
- Auth bypass / missing `user_id` filter / `db.query(...)` / sync-in-async / missing migration / merge-conflict markers / hardcoded secrets / unmerged `ON CONFLICT` on accumulative columns / stale `down_revision` / heartbeat-missing on a NATS step / partial-completion-not-handled / agent reducer missing — these never demote.
- A "Suggestion" rule (named typed primitives, `TaskGroup` over `gather`, `freezegun` for time-sensitive tests) can be omitted entirely if it would produce noise, but not silently demoted to "Nit" to pad the count.

Rules:
- Group by severity, not file. **Blockers**: explicit-rule violations (auth bypass, sync function in async stack, missing migration, missing Bruno, sync DB call, hardcoded secret). **Suggestions**: idiomatic improvements (gather over sequential awaits, extract a literal union, hoist a helper). **Nits**: subjective polish.
- Each line includes `path:line` and a concrete fix.
- Omit categories with no findings.
- If everything is clean: one line — `**Verdict:** ship — no issues found in <N> files.`

## 7. Offer to apply

After the report (skip when verdict is `n/a` / `ship`), call `AskUserQuestion` with options: **All** (Mechanical + Structural; Judgment → `## Needs you`), **Blockers only**, **No**. Use `AskUserQuestion` for any other decision in the run too — never inline prose questions. If `AskUserQuestion` isn't loaded, fetch via `ToolSearch query: "select:AskUserQuestion"`.

### Categorize before applying

**Mechanical** (auto-apply, low risk): `Optional[X] → X | None`, `List[X] → list[X]`, `from typing import` cleanup, `datetime.utcnow() → datetime.now(timezone.utc)`, `print(...) → logger.info(...)`, f-string log → `extra={...}`, typeahead `info → debug`, hardcoded `204 → status.HTTP_204_NO_CONTENT`, missing `Annotated[…,Depends]`, missing `response_model`, redundant `Field(alias=...)`, `db.query(...) → select(...)` when shape is direct, Pydantic v1→v2 renames, `Field(default=[]) → default_factory=list`, conflict-marker removal when resolution is obvious.

**Structural** (apply with care): SQL from router → service, splitting a router, adding a missing `.bru`, generating a migration scaffold (no `--autogenerate`), wiring `get_<X>_service`, hoisting a Literal union, extracting a NATS subject builder, adding `selectinload`, re-pointing stale `down_revision`, switching `ON CONFLICT` to merge semantics, `pool_recycle`/`pool_pre_ping`, naming a constraint, adding `SET LOCAL lock_timeout`, `gather → TaskGroup`, bundling >4 params into a dataclass (single method, ≤5 call sites), `LIMIT N+1 → len(rows) < limit` (scoped to one service method), deleting a debug/report endpoint + its `.bru`, deleting a one-off `scripts/*.py`. Use `git mv` for moves; sweep importers with `git grep`.

**Judgment** (never auto-apply, → `## Needs you`): API redesigns on **shipped** endpoints, splitting a service, new layers, transaction-boundary changes, retrofitting tests, hardcoded-reference-dict → PG (new table + migration + service + callsites), per-source → generic `risk_lists`, JSON column → normalised side table, FK/xref backfills, LangGraph reducers/sync barriers/`RunnableConfig`, `AgentTaskMonitor` registration, long-step session refactors, new `_SOURCE_VERSIONS` tuples, new `AuditEventType` entries, audit emit in previously-unaudited code, squashing **already-deployed** migrations.

#### "API contract change" calibration — Structural when no shipped client depends on the old shape

The patterns below are normally Judgment because they break clients. They drop to **Structural** (auto-applicable) when **the endpoint is new in this same diff** — i.e. there is no shipped client to break:

- Multi-field cursor → opaque token.
- List endpoint → split into `/count` sibling (drop `unreadCount` / `totalCount` from list payload).
- `nextCursor=null` on last/empty → always-echo-last-row contract.
- Renaming a query/path param, switching response shape (`unread_count` → dedicated route), changing default values.

**Detection — endpoint-is-new heuristic**, run for the routers in the diff:

```bash
for r in $(git diff --find-renames --name-only "$MB"...HEAD -- 'src/routers/*.py'); do
  # If the router file itself is added in this diff, every route in it is new.
  git log --diff-filter=A --format= -- "$r" | grep -q . && echo "$r: ADDED in this diff (all routes new — contract changes are Structural)"
  # Else check if the @router lines were added on this branch.
  git blame "$r" 2>/dev/null | awk -v mb="$(git rev-parse --short=8 $MB)" '
    /@router\.(get|post|put|delete|patch)/ {
      if (substr($1,1,8) > mb || $0 !~ mb) print FILENAME": route on this branch — likely new"
    }
  '
done
```

Cleaner: if `git log --diff-filter=A --name-only $MB...HEAD` lists the router file, **all** of its routes are new in the diff — every contract change on that router is Structural. If only some routes are new (added inside an existing router), check `git blame` against `$MB` for the route decorator line.

**When you find an unshipped contract change in this same diff, apply it — don't punt to Judgment.** The user landing this branch is the first chance to ship the right shape; deferring it to a follow-up PR means re-doing the contract decision twice and adding a migration window for nothing.

Stays **Judgment** (still Needs you) when:
- The route exists on `origin/$BASE` (clients exist).
- Even if the route is new this diff, the change requires a UI- or worker-side decision the diff can't make alone (e.g. the count endpoint requires the UI to switch its polling target — flag the UI work as a follow-up but apply the API change).
- The diff is structurally entangled with an in-flight feature flag or rollout system.

**The 6 PR-comment patterns this calibration unblocks** (track by name; each reflects a real past-review):

| Pattern | Skill section | New default for new-in-diff endpoint |
| --- | --- | --- |
| Split cursor (`beforeX`+`beforeY`) → one opaque `cursor` | §B Cursor pagination | Structural |
| `LIMIT N+1` → `len(rows) < limit` | §B Cursor pagination | Structural |
| `nextCursor=null` on last/empty → always echo | §B Cursor pagination | Structural |
| List response bundles `unreadCount` / `totalCount` → split `/count` | §B One responsibility | Structural |
| `>4 params` or `≥2 optional defaults` → `@dataclass(frozen=True, slots=True)` bundle | §C Parameter object | Structural (always — internal change, no client impact) |
| Branch ships ≥ 2 migrations on same table → squash | §F.1 | Structural (always — pre-merge cleanup) |

### Apply phase

1. **Preview**: print proposed plan as `Mechanical (N)` / `Structural (M)` / `Skipping → Needs you (K)` with `path:line` + one-line each. Confirm via `AskUserQuestion`.
2. **Apply Mechanical first** (no dependency risk), then **Structural**. After each batch, run `uv run mypy <files>` + `uv run flake8 <files>`. If Mechanical breaks types, **stop** before Structural.
3. **Re-walk §5.5 spot-checks** against the new state; surface anything new under `## Surfaced after apply`.
4. **Summary line**: `Applied <N> fixes across <M> files. mypy: <pass/fail>. flake8: <pass/fail>. Bruno: <synced/N missing>.`

Constraints:
- Edit in place. **Never** `git add` / commit / push / stash / amend.
- **Never** `alembic upgrade/downgrade`, `uv sync/lock`, `pip install/uninstall`.
- Generating an Alembic revision file is OK on opt-in; **never** `--autogenerate` (misses indexes, server defaults, nullability).
- After Structural file moves / import rewrites, re-grep for stragglers.
- Bruno changes: verify file shape only — never "run" the request.
- **Comments discipline (apply-phase)** — default to writing **no** new comments when applying fixes. Only add one if **all** of these hold: the WHY is non-obvious, removing the comment would mislead a future reader, and the rationale isn't already captured by an identifier name, a typed signature, or a precedent the team has documented elsewhere (PR, constitution, past-review citation). Do **not** write "what"-comments that paraphrase the code, "rationale"-comments that explain the diff itself ("switched from N+1 to len < limit because…"), or breadcrumbs that point at the skill / past review. If a fix needs a multi-line explanation, that explanation belongs in the PR description, not the source. When in doubt: leave it out — the user can always ask for a comment if they want one.
- User picks **No** → end with: `Left untouched. Re-run /be-code-review to verify after fixes.`

## 8. Don't do

- Don't comment on style issues outside the diff.
- Don't suggest large refactors of unchanged code.
- Don't run formatters, linters, or migrations the user didn't ask for.
- Don't open a PR, commit, push, or stash — even after applying fixes.
- Don't run the live API or hit external services to "verify" — code review is read + reason, not a live test.
- Don't run `alembic upgrade` or any database-mutating command.
- Don't `uv sync` / `uv lock` / `pip install` / `pip uninstall` — dependency state is the user's call.

## Appendix A. Past-review precedents — citation pool

When a finding matches one of the patterns below, **cite the precedent in the finding line**: it converts "the skill says X" into "the team has rejected this in review N times". Quotes are paraphrased from prior PR comments on this repo.

| Pattern | Section | Precedent quote |
| --- | --- | --- |
| Hardcoded ISO/country dict in code | §T | *"Let's keep all info in one place — PG in our case. Just add iso2 column to table and add those to migration and drop hardcoded dictionary."* |
| `json.dumps(...)` blob in a generic config table | §F.4 | *"Flatten data — one row per country and no JSONs. Keep it in own table rather than config."* |
| Migration writing local report files / reading from `data/*.csv` | §F.4 | *"That's not for migration — just run script locally and attach results to Jira ticket for us to know which orgs require additional update."* |
| `ON CONFLICT DO UPDATE SET names = EXCLUDED.names` on accumulative column | §F.2 | *"need to merge names"* |
| Debug / report endpoint shipped in production routers | §B | *"No need in debug API — we will use it as one time execution result to ask for more data."* / *"Better not add debug APIs we do not have capacity to maintain these."* |
| One-off script in `scripts/` connecting to prod DB | §U | *"Should be just a one time run of local utility and report in Jira ticket — without local report files in production image."* |
| Stale `down_revision` after rebase | §F.1 | *"Latest revision in main now is j4k5l6m7n8o9."* |
| Per-source list table (`section1286_*`) instead of generic | §F.4 | *"Need a generic table name where list1286 is just one of the possible 'source' values so that we won't be adding new tables for every new 'risk' list."* |
| Free-text name reference instead of FK / xref | §T | *"We need more tight coupling with organizations here — a foreign key to org table or a xref table with that link."* |
| Org list missing rows for unmatched orgs | §T | *"For every 1286 org that is not present there yet — by name or any of alternative names — put a new entry in orgs."* |
| List of typed records as JSON column on main table | §T | *"This should be normalized in a separate table with separate fields rather than JSON in main table."* |
| Hardcoded business invariant nulled (`country_code: None` for SECTION_1286) | §F.2 | *"US — origin of SECTION_1286."* |
| Pagination by `name` with `offset` (or in-memory) | §B | *"Should be common limit/offset pattern for API pagination, supported by DB query."* / *"Will need to sort by a field that is not expected to get elements inserted inside sequence — like created_at this is constantly increasing value."* |
| `logger.info` on typeahead / per-keystroke | §I | *"debug loglevel."* |
| Static-data ingest via custom script connecting to prod | §U | *"We won't be able to run script by connecting e.g. to prod DB directly. So we have two options: either making this script a DB migration script and include all the rows in it, or make an API to create new rows."* |
| Merge conflict marker pushed in source | §S | *"Fix conflicts before merging."* |
| Schema omits known-extracted fields | §T | *"Please extract emails, links and summary from personal info extraction to API data model and lets merge it."* |
| Cursor split across two query params | §B (Cursor pagination) | *"You are already using cursor — use it everywhere instead of two fields."* |
| `LIMIT N+1` for last-page detection | §B (Cursor pagination) | *"Not correct — we do not need to read extra data. It's enough to check result.size < limit to understand it's the last page."* |
| `nextCursor=null` on last page / empty result | §B (Cursor pagination) | *"Cursor should always point to the last entry in resultset… If no results were loaded — cursor should be same we got in request."* |
| Hand-rolled re-implementation of framework primitive (lens) | §S (Hand-rolled vs primitive) | *"Seek pagination should be a single where `(id, time) > (queryId, queryTime)` — it covers duplicate time correctly."* (instance: OR/AND seek → `tuple_(...)` row-compare; same lens applies to `or_`-chains → `.in_()`, paired bounds → `.between()`, manual upserts → `ON CONFLICT`, etc.) |
| List endpoint bundles aggregate count | §B (One responsibility) | *"No need in unread to be called each execution. If we need to show count on UI there should be count endpoint with same filters returning only amount."* |
| Service method with too many positional/keyword params | §C (Parameter object) | *"Use objects with named fields for method to be more self-descriptive."* |
| Branch ships ≥ 2 migrations on the same table | §F.1 (Squash) | *"Collapse migrations into one."* |

When citing, quote the precedent in *italics* and tag the section: e.g. `(§F.2 precedent: "need to merge names")`.

If you encounter a new pattern in PR review that recurs, add it to this table — the appendix is meant to grow as the team accumulates standards.

## Appendix B. References

- Constitution authority order: `.specify/memory/constitution.md` → `CLAUDE.md` / `AGENTS.md` → this skill → idiomatic Python/FastAPI.
- Agent-internal review: `/agent-review` (deep review against `src/agents/AGENT_CONSTITUTION.md` and `LANGGRAPH_CONSTITUTION.md`).
- Speckit: `specs/<NNN>-<feature>/{spec,plan,tasks,data-model}.md`, `contracts/`.
