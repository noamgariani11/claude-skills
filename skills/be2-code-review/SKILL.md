---
name: be2-code-review
description: |
  Back-end code review for the ffrs-core-api Java/Spring Boot service. Auto-detects the active
  git branch, base branch, and the project's layered architecture (controllers / services /
  repositories / domain / dto / messaging / clients), then reviews the diff against
  controller/service separation, Spring Data JPA discipline, Liquibase migration hygiene,
  constructor injection, Lombok + Jakarta validation, structured Slf4j logging, Bruno collection
  sync, @Transactional proxy mechanics, Lombok/JPA entity safety, Spring Security/Keycloak,
  Jackson serialization, Redis caching, observability, transaction boundaries, N+1 queries,
  auth scoping, Java 25 idioms, dead code, duplication, AI-agent-introduced anti-patterns, and
  unused packages. After producing the report, the skill asks the user whether to apply the
  fixes; on confirmation it applies the mechanical and structural fixes in-place (never commits,
  pushes, stashes, or runs migrations).
  Use when asked to "be2 code review", "java review", "review my core-api changes", "review this branch",
  "check my diff", "/be2-code-review", or before opening a backend PR on ffrs-core-api.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - AskUserQuestion
---

# be2-code-review

You are a senior back-end reviewer for the ffrs-core-api Java 25 / Spring Boot service. Review **only the changed code** in the current diff, produce an actionable report, then ask the user whether to apply the fixes. Do not rewrite the world. Do not comment on code that did not change unless a change directly references it.

The repo's authority order (when rules conflict): `AGENTS.md` / `docs/code-guide.md` → this skill → idiomatic Java 25 / Spring Boot.

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
```

Scope: dirty tree → staged + unstaged + untracked. Clean tree → `MB=$(git merge-base "origin/$BASE" HEAD)`, use `$MB...HEAD`. Always pass `--find-renames`.

## 2. Read project conventions

Authority order: `AGENTS.md` / `docs/code-guide.md` → this skill → idiomatic Java 25 / Spring Boot.

Always read:
- `AGENTS.md` at root — mandates: Bruno sync per controller change, Spotless formatting, Lombok, constructor injection, `jakarta` annotations, `finch` config prefix, `com.finchai` base package, Java 25 syntax.
- `docs/code-guide.md` if present.
- `build.gradle.kts` (root + `app/`) — Spring Boot version, dep additions/removals.
- `app/src/main/resources/db/changelog/db.changelog-master.yaml` — Liquibase master file to check migration ordering.
- `bruno/ffrs-api/` — every controller prefix has a sub-folder; AGENTS.md mandates Bruno sync per controller change.

**Documented conventions** (AGENTS.md, code-guide.md) override skill rules. **Legacy state is not a convention** — old code using field injection / non-Lombok patterns is observed history; new code follows the rules.

**Tooling-aware skipping** — skip categories the project's tooling already covers:
- Spotless → skip cosmetic whitespace/brace style if `./gradlew spotlessApply` would fix it automatically. Still flag structural issues Spotless can't catch.
- Checkstyle / compiler warnings (if configured) → skip items they report.

Note skipped categories once at the report header.

Catalog existing surfaces before suggesting reuse:

```bash
find app/src/main/java -name "*Controller.java" | head -20
find app/src/main/java -name "*Service.java" | head -20
find app/src/main/java -name "*Repository.java" | head -20
find app/src/main/java/com/finchai/ffrs/core/common -type f | head -20
```

Known project surfaces: `FfrsPrincipal` (auth principal, injected as method param), `ServiceException` / `ErrorCode` hierarchy (domain exceptions), `RestExceptionHandler` (@RestControllerAdvice), `IdGenerator` / `TimeProvider` (injectable utilities), `AgentSubjects` (NATS subject builder), `AgentRpcClient` (agent messaging), `JetStream` (NATS), `CommonObjectMapper` (Jackson).

## 3. Short-circuit on irrelevant diffs

If every changed file matches the config glob — `*.kts`, `*.gradle`, `*.md`, `*.yml`, `*.yaml`, `.gitignore`, `Dockerfile*`, `*.properties`, `bruno/**/environments/*.bru` — emit one line and stop:

```
Verdict: n/a — diff is config/docs-only (<N> files). No BE rules apply.
```

If the diff is **bruno-only** (only `bruno/**/*.bru` outside environments), still review for: missing endpoint coverage, stale params, broken auth/url variables.

#### Fast path for trivial diffs

If the diff is small (≤ 3 files, ≤ 30 changed lines total) **and** every change is purely mechanical (import reorder, log level change, Lombok annotation swap, constant rename), skip the multi-section walk. Run only:
1. `./gradlew spotlessApply --dry-run` on changed files (or note if Spotless would change them).
2. Confirm no new auth/migration/controller/service files introduced.
3. Emit: `Fast path: <N> mechanical changes. Verdict: ship.`

If anything in the diff is **not** purely mechanical, drop the fast path and run the full §5 checklist.

## 4. Gather context

- List changed files with `--find-renames`.
- Read each changed file in full (imports, class-level annotations, surrounding methods).
- Deletions/renames: `git grep -n <OldName>` to confirm callers updated.
- Controllers: open matching `bruno/ffrs-api/<resource>/` folder; confirm Bruno sync.
- Domain entities: confirm matching Liquibase changeset in the diff (or already applied).

## 4.5. Run build checks on changed files only

```bash
MB=$(git merge-base "origin/$BASE" HEAD 2>/dev/null || git merge-base main HEAD)
CHANGED_JAVA=$(git diff --find-renames --name-only "$MB"...HEAD -- '*.java' \
  | xargs -I{} sh -c '[ -f "{}" ] && echo "{}"')

# Check Spotless would not flag formatting issues
./gradlew spotlessCheck 2>&1 | head -30

# Compile check (fail fast)
./gradlew compileJava compileTestJava 2>&1 | tail -20
```

Output handling:
- Clean → `Build: clean.` once.
- Spotless violations → `## Formatting` section with file paths; these are auto-fixable.
- Compile errors → verdict can't be `ship`.
- Build unavailable → note `Build: skipped — Gradle not reachable`, continue.

## 5. Checklist

Only flag real issues found in the changed code. Quote `path:line`. Do not pad with "looks good" notes — silence is praise.

### 30-second checklist (TL;DR)

| # | Surface | Check |
| --- | --- | --- |
| 1 | **Layers (§A)** | Controller, Service, Repository, Domain, DTO, Messaging — file in right package; no cross-layer back-imports. |
| 2 | **Controllers (§B)** | Thin: no SQL/repo calls; `FfrsPrincipal` for auth; `@Validated`; `@ResponseStatus`; matching Bruno; no debug endpoints; cursor pagination stable-sorted; `@Valid` on `@RequestBody`; nested DTOs have `@Valid`. |
| 3 | **Services (§C)** | `@Service` + `@Transactional`; `userId` filter on user-scoped reads; domain exceptions not `HttpStatus`; no `@Autowired` field injection; methods > 4 params → record/class param object; `@Transactional` only on `public` methods; no self-invocation; checked exceptions set `rollbackFor`. |
| 4 | **DTOs (§D)** | `@Value` (Lombok immutable) or `record` for responses; `@Nonnull`/`@Nullable`; camelCase JSON; no mutable state; Lombok entity safety (`@Data` / `@ToString` / `@EqualsAndHashCode` never on `@Entity`); Jackson `@JsonIgnoreProperties(ignoreUnknown=true)` on external-response DTOs. |
| 5 | **JPA / DB (§E)** | `@Transactional(readOnly=true)` on reads; `@EntityGraph` for eager-fetch on list endpoints; no N+1; bidirectional relationships maintained on both sides; `@Builder.Default` on entity collection fields; tz-aware `LocalDateTime`. |
| 6 | **Liquibase (§F)** | Never edit a deployed changeset; SQL changeset appended to master; `IF NOT EXISTS`; rollback block; NOT NULL with backfill; named constraints; correct ordering; `runOnChange` for views/procedures; timestamp-based IDs. |
| 7 | **Injection / config (§G–H)** | Constructor injection via `@RequiredArgsConstructor` + `final`; settings via `@ConfigurationProperties(prefix="finch")`; no `localhost` in non-test config. |
| 8 | **Logging (§I)** | `@Slf4j`; parameterised `log.info("msg {}", val)`; no `System.out.println`; `debug` for high-frequency paths. |
| 9 | **Clients (§J)** | Timeout set; singleton `OkHttpClient`; retry for idempotent reads; error mapped to domain exception; trace headers propagated. |
| 10 | **NATS (§K)** | Hierarchical subjects via `AgentSubjects`; JetStream for durable; ack/nak explicit; subject builders not inline strings. |
| 11 | **Auth + Security (§L)** | `FfrsPrincipal` injected; `userId` from principal not path param; mutating routes protected; `AuditLog` on sensitive actions; Keycloak role extractor registered; `@PreAuthorize` only on `public` methods; CSRF not blindly disabled. |
| 12 | **Types (§M)** | Java 25 idioms; `@Nonnull`/`@Nullable` on DTOs; no raw types; records not used as `@Entity`. |
| 13 | **Tests (§O)** | JUnit 5 + `@ExtendWith(MockitoExtension.class)`; no `@SpringBootTest` on unit tests; no `@Transactional` on integration tests; `usingRecursiveComparison()` for field-by-field asserts; no `@MockBean` inflation. |
| 14 | **Redis (§W)** | Jackson serializer (not Java native); TTL configured; no `@Cacheable` self-invocation; never cache security context. |
| 15 | **Observability (§X)** | `ContextPropagatingTaskDecorator` on `@Async` executors; OkHttp interceptor injects trace headers; no raw `new OkHttpClient()` for traced paths. |
| 16 | **Dead code (§S)** | No merge-conflict markers; no `TODO` without ticket; no commented-out code. |
| 17 | **Data modelling (§T)** | No hardcoded reference maps/lists; FK over free-text; normalised side tables over JSONB arrays; generic over per-source. |
| 18 | **AI patterns (§Y)** | No entities returned from controllers; no DTO mapper in loops without `@EntityGraph`; `findById().get()` → `orElseThrow`; `new ObjectMapper()` → injected bean. |

### A. Layered architecture — keep the layers honest

The project uses a **package-per-feature** structure with consistent sub-packages per feature:

```
app/src/main/java/com/finchai/ffrs/core/
  <feature>/
    <Feature>Controller.java        # HTTP only — request/response, validation, status codes
    <Feature>Service.java           # Business logic; testable without HTTP
    <Feature>Repository.java        # Spring Data JPA interface
    domain/                         # JPA entities (@Entity, @Table)
    dto/                            # Request/Response DTOs (Lombok @Value / records)
    messaging/                      # NATS publishers / event payloads
  common/
    exception/                      # ServiceException hierarchy + RestExceptionHandler
    security/                       # FfrsPrincipal, auth utilities
    generator/                      # IdGenerator, TimeProvider
```

Flag:
- A **controller** that imports a `Repository` and calls it directly → push to the matching service.
- A **service** that imports `HttpStatus`, `ResponseEntity`, or `@RestController` → services are HTTP-agnostic; throw `ServiceException` subclasses.
- A **service** that imports `HttpServletRequest` or Spring MVC types → same violation.
- A **DTO** placed in `domain/` instead of `dto/` — DTOs live in `dto/`, entities in `domain/`.
- A **new entity** (annotated `@Entity`) placed anywhere other than `<feature>/domain/`.
- **Cross-feature service calls going the wrong way**: a lower-level service importing a higher-level one. Dependencies flow: controllers → services → repositories/clients/messaging. Cross-feature: `common/` is always importable; peer features may call each other's services (not controllers, not repos directly).
- A **new utility class** under `common/` that is only used in one feature → belongs next to that feature, not in `common/`.

#### "Belongs to a service" heuristic

A method currently inline in a controller **belongs to service X** when it operates on X's domain entity, calls X's repository, or coordinates services X already coordinates. Cite the suggested file path.

### B. Controllers — pure HTTP boundary

Controllers handle: request parsing, constraint validation, calling the service, mapping to response DTO, throwing `NotFoundException`/`ConflictException` etc. based on service result. **Nothing else.**

Flag in controller code:
- **Direct repository call** (`@Autowired FooRepository` in a controller) → push to service.
- **Business logic inline** (`if/else` branching, data transformations, conditional decisions that aren't HTTP-error-mapping) → push to service.
- **`@Autowired` field injection** in a controller (or anywhere) → use constructor injection: `@RequiredArgsConstructor` + `final` fields. Severity: **Blocker** (AGENTS.md mandate).
- **Missing `@Validated`** on a controller that uses `@Min`/`@Max`/`@NotBlank` etc. on method parameters → validation silently skipped. Severity: **Blocker**.
- **Missing `@Valid`** on a `@RequestBody` parameter → all field-level constraints on the DTO are silently ignored. Severity: **Blocker**.
- **Nested DTO without `@Valid`** on the containing field — validation does not cascade into nested objects unless the field is annotated `@Valid`. Severity: **Blocker**.
- **`@Valid` vs `@Validated` on service methods** — `@Valid` on a `@RequestBody` throws `MethodArgumentNotValidException` (400). `@Validated` on a service-layer method throws `ConstraintViolationException`, which has no default 400 handler in Spring Boot and becomes HTTP 500 unless `RestExceptionHandler` handles it. Severity: **Blocker** for new `@Validated`-annotated service methods without a matching `@ExceptionHandler`.
- **Missing `@ResponseStatus`** on `POST` that creates (should be `HttpStatus.CREATED`), `DELETE` with no body (`HttpStatus.NO_CONTENT`), `PUT` with no body (`HttpStatus.NO_CONTENT`). Match existing style. Severity: **Suggestion**.
- **`HttpStatus` integer literals** (`@ResponseStatus(code=204)`) → use `HttpStatus.NO_CONTENT` constant. Severity: **Nit**.
- **User identification from path param** (`@PathVariable String userId`) instead of `FfrsPrincipal.getUserId()` → IDOR risk. Severity: **Blocker**.
- **Missing `FfrsPrincipal principal` param** on a route that handles user-scoped data → unscoped query. Severity: **Blocker**.

#### Debug / report / one-off admin endpoints

Routes named "debug", "report", "diagnostic", "dump", "one-time", "temporary" are rejected. Alternatives: local script + attach to Jira; existing list endpoint with filter param. **Blocker** (past-review precedent).

#### Pagination shape — DB-backed, stable sort

Two flavors:
- **`limit` + `offset`** — low-cardinality lists.
- **Cursor pagination** — high-volume / "load-newer" UIs.

In both: DB executes pagination (`Pageable` with `PageRequest.of(0, limit)` for cursor, native query `LIMIT/OFFSET` for offset), not in-memory slicing. Sort by non-shifting column (`created_at`, `id`, ULID) with a stable tie-breaker.

Flag: in-memory `List.subList(...)` after loading all rows; no pagination on list that can exceed ~50 rows; sort by user-mutable field.

#### Cursor pagination contract (seek/keyset)

1. **One opaque `cursor` query param** — not separate fields. `NotificationCursor.decode(cursor)` + `NotificationCursor.encode()` is the existing pattern — follow it.
2. **Last-page detection via `items.size() < limit`** — not `LIMIT N+1`. Same cost, one fewer DB row.
3. **`nextCursor` always points at the last returned row** — even on the last page. On empty result, echo the request cursor (never `null`). Without this, seek-pagination polling breaks silently. **Blocker**.

Native query row-value seek (the project's precedent from `NotificationRepository`):
```sql
AND (created_at, id) < (:cursorCreatedAt, :cursorId)
```
Not two separate `WHERE` predicates. Lets Postgres use a composite index as one range scan.

#### One responsibility per endpoint — counts in their own routes

`GET /resource` → `{ items, nextCursor }`. Counts live in `GET /resource/count` with the same filter params. The project already does this (`/notifications` + `/notifications/count`). Flag a list response that bundles `totalCount`/`unreadCount`/`hasMore` (beyond `nextCursor`). **Suggestion**; **Blocker** if the count dominates list latency.

#### Bruno collection sync (AGENTS.md mandate, Blocker)

For each changed controller, list `bruno/ffrs-api/<resource>/` and confirm a `.bru` file for every `@GetMapping`/`@PostMapping` etc. Flag: new route → no `.bru`; path change → stale `.bru`; new query/path/body param → no matching param in `.bru`; removed route → orphan `.bru`. Name the expected file path in each finding.

### C. Services — transactional, DI-injected, domain-exception-aware

Services hold deps via constructor, annotated `@Service`, use `@Transactional` / `@Transactional(readOnly=true)`.

- **`@Autowired` field injection** → `@RequiredArgsConstructor` + `final`. Severity: **Blocker**.
- **Missing `@Transactional`** on a method that writes to the DB (multiple saves, delete + create) → operations not atomic. Severity: **Blocker**.
- **Missing `@Transactional(readOnly=true)`** on a read-only service method. Severity: **Suggestion**.
- **`HttpStatus`, `ResponseEntity`, `@ResponseStatus`** imported in a service → throw `ServiceException` subclasses instead. Severity: **Blocker**.
- **`new` constructing another Spring bean** → defeats the container. Severity: **Blocker**.
- **Missing `userId` / `orgId` filter** on a user-scoped read — cross-tenant data leak. Severity: **Blocker**.
- **`repository.findById(id)` without checking `orgId`** when the entity is org-scoped → IDOR. Severity: **Blocker**.
- **`repository.findById(id).get()` without `orElseThrow`** → throws `NoSuchElementException` (HTTP 500) instead of the project's `NotFoundException` (HTTP 404). Extremely common AI-generated pattern. Severity: **Blocker**.
- **`TransactionSynchronizationManager.registerSynchronization`** for after-commit side effects — the project's correct pattern (see `NotificationService.publishAfterCommit`). Flag any publisher call placed directly inside a `@Transactional` method without `afterCommit()` registration when the operation is commit-dependent.
- **`Optional.get()` without `isPresent()` check** → same as above. Use `.orElse(null)`, `.orElseThrow(...)`, or `ifPresent(...)`. Severity: **Blocker**.
- **`save()` + separate `findById()` to re-read** → use `save()` return value or `@EntityGraph` on the initial load. Severity: **Suggestion**.

#### Parameter-object threshold

Bundle into a record or class when **any** is true:
- > 4 params (excluding the service bean itself; `userId`/`orgId` count as 1 each).
- 2+ optional params with defaults.
- Same param group recurs across 2+ methods.

Don't bundle: ≤ 4 clearly-named scalars.

**Suggestion**. Past-review precedent: *"Use objects with named fields for method to be more self-descriptive."*

#### @Transactional proxy mechanics — silent failure modes

Spring AOP uses CGLIB proxies. Several common patterns silently no-op the `@Transactional` annotation, causing data corruption without any error:

- **`@Transactional` on a `private` / `protected` / package-private method** — proxy cannot intercept it; annotation is completely ignored. No error at runtime, no warning. Severity: **Blocker**.
- **Self-invocation: `this.someTransactionalMethod()`** — the call goes directly to the concrete object, bypassing the proxy. The called method runs without a transaction even if annotated. AI agents reproduce this frequently by splitting one transactional method into private helpers. Fix: extract to a separate `@Component` / `@Service` bean and inject it, so the call travels through the proxy. Severity: **Blocker**.
- **Checked exceptions don't trigger rollback by default** — only `RuntimeException` and `Error` cause rollback. A method that throws or rethrows a checked exception will commit the partial write. Fix: `@Transactional(rollbackFor = Exception.class)` when needed, or wrap in a runtime exception. Severity: **Blocker** when checked exceptions cross a service boundary.
- **Swallowing the exception inside `@Transactional`** — a bare `catch (Exception e) { log.error(...); }` means Spring never sees the exception; the transaction commits with partial data. Fix: re-throw after logging, or call `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()`. Severity: **Blocker**.
- **`@Transactional` on `@PostConstruct`** — the proxy chain is not yet wired during bean initialization; the annotation is ignored. Fix: move post-init DB work to an `ApplicationReadyEvent` listener. Severity: **Suggestion**.
- **`@Transactional` method calling external HTTP client / NATS RPC** — holds a DB connection for the entire duration of the remote call. Under load this exhausts the connection pool. Fix: close the transaction before the remote call; reopen if needed afterward. Severity: **Blocker** (see §E).

### D. DTOs — immutable, annotated, camelCase JSON

The project uses Lombok `@Value` (immutable) for response DTOs and `record` for simple value objects. Jackson serialises field names as camelCase by default.

Flag:
- **Mutable DTO** (`@Data` instead of `@Value` for a response type that never mutates) → prefer `@Value` or a Java `record`. Severity: **Suggestion**.
- **Missing `@Nonnull` / `@Nullable`** on DTO fields — AGENTS.md mandates these on all DTOs. Severity: **Suggestion** for existing; **Blocker** for new DTOs without any nullability annotations.
- **Manual getter/setter in a DTO** instead of Lombok annotation → boilerplate, misses the pattern. Severity: **Suggestion**.
- **DTO extending `@Entity`** or having `@Column` / `@Table` — DTOs and entities are separate. Severity: **Blocker**.
- **`@JsonProperty` hardcoding a camelCase alias** that Jackson would derive automatically → redundant. Remove. Severity: **Nit**.
- **`@JsonProperty` with a snake_case alias** on a field in a new DTO — the API contract uses camelCase; only override when an existing endpoint already uses snake_case. Severity: **Suggestion**.
- **Primitive `int`/`long`/`boolean` in a DTO** where `null` is a valid API signal → use boxed type. Severity: **Suggestion**.

#### Lombok + JPA entity safety

These Lombok mistakes on `@Entity` classes are the highest-frequency correctness bugs in the codebase, and the ones AI coding agents reproduce most often:

- **`@Data` on a `@Entity`** — generates `equals()` and `hashCode()` using all fields including `id`. Before persist, `id` is `null`; after persist, `id` is set. The hash code changes mid-session, silently corrupting `HashSet` / `HashMap` lookups. This is a well-known Hibernate correctness bug. Severity: **Blocker**. Fix: never use `@Data` on `@Entity`. Use `@Getter @Setter @ToString` separately and implement `equals`/`hashCode` on a stable natural key (business key or UUID-based `instanceof` check as recommended by Hibernate).
- **`@EqualsAndHashCode` traversing bidirectional relationships → infinite recursion / stack overflow** — default Lombok `equals()` on entity A calls B's `equals()`, which calls A's, and so on. Fix: `@EqualsAndHashCode(onlyExplicitlyIncluded = true)` with `@EqualsAndHashCode.Include` only on the stable business key. Severity: **Blocker**.
- **`@ToString` on lazy collections → accidental N+1 load or `LazyInitializationException`** — `toString()` touches all fields. `log.debug("{}", entity)` inside a transaction fires unintended SQL; outside a transaction throws. Fix: always `@ToString.Exclude` on every `@OneToMany` / `@ManyToMany` field. Severity: **Blocker**.
- **`@Builder` on JPA entities without `@Builder.Default`** — `@Builder` bypasses field initializers (e.g. `= new ArrayList<>()`). Collection fields are `null` instead of empty; Hibernate cascade operations then NPE. Fix: add `@Builder.Default` on every field that needs initialization, or avoid `@Builder` on entities entirely. Severity: **Blocker**.
- **`@Value` used for a DTO that must be deserialized by Jackson** — `@Value` marks the class `final` and generates an all-args constructor. Jackson cannot deserialize without `@JsonCreator` / `@ConstructorProperties` or the `jackson-module-parameter-names` module. Severity: **Blocker** for request-body DTOs. Fix: use Java `record` (Jackson 2.12+ handles records natively), or add `@JsonCreator` + `@JsonProperty` on constructor parameters.
- **`@RequiredArgsConstructor` with `@Autowired` field injection mixed in the same class** — `@RequiredArgsConstructor` only generates a constructor for `private final` fields. Any field without `final` is not injected via constructor, leaving it `null`. Fix: make all injected fields `private final`. Severity: **Blocker**.

#### Jackson serialization

- **`@JsonIgnore` on a field vs on a getter behaves differently** — on a private field: ignored for both serialization and deserialization. On a getter: ignored only for serialization (field can still be written during deserialization). Behavior also diverged in Jackson 2.14. Fix: use `@JsonProperty(access = JsonProperty.Access.READ_ONLY)` or `WRITE_ONLY` for explicit directional control. Severity: **Suggestion**.
- **`@JsonIgnoreProperties(ignoreUnknown = false)` (the strict default) on external-API response DTOs** — when a downstream service adds a new field, Jackson throws `UnrecognizedPropertyException` and the caller fails completely. Fix: annotate all DTOs that represent external API responses with `@JsonIgnoreProperties(ignoreUnknown = true)`, or configure the global `ObjectMapper` bean with `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES = false`. Severity: **Blocker** for new external-response DTOs.
- **`new ObjectMapper()` inside a method** — expensive to construct, creates a new instance with none of Spring's auto-configuration (`JavaTimeModule` absent, custom serializers absent, feature flags absent). Very high-frequency AI agent mistake. Fix: inject the auto-configured `ObjectMapper` bean (or the project's `CommonObjectMapper`). Severity: **Blocker**.
- **`LocalDateTime` / `ZonedDateTime` serialized as numeric array by default** — Jackson without `JavaTimeModule` or `write-dates-as-timestamps=false` outputs `[2024,6,15,10,30,0]` instead of ISO-8601 strings. Fix: confirm `spring.jackson.serialization.write-dates-as-timestamps=false` is set and `JavaTimeModule` is registered. Severity: **Suggestion** for new date fields on response DTOs.
- **`@JsonCreator` missing on immutable classes / records with multiple constructors** — when more than one constructor is present, Jackson throws `InvalidDefinitionException` because it cannot determine which to use for deserialization. Fix: annotate the target constructor with `@JsonCreator` and each parameter with `@JsonProperty("fieldName")`. Severity: **Blocker** for request-body records/value classes.

### E. Spring Data JPA — transactions, N+1, tz-aware datetimes

The project uses Hibernate + PostgreSQL. Patterns to enforce:

- **`@Transactional` on the repository method** when the service method also has `@Transactional` → double-transaction nesting is usually harmless but signals confusion about where the boundary is. Flag only when it changes propagation semantics. Severity: **Nit**.
- **N+1 queries**. Any `@OneToMany` / `@ManyToMany` relationship accessed in a loop where the parent was loaded without `@EntityGraph` or `JOIN FETCH` is N+1. Look for:
  ```java
  List<Workflow> workflows = workflowRepository.findAll(...);
  for (var w : workflows) {
      w.getSteps().size();  // ← lazy fetch per-row → N+1
  }
  ```
  Suggest `@EntityGraph(attributePaths="steps")` on the repository query. Severity: **Blocker** for new list endpoints.
- **`FetchType.EAGER` on a `@OneToMany`** → loads the collection unconditionally; use `FetchType.LAZY` + `@EntityGraph` on queries that need it. Severity: **Suggestion**.
- **Bidirectional relationship not maintained on both sides** — setting only one side of a `@OneToMany`/`@ManyToOne` pair leaves the in-memory graph inconsistent within the same session. Hibernate uses the owning side for SQL; the other side looks empty until the next `find`. Fix: always use a helper method that sets both sides. Severity: **Suggestion**.
- **`LazyInitializationException` outside transaction** — accessing a lazy relationship after the transaction closes. Common when entities are mapped to DTOs in a controller outside the service transaction. Fix: load all required data within the service transaction boundary; use DTOs/projections that don't carry Hibernate-managed proxies. Severity: **Blocker** when it propagates to production.
- **`LocalDateTime` without timezone** for fields that store user-facing timestamps → prefer `Instant` or document the assumed TZ. The project uses `LocalDateTime` — match the existing convention but flag new `timestamptz` DB columns mapped to `LocalDateTime` without documentation. Severity: **Suggestion**.
- **`native=true` query with SQL string concatenation** (`"WHERE id = " + id`) → SQL injection. Use `@Param`. Severity: **Blocker**.
- **`entityManager.createNativeQuery(...)` with string concatenation** → same Blocker.
- **`findAll()` without pagination** on an entity that can grow unboundedly → OOM / slow query. Severity: **Blocker** for new endpoints; **Suggestion** for existing.
- **`save()` in a loop for bulk insert** → use `saveAll(List<...>)` for ≥ 5 entities. Severity: **Suggestion**.
- **`save()` on a detached entity when intent is update** — if the entity was not loaded from the DB in the current session and the `id` was set manually, Hibernate may issue an `INSERT` instead of `UPDATE` depending on the `isNew()` strategy. Fix: always load with `findById()` before mutating, or use `saveAndFlush` with proper version/id handling. Severity: **Suggestion**.

#### JPA entity patterns

- **No `@Column(nullable=false)` on required fields** → Hibernate won't enforce at DDL time; flag alongside a missing `@Nonnull` annotation. Severity: **Suggestion**.
- **`@Column(updatable=false)` missing on `createdAt` / `id`** — the project sets this consistently; new entities must too. Severity: **Suggestion**.
- **`@GeneratedValue`** vs manual `IdGenerator.generate()` — the project uses manual ID generation; don't mix `@GeneratedValue(strategy=IDENTITY)` for UUID PKs. Severity: **Suggestion**.
- **`CascadeType.ALL`** on a relationship where `REMOVE` would silently delete children — review intent; `CascadeType.PERSIST, MERGE` is usually safer. Severity: **Suggestion**.

#### Connection pool and session hygiene

- **Long-held transactions** — a `@Transactional` service method that calls an external HTTP client / NATS RPC / `Thread.sleep()` holds a DB connection for the entire duration. Under load this exhausts the pool. Flag: any `@Transactional` method that calls `agentRpcClient`, `jetStream`, or any Retrofit/OkHttp client. Severity: **Blocker**.
- **Session-per-request is the default** — don't open a second `EntityManager` / `Session` inside a `@Transactional` method. Severity: **Blocker**.

#### Bulk operations

- **`save()` in a loop** vs `saveAll(list)` for ≥ 5 rows — `saveAll` issues fewer flushes and is cleaner. Severity: **Suggestion**.
- **`findAll()` materializing large result sets** — always pair with a `Pageable` parameter or a `Specification`-based bounded query. Severity: **Blocker** for new endpoints.

### F. Liquibase migrations — ordered, reversible, production-safe

The project uses Liquibase SQL changesets appended to `db/changelog/db.changelog-master.yaml`.

For each new changeset file in the diff:

- **Editing an already-applied changeset** — Liquibase stores a checksum in `DATABASECHANGELOG`. Modifying any applied changeset causes a `ValidationFailedException` checksum mismatch and the app fails to start. **This is the #1 Liquibase production failure mode.** Severity: **Blocker**. Fix: always add a new changeset to correct a previous one; never modify deployed ones. Check via: `git log --follow -- <changeset-file>` — if it appears on `origin/$BASE`, it's deployed.
- **Not listed in `db.changelog-master.yaml`** → migration will never run. Severity: **Blocker**.
- **Listed out of order** (higher number inserted before lower) → unpredictable execution. Severity: **Blocker**.
- **No `-- rollback` block** (or SQL-format rollback comment) when the change is reversible (table/column/index add) → every schema change should be reversible. Severity: **Blocker**.
- **No `IF NOT EXISTS`** on `CREATE TABLE` / `CREATE INDEX` — changesets must be rerunnable safely after partial failure. Severity: **Blocker**.
- **`NOT NULL` column added to a populated table without `DEFAULT` or backfill** → migration fails on prod data. Must either use `DEFAULT <val>` or an `UPDATE` backfill step before removing `DEFAULT`. Severity: **Blocker**.
- **Column type change** without explicit cast (e.g. `VARCHAR → UUID`) → likely broken on production data. Severity: **Blocker**.
- **Rename via `DROP COLUMN` + `ADD COLUMN`** instead of `ALTER TABLE … RENAME COLUMN` → loses data. Severity: **Blocker**.
- **`CREATE INDEX` (non-concurrent) on a large table** → `ACCESS EXCLUSIVE` lock; production outage. Use `CREATE INDEX CONCURRENTLY`. Severity: **Blocker** on hot tables.
- **`ALTER TABLE … ALTER COLUMN` on a large table** without `LOCK_TIMEOUT` → same outage risk. Severity: **Blocker** on hot tables.
- **Un-named constraints** (`CHECK`, `UNIQUE`, `FOREIGN KEY`) → auto-generated names are hard to drop later. Always name them: `CONSTRAINT ck_<table>_<rule> CHECK (...)`. Severity: **Suggestion**.
- **Seed rows without `ON CONFLICT DO NOTHING`** → fails on re-run. Severity: **Blocker**.
- **Two changesets on the same branch modifying the same table** → squash before merge. Severity: **Suggestion**; **Blocker** at 4+ changesets.
- **`runOnChange: true` missing on stored procedures / views / functions** — after initial apply, Liquibase ignores all subsequent changes to the file. Severity: **Blocker** for any changeset containing `CREATE OR REPLACE` DDL. Fix: add `runOnChange: true` to the changeset header.
- **Changeset IDs using sequential integers** in a multi-developer team — two developers creating changesets on different branches get ID collisions. Severity: **Suggestion**. Fix: use timestamp-based IDs (`20240615-1`) or `author-timestamp` format to make IDs globally unique.
- **Environment-specific data (seed/fixture) without `context` guard** — dev or test seed data will run in production. Severity: **Blocker** for any changeset that inserts rows only appropriate for non-prod environments. Fix: add `context: "dev,test"` to the changeset.

#### Production-safety checklist

For `ALTER TABLE` / `CREATE INDEX` / bulk `UPDATE` on a table with > ~50k rows:
- Set `LOCK_TIMEOUT '5s'` before DDL: `SET LOCAL lock_timeout = '5s';`
- `CREATE INDEX CONCURRENTLY` (cannot run inside a Liquibase transaction block — use `runInTransaction="false"` in the changeset).
- `SET LOCAL statement_timeout` before long DML.

#### Data modelling in migrations (Blocker on violation)

1. **Generic over per-source** — one `risk_lists` table with a `source` column; not `section1286_*`, `ofac_*`, etc.
2. **FK / xref over free-text** — cross-entity references use FK or xref table.
3. **Normalised side tables over JSONB arrays** — when a JSONB column holds typed structured records (not opaque payloads), normalise to a side table.

Cite Appendix A on every violation.

### G. Spring dependency injection

The project uses constructor injection exclusively.

Flag:
- **`@Autowired` on a field** instead of constructor injection → defeats `final` guarantees, harder to test. Severity: **Blocker** (AGENTS.md mandate).
- **`@Autowired` on a setter** → same violation.
- **`@Autowired` absent on a constructor in a class with multiple constructors** without `@RequiredArgsConstructor` → Spring may call the wrong constructor. Severity: **Blocker**.
- **Spring bean constructed with `new`** inside another bean — defeats DI; inject via constructor. Severity: **Blocker**.
- **`ApplicationContext.getBean(...)` inside business code** → Service Locator anti-pattern. Severity: **Blocker**.
- **`@Lazy` without justification** — usually a circular-dep smell. Flag and suggest resolving the cycle. Severity: **Suggestion**.

### H. Configuration & secrets

AGENTS.md: use `@ConfigurationProperties(prefix="finch")` for all application config.

Flag:
- **Hardcoded URLs** (`http://localhost:8080`, `https://api.elsevier.com`) in source — use `@ConfigurationProperties`. Severity: **Blocker**.
- **`localhost` in non-test configuration** — works locally, fails in every other environment. Severity: **Blocker**.
- **Hardcoded secrets** (API keys, JWT secrets, passwords) in source. Severity: **Blocker**.
- **`@Value("${some.property}")` for a group of related properties** when a `@ConfigurationProperties` class would be cleaner. Severity: **Suggestion**.
- **`System.getenv(...)` inside service code** → use `@ConfigurationProperties`. Severity: **Blocker**.
- **`@ConfigurationProperties` without `prefix="finch"`** — AGENTS.md mandate. Severity: **Suggestion** for existing; **Blocker** for new.
- **New config property without a default in `application.properties`/`application.yml`** and without documentation → will break on deploy if the var isn't set. Severity: **Suggestion**.

### I. Logging — structured, Slf4j, correct levels

AGENTS.md mandates `@Slf4j` + structured logging.

Flag:
- **`System.out.println(...)` / `System.err.println(...)`** anywhere in `src/main/` → replace with `log.info(...)`. Severity: **Blocker**.
- **`new Logger(...)` / `LogManager.getLogger(...)`** directly instead of `@Slf4j` annotation. Severity: **Blocker** (AGENTS.md).
- **`log.info("Created entity " + entity.getId())`** (string concatenation or interpolation) → use parameterised form: `log.info("Created entity id={}", entity.getId())`. Severity: **Suggestion**.
- **`log.error(e.getMessage())`** in a `catch` block → `log.error("Operation failed", e)` — includes the stack trace. Severity: **Suggestion**.
- **Sensitive data in logs**: raw tokens, passwords, full JWT payloads, plaintext credentials. Severity: **Blocker**.
- **`log.info` on high-frequency paths** — typeahead/autocomplete endpoints, per-item inside batch loops, polling paths — use `log.debug`. Severity: **Suggestion**.
- **`log.toString()` on a JPA entity inside a transaction** — if the entity has `@ToString` on lazy fields, this fires unintended SQL. Severity: **Blocker** (see §D Lombok).

#### Log level discipline

- `ERROR` — actionable; needs human response.
- `WARN` — degraded but continuing.
- `INFO` — lifecycle events (entity created, workflow started/finished, subscription bound, app start).
- `DEBUG` — development only; not in prod hot paths.

Flag `log.info(...)` on: typeahead endpoints, per-item batch iterations, NATS keep-alives, polling endpoints.

### J. External clients — timeouts, retries, error mapping

The project uses Retrofit2 + OkHttp3 for HTTP clients. New external HTTP calls belong in dedicated client classes.

Flag:
- **`OkHttpClient` constructed per-request / per-method** — creates a new connection pool every time, exhausting file descriptors and threads rapidly under load. Fix: create exactly one `OkHttpClient` as a Spring `@Bean` and share it across all Retrofit instances. Severity: **Blocker**.
- **No `connectTimeout` / `readTimeout` / `writeTimeout`** on a new `OkHttpClient.Builder` → hangs in production. Severity: **Blocker**.
- **No retry policy** on idempotent reads from a flaky upstream → at minimum implement a simple retry with backoff. Severity: **Suggestion**.
- **Retrofit error body not mapped to a domain exception** — services should receive `NotFoundException` / `ExternalServiceException`, not `retrofit2.HttpException`. Map in the client layer. Severity: **Suggestion**.
- **`Call.execute()` (synchronous Retrofit)** inside a Spring MVC request thread — blocks a Tomcat/Undertow thread. Use `Call.enqueue(...)` or a dedicated executor for non-blocking flow. Severity: **Blocker** if the upstream is slow.
- **`ResponseBody` not closed** — when using raw `Call<ResponseBody>`, the body must be explicitly closed. Forgetting `.close()` leaks the underlying HTTP connection (OkHttp logs "A connection to X was leaked"). Fix: try-with-resources on `ResponseBody`, or use Retrofit's built-in Jackson converter which handles body consumption automatically. Severity: **Suggestion**.
- **Retrofit interface method without HTTP verb annotation** — a method missing `@GET` / `@POST` etc. compiles without error but throws `IllegalArgumentException` at runtime on first call. Fix: ensure every interface method has exactly one HTTP method annotation; add a smoke test. Severity: **Blocker**.
- **No trace header propagation in OkHttp interceptors** — manually constructed `OkHttpClient` instances bypass Micrometer's auto-instrumentation and don't propagate `traceparent` / `tracestate` headers. Downstream services receive requests outside the trace. Fix: add a custom `Interceptor` that reads the current `Span` context and injects W3C headers (see §X). Severity: **Suggestion** for internal service calls; **Blocker** for cross-service tracing.

### K. NATS messaging

The project uses NATS JetStream for durable events and core NATS for browser-inbox messages.

Flag:
- **Inline subject construction** (`"user." + userId + ".notifications"`) in 2+ places → `AgentSubjects`-style utility class or string constant. Severity: **Suggestion**. Precedent: `NotificationEventPublisher.SUBJECT_PATTERN` as a constant, `AgentSubjects` as a utility class.
- **`jetStream.publish(...)` to a browser inbox `_INBOX.*` subject** → will fail silently for browser subscribers (use `connection.publish(...)` for core NATS). Severity: **Blocker**.
- **`connection.publish(...)` for workflow lifecycle events** that need durability → use `jetStream.publish(...)`. Severity: **Blocker**.
- **No `try/catch` around `jetStream.publish(...)`** in a `@Transactional` service method → a publish failure rolls back the DB transaction. Always catch and log publish failures separately. Severity: **Suggestion**.
- **Payload size check missing** — the project has `maxPublishBytes` check in `NotificationEventPublisher`; new publishers should follow the same pattern. Severity: **Suggestion**.
- **NATS listener without ack/nak** (where applicable) → message redelivery storm. Severity: **Blocker**.
- **NATS subject that doesn't use the `user.{userId}.*` hierarchy** for user-scoped events — prevents per-user filtering and enables cross-tenant leaks. Severity: **Blocker**.
- **Pull consumer without `durable` name** — creating a pull-subscribe consumer without `.durable("name")` in the consumer configuration throws a server error. AI agents unfamiliar with JetStream generate this pattern frequently. Severity: **Blocker**.
- **Subject filter mismatch between stream and consumer** — if the consumer's `filterSubject` doesn't match any subject covered by the stream, the server returns error `90011`. Often a silent startup failure if not validated. Fix: ensure the stream's `subjects` list covers the consumer's `filterSubject`. Severity: **Blocker**.
- **Missing `msg.inProgress()` on long-running handlers** — if processing exceeds `ackWait`, JetStream redelivers the message while it is still being processed, causing duplicate processing. Fix: call `msg.inProgress()` (working/ping) periodically for processing > 30s. Severity: **Blocker** for orchestration-tier handlers.
- **`consumerInfo()` called in a hot path** — `jsm.consumerInfo(stream, consumer)` per-message adds significant overhead. Severity: **Suggestion**. Fix: cache consumer info and refresh on errors.
- **Connection disruption not handled in fetch loops** — during NATS reconnect, pending `fetch()` loops stall silently. Without error handling and retry around `fetch()`, consumers stop receiving messages after any network blip. Fix: wrap fetch loops in `try/catch` for `IOException` / `JetStreamApiException` and re-establish the subscription on connection events. Severity: **Suggestion**.

### L. Auth, permissions, and audit

Auth is Keycloak via Spring Security OAuth2 Resource Server; user surfaces as `FfrsPrincipal`.

Flag — all **Blocker** unless noted:
- **New mutating route (POST/PUT/DELETE/PATCH) that doesn't receive `FfrsPrincipal`** → unauth public mutation.
- **User data query without `userId` / `orgId` filter** → cross-tenant data leak.
- **Path or query param used to identify the current user** (`/users/{userId}/data`) instead of `principal.getUserId()` → IDOR.
- **`principal.getUserId().toString()` vs `principal.getUserId()`** — note which type (`String` vs `UUID`) the repository expects; flag type mismatch that requires `.toString()` where the repo accepts `UUID` directly.
- **Logging `Authorization` headers or raw JWT tokens** in plaintext. Severity: **Blocker**.
- **Admin action without `AuditLog` record** — Severity: **Suggestion** for self-service; **Blocker** for admin actions on other users' data.

#### Spring Security / Keycloak

- **Keycloak roles not extracted → all `@PreAuthorize` checks silently return false** — Spring Security's default `JwtAuthenticationConverter` does not know Keycloak's `realm_access.roles` / `resource_access.{client}.roles` structure. Every role-based check fails silently (no error, just `AccessDeniedException`). Fix: register a custom `JwtAuthenticationConverter` bean that reads `realm_access.roles` and prefixes them with `ROLE_`. Severity: **Blocker** if any `@PreAuthorize` annotation exists in the diff.
- **Issuer URI mismatch → 401 on every request** — `spring.security.oauth2.resourceserver.jwt.issuer-uri` is compared character-for-character against the `iss` claim in tokens. A trailing slash, `http` vs `https`, or wrong realm name causes silent 401s that are hard to diagnose. Fix: decode a real token with jwt.io, copy the exact `iss` value. Severity: **Blocker** when the diff touches security configuration.
- **`@PreAuthorize` on a `private` method** — same AOP proxy root cause as `@Transactional` on private methods: no authorization is applied. Severity: **Blocker**. Fix: only annotate `public` methods.
- **`.csrf(csrf -> csrf.disable())` without confirming stateless JWT auth** — disabling CSRF is appropriate for pure JWT resource servers, but dangerous if any endpoint uses session cookies. AI agents always disable CSRF by default. Severity: **Blocker** if any session/cookie-based auth is present; **Suggestion** otherwise — add an inline comment confirming the JWT-only reason.
- **Custom `SecurityFilterChain` filter added at wrong position** — adding a filter with `http.addFilter(new MyFilter())` places it at the wrong point in the chain. If the filter depends on the security context being populated, it may run before authentication. Fix: use `addFilterBefore`, `addFilterAfter`, or `addFilterAt` with an explicit anchor class. Severity: **Suggestion**.

### M. Java 25 idioms and type safety

AGENTS.md: use Java 25 syntax. The project already uses `var`, switch expressions, text blocks, records, and pattern matching.

Flag newly-added:
- **`instanceof` check followed by manual cast** — use pattern matching: `if (obj instanceof Foo foo) { foo.method(); }`.
- **Multi-branch `if/else` on enum values** → switch expression with arms.
- **`Optional.isPresent()` + `Optional.get()`** → `Optional.map(...)`, `Optional.ifPresent(...)`, or `Optional.orElseThrow(...)`.
- **Raw type usage** (`List list = new ArrayList()` without generics). Severity: **Blocker**.
- **`var` used where the type is non-obvious** → use explicit type for clarity. Severity: **Nit**.
- **Checked exceptions declared in method signature** that the method body never throws (AGENTS.md: "Do not throw exceptions in method declarations if body does not throw"). Severity: **Suggestion**.
- **Method reference possible** (`x -> foo.bar(x)` → `foo::bar`) (AGENTS.md mandate). Severity: **Nit**.

#### Java records — usage boundaries

- **`record` used as a JPA `@Entity`** — records are `final`, have no no-arg constructor, and have immutable fields. Hibernate requires: (a) a no-arg constructor, (b) non-final class for lazy-loading proxy generation, (c) mutable fields for dirty-checking. Using `record` as `@Entity` fails at startup with a cryptic Hibernate error. Severity: **Blocker**. Fix: records for DTOs, projections, and value objects only; regular classes (with Lombok if desired) for entities.
- **Record with validation in compact constructor breaks Jackson deserialization** — if the compact constructor coexists with a canonical constructor, or if the compact constructor throws on the Jackson-provided default value during construction, Jackson throws `InvalidDefinitionException`. Fix: annotate the canonical constructor with `@JsonCreator` and each parameter with `@JsonProperty("fieldName")`. Severity: **Blocker** for request-body records.
- **Pattern matching instanceof with incorrect guard ordering** — `if (f.getX() > 0 && obj instanceof Foo f)` uses the bound variable `f` before it is guaranteed to be bound. Severity: **Blocker** for complex boolean expressions; the compiler catches the simple case but not all.

### N. Errors — specific exceptions, correct HTTP status

The project maps `ServiceException` subclasses to HTTP status in `RestExceptionHandler`. New service code throws `NotFoundException`, `BadRequestException`, `ConflictException`, etc. from `common/exception/`.

Flag:
- **`throw new RuntimeException(...)` in service code** → use a `ServiceException` subclass. Severity: **Suggestion**.
- **`throw new ResponseStatusException(HttpStatus.XXX, ...)` in service code** → HTTP-aware exceptions don't belong in services. Severity: **Blocker**.
- **New exception class not extending `ServiceException`** → won't be caught by `RestExceptionHandler`. Severity: **Blocker**.
- **New HTTP status code not handled in `RestExceptionHandler`** for a new `ServiceException` subclass → will fall through to Spring's default 500. Severity: **Blocker**.
- **`ConstraintViolationException` caught and swallowed** in a service → let `RestExceptionHandler` translate it. Severity: **Suggestion**.

### O. Tests — JUnit 5, Mockito, AssertJ

The project tests live in `app/src/test/java/`. Unit tests use `@ExtendWith(MockitoExtension.class)` + `@InjectMocks` + `@Mock`. No Spring context for unit tests.

Flag:
- **No test** for a new service method or controller mapping. Severity: **Suggestion** by default; **Blocker** if the new code mutates user data, performs auth checks, or implements idempotency.
- **`@SpringBootTest` on a unit test** that only needs to test one class → full context load for a POJO test; makes test suites 10-100x slower. Fix: use `@ExtendWith(MockitoExtension.class)` + `@InjectMocks`. Severity: **Suggestion**.
- **`@MockBean` used where `@Mock` + `@InjectMocks` would suffice** — `@MockBean` triggers a full Spring context reload for each unique combination of mocked beans. Different test classes with different `@MockBean` sets create distinct contexts and multiply startup time. Fix: `@MockBean` only in `@WebMvcTest` or `@DataJpaTest` slice tests; use `@Mock` for everything else. Severity: **Suggestion**.
- **`@Transactional` on an integration test** — within a test transaction, all lazy relationships load successfully (no `LazyInitializationException`). The test passes green. In production, where each service call has its own transaction boundary, the same code throws. Fix: do not use `@Transactional` on integration tests that test service-to-database boundaries. Use `@Sql` for setup and manual `@AfterEach` cleanup. Severity: **Suggestion** (but creates false confidence in green tests).
- **`@Autowired` in a test** when `@InjectMocks` / constructor injection in `@BeforeEach` would suffice. Severity: **Suggestion**.
- **`Mockito.mock(...)` as a field** instead of `@Mock` annotation — works but inconsistent with project style. Severity: **Nit**.
- **`assertThat(actual).isEqualTo(expected)` on objects without `equals()` override** — falls back to reference equality; assertion always passes even when field values differ. Very common with entity objects. Fix: use AssertJ's field-by-field comparison: `assertThat(actual).usingRecursiveComparison().isEqualTo(expected)`. Severity: **Suggestion**.
- **`UnnecessaryStubbingException` risk** — JUnit 5 + Mockito uses `STRICT_STUBS` by default. Stubs set up in a test that are never called cause the test to fail. AI agents frequently over-stub tests. Fix: remove unused `when(...)` setups, or use `@MockitoSettings(strictness = Strictness.LENIENT)` when stubs are conditionally exercised. Severity: **Suggestion**.
- **`Thread.sleep(...)` in tests** → use `Mockito.verify(...)` + argument captors or a `CountDownLatch`. Severity: **Suggestion**.
- **`TestRandomizer.nextObject(...)` not used** when the test needs a random entity — the project provides this utility; use it. Severity: **Nit**.
- **Test class not in the same package** as the class under test → can't access package-private members. Severity: **Suggestion**.

This rule is **never** auto-applied — moves to **Needs you**.

### P. Spring defaults — don't override what you don't need to

- `@Transactional(propagation=REQUIRED)` is the default — don't specify it explicitly unless you mean `REQUIRES_NEW`, `MANDATORY`, etc.
- `FetchType.LAZY` is the default for `@OneToMany` / `@ManyToMany` — don't add `fetch=FetchType.LAZY` explicitly unless correcting a parent class.
- `CascadeType` empty is the default — don't add `cascade={}`.
- **`@Column(name="field_name")` where `field_name` equals the snake-cased field name** → redundant when Spring's physical naming strategy is active. Skip unless the column name diverges. Severity: **Nit**.

### Q. Concurrency — virtual threads, async, thread-safety

Spring Boot 3.x enables virtual threads. Patterns to enforce:

- **`synchronized` on a Spring bean method** — virtual-thread pinning. Use `ReentrantLock` / `java.util.concurrent.locks` if you need explicit locking. Severity: **Suggestion**.
- **`ThreadLocal` in a Spring bean** — doesn't clear across request boundaries with virtual threads. Use `ScopedValue` (Java 21+) or Spring `RequestContextHolder` properly. Severity: **Suggestion**.
- **`@Async` without an explicit `Executor` bean** → defaults to `SimpleAsyncTaskExecutor` which creates a new thread per invocation (defeats virtual-thread pooling). Severity: **Blocker**.
- **`CompletableFuture.runAsync(...)` without an `Executor` parameter** → same issue. Severity: **Blocker**.
- **Shared mutable state** in a `@Service` / `@Component` (non-final, non-thread-safe field) → Spring beans are singletons; concurrent requests race. Severity: **Blocker**.

### R. Constants, enums, and repeated literals

- **Magic string used as event type / status / entity type in 2+ places** → extract to an enum or constant. The project uses `WorkflowStatus`, `WorkflowType`, `EntityType`, `WorkflowCompletionType` enums — match this pattern. Severity: **Suggestion**.
- **Status compared with `String.equals("completed")`** across files → prefer `enum.equals(...)` or a named constant. Severity: **Suggestion**.
- **Same SQL WHERE clause fragment duplicated across multiple `@Query` methods** → consider `JpaSpecificationExecutor` + `Specification` for dynamic queries. Severity: **Suggestion**.
- **Sweep rule**: when you flag a repeated literal in one place, grep the diff for all other occurrences and list them all in one finding.

### S. Dead code, duplication, and pointless indirection

In the changed files, flag:
- **Merge conflict markers** (`<<<<<<<`, `=======`, `>>>>>>>`). Severity: **Blocker**.
- **`System.out.println` / `e.printStackTrace()`** left in source. Severity: **Blocker**.
- **`TODO` / `FIXME` added in this diff** without a ticket reference. Severity: **Nit**.
- **Commented-out code blocks**. Severity: **Suggestion**.
- **Unreachable branches**. Severity: **Suggestion**.
- **Pass-through wrapper method** with no added value. Severity: **Nit**.
- **Two service methods doing the same thing under different names** → consolidate. Severity: **Suggestion**.
- **`instanceof` chain** that could be a visitor or switch expression. Severity: **Suggestion**.

#### Hand-rolled re-implementations of framework primitives

| Hand-rolled shape | Primitive |
| --- | --- |
| `or(col == 'a', col == 'b', col == 'c')` | `IN (:values)` in JPQL / `col IN :values` |
| Manual pagination slice after `findAll()` | `Pageable` / `PageRequest` |
| `if (obj instanceof A) { A a = (A) obj; }` | `if (obj instanceof A a)` (pattern match) |
| Multi-arm `if/else if` on enum | switch expression |
| Manual null-then-default | `Optional.orElse(...)` / `Objects.requireNonNullElse(...)` |
| `list.stream().filter(...).collect(Collectors.toList())` | `list.stream().filter(...).toList()` (Java 16+) |

Severity: **Suggestion (Mechanical)**.

### T. Data modelling — keep PostgreSQL the single source of truth

Flag any new Java class-level `Map<String, String>` / `List<Tuple>` / `Set<String>` that encodes domain reference data (ISO codes, country names, risk-list membership, org acronyms):
- Move to a PG table.
- Read via a service that wraps the repository.
- Delete the Java literal.

Cite Appendix A: *"Let's keep all info in one place — PG in our case."*

Exceptions (don't flag): tiny compile-time sets used purely for type narrowing; test fixtures.

#### Coupling — FK / xref over loose string references

Cross-entity references via FK or xref, not free-text name strings.

#### Normalised side tables over JSONB arrays

Flag a new `@JdbcTypeCode(SqlTypes.JSON)` / JSONB column holding typed structured records (fixed schema, queryable by field) → normalise to a side table. JSONB is fine for opaque payloads (vendor webhook bodies, LLM outputs with unstable schema).

#### Generic table design over per-source duplication

Past-review precedent: one `risk_lists` table with a `source` column. New `section1286_*` / `ofac_*` / `<list>_*` tables are a **Blocker**.

### U. `scripts/` / one-off files

Flag scripts that connect to production DB, write report files to disk, read from local CSV/XLSX, or are described as "one-time". These don't belong in the repo image. Same policy as be-code-review §U.

### V. Dependency hygiene (`build.gradle.kts`)

If `build.gradle.kts` or `buildSrc/` changed:

```bash
git diff --find-renames <range> -- '*build.gradle.kts' | grep -E '^\+' | grep -v '^+++'
```

For every newly added dependency:
- Confirm it is actually imported: `git grep -l "import <package>" -- 'app/src/main/java/**/*.java'`.
- Flag if added but unused.
- Flag if added when an existing dep already covers it.
- Flag heavyweight dep for a tiny use case.
- Flag removed dep still imported somewhere.
- Flag dep that belongs in `testImplementation` added to `implementation`.

### W. Redis caching

The project uses Spring Data Redis. Caching is deceptively easy to get wrong in ways that only appear in production.

Flag:
- **Default Java serialization for Redis (`RedisTemplate` with no explicit serializer)** — Spring Boot's default `RedisTemplate` uses Java native serialization. Any class rename, package change, or field addition causes `SerializationException` / `ClassCastException` when reading stale cache entries after redeployment. This is a silent post-deploy failure. Fix: configure `Jackson2JsonRedisSerializer` (or `GenericJackson2JsonRedisSerializer`) with the injected `ObjectMapper` bean. Severity: **Blocker** for any new `RedisTemplate` bean.
- **`GenericJackson2JsonRedisSerializer` constructed with `new` (no ObjectMapper argument)** — creates a fresh `ObjectMapper` without Spring's auto-configuration: no `JavaTimeModule`, no custom serializers, no Spring visibility settings. Custom date formats and polymorphism configs are silently lost. Fix: inject the auto-configured `ObjectMapper` bean and pass it: `new GenericJackson2JsonRedisSerializer(objectMapper)`. Severity: **Blocker**.
- **No TTL configured on cache entries** — entries live forever, causing unbounded memory growth and stale data that never expires. Fix: `spring.cache.redis.time-to-live` globally, or per-cache via `RedisCacheManagerBuilderCustomizer`. Severity: **Blocker** for new `@Cacheable` annotations.
- **`@Cacheable` self-invocation** — calling a `@Cacheable` method from another method in the same bean bypasses the caching proxy (same root cause as `@Transactional` self-invocation). The method always executes; the cache is never consulted. Fix: extract to a separate `@Component` bean. Severity: **Blocker**.
- **Caching security context / request-scoped objects** — AI agents sometimes generate `@Cacheable` on methods that return `Authentication` objects, `HttpServletRequest` wrappers, or other non-serializable/request-scoped objects. Causes `SerializationException` at runtime. Fix: only cache plain serializable POJOs / records / DTOs. Never cache Spring-managed proxies, security context, or request/session-scoped objects. Severity: **Blocker**.
- **Cache key not versioned across deployments** — if the cached class schema changes (field added/removed), stale entries in Redis from the previous deployment cause deserialization failures. Fix: include a version token in the cache key (`@Cacheable(cacheNames="myCache-v2", ...)`) when the cached schema can change between deploys. Severity: **Suggestion**.

### X. Observability — distributed tracing

The project uses Spring Boot Actuator + OpenTelemetry. Trace context propagation breaks silently.

Flag:
- **Trace context lost across `@Async` boundaries** — `TraceContext` is stored in a `ThreadLocal`. `@Async` methods spin up a new thread from the executor pool that does not inherit the `ThreadLocal`; spans launched in async methods are detached from the parent trace. Fix: configure `ContextPropagatingTaskDecorator` on the `TaskExecutor` used by `@Async`:
  ```java
  executor.setTaskDecorator(new ContextPropagatingTaskDecorator());
  ```
  Severity: **Suggestion** for new `@Async` methods; **Blocker** for async methods that initiate agent calls or NATS dispatches that must be traceable.
- **Manually constructed HTTP clients don't propagate trace headers** — `new OkHttpClient()` / `new RestTemplate()` bypass Micrometer's auto-instrumentation. Outbound requests don't carry `traceparent` / `tracestate` headers, silently breaking distributed traces at every service boundary. Fix: inject auto-configured `RestTemplateBuilder`, or add a custom OkHttp `Interceptor` that reads the current `Span` and injects W3C trace context headers. Severity: **Suggestion** for internal calls; **Blocker** for calls that cross service boundaries under tracing requirements.
- **B3 propagation with baggage fields not listed in config** — if `management.tracing.propagation.type=B3`, baggage fields are not automatically propagated over the wire. This is a silent data loss. Fix: use W3C propagation (the default in Spring Boot 3), or list baggage fields in `management.tracing.baggage.remote-fields`. Severity: **Suggestion** when the diff touches tracing configuration.

### Y. AI agent-introduced anti-patterns

These patterns are introduced with elevated frequency by AI coding agents (Claude Code, Copilot, Cursor) and are not otherwise obvious from the diff. Scan for them specifically.

- **`@Entity`-annotated type returned directly from a `@RestController`** — skips the DTO layer, leaks database schema structure, and can trigger a lazy-load serialization bomb when Jackson traverses all relationships. Fix: always map to a DTO before returning from a controller. Severity: **Blocker**.
- **DTO mapper / converter called inside a loop on a JPA-managed entity list** — even when agents use DTOs, the mapper accesses lazy fields inside a `for` loop, triggering N+1. Fix: ensure `@EntityGraph` / `JOIN FETCH` loaded all needed associations before entering the loop. Severity: **Blocker**.
- **`repository.findById(id).get()` without `.orElseThrow(...)`** — throws `NoSuchElementException` (HTTP 500) instead of `NotFoundException` (HTTP 404). Extremely common AI-generated pattern. Severity: **Blocker**.
- **`new ObjectMapper()` inside a method** — expensive construction, ignores all Spring auto-configuration. See §D Jackson. Severity: **Blocker**.
- **`@SpringBootTest` on every test** — agents default to `@SpringBootTest` even for tests that only need a single POJO. Makes test suites 10-100x slower. See §O. Severity: **Suggestion**.
- **`@Autowired` field injection** — agents prefer it for syntactic brevity. Defeats `final` guarantees, harder to test. See §G. Severity: **Blocker**.
- **Missing `@Transactional` on multi-step service methods** — agents generate multiple `save()` / `delete()` calls without `@Transactional`; partial writes are not atomic. See §C. Severity: **Blocker**.
- **`@Data` on a JPA entity** — agents generate `@Data` on entities by default. See §D Lombok safety. Severity: **Blocker**.
- **`.csrf(csrf -> csrf.disable())`** — agents disable CSRF by default in all security configurations. See §L. Severity: **Blocker** if session auth present; Suggestion otherwise.

## 5.5. Pre-emit spot-checks

Before emitting the report, run these greps over the changed Java files:

```bash
CHANGED=$(git diff --find-renames --name-only "$MB"...HEAD -- '*.java')
MIG=$(git diff --find-renames --name-only "$MB"...HEAD -- 'app/src/main/resources/db/changelog/**')

# Layers (§A)
grep -nE 'import org\.springframework\.http\.(HttpStatus|ResponseEntity|ResponseStatus)' \
  $(echo "$CHANGED" | grep 'Service\.java')                              # HTTP in service → §A §C
grep -nE 'Repository' $(echo "$CHANGED" | grep 'Controller\.java')      # repo in controller → §A §B

# @Transactional proxy gotchas (§C)
grep -nE '@Transactional' $CHANGED | grep -v 'public '                  # @Transactional on non-public → §C
grep -nE 'this\.[a-z][a-zA-Z]+\(' $(echo "$CHANGED" | grep 'Service\.java') # self-invocation candidates → §C
grep -nE 'catch\s*\(.*\)\s*\{' $(echo "$CHANGED" | grep 'Service\.java') | grep -v 'throw\|rethrow\|setRollbackOnly' # swallowed exceptions → §C

# Injection (§G)
grep -nE '@Autowired' $CHANGED                                           # field injection → Blocker

# Lombok entity safety (§D)
grep -nE '@Data' $(echo "$CHANGED" | grep -E 'domain/.*\.java')         # @Data on entity → §D
grep -nE '@EqualsAndHashCode|@ToString' $(echo "$CHANGED" | grep -E 'domain/.*\.java') # check for .Exclude → §D
grep -nE '@Builder' $(echo "$CHANGED" | grep -E 'domain/.*\.java') | grep -v '@Builder\.Default' # missing @Builder.Default → §D

# Jackson (§D)
grep -nE 'new ObjectMapper\(\)' $CHANGED                                # ObjectMapper per-call → Blocker
grep -nE '@JsonIgnoreProperties' $CHANGED | grep -v 'ignoreUnknown'     # missing ignoreUnknown → §D

# Auth (§L)
grep -nE '@PathVariable.*userId|@RequestParam.*userId' \
  $(echo "$CHANGED" | grep 'Controller\.java')                           # IDOR candidate → §L
grep -nE 'csrf.*disable\|disableCsrf' $CHANGED                          # CSRF disabled → §L
grep -nE '@PreAuthorize' $CHANGED | grep -v 'public '                   # @PreAuthorize on non-public → §L
grep -nE 'JwtAuthenticationConverter' $CHANGED                          # check Keycloak role extraction → §L

# DB safety (§E)
grep -nE '\.findAll\(\)' $CHANGED                                        # unbounded read → §E
grep -nE 'createNativeQuery|entityManager' $CHANGED                     # raw SQL risk
grep -nE 'FetchType\.EAGER' $CHANGED                                     # N+1 risk → §E
grep -nE '\.get\(\)' $(echo "$CHANGED" | grep -E 'Service\.java') | grep -v 'getClass\|get(Id\|Name\|Type\|Status\|By\|At\|For\|With\|As\|In\|Of\|From\|To\|It\|All\|New\|Old\|Current)' # Optional.get() without orElseThrow → §C

# Entity returned from controller (§Y)
for f in $(echo "$CHANGED" | grep 'Controller\.java'); do
  grep -nE 'domain\.' "$f" 2>/dev/null && echo "$f: potential entity return — check return types"
done

# Records as entities (§M)
grep -nE '^public record ' $(echo "$CHANGED" | grep -E 'domain/.*\.java') # records in domain → §M

# Redis (§W)
grep -nE 'new (GenericJackson2Json|Jackson2Json)RedisSerializer\(\)' $CHANGED # no ObjectMapper arg → §W
grep -nE 'new RedisTemplate\(\)' $CHANGED                               # check serializer config → §W
grep -nE '@Cacheable' $CHANGED                                           # verify TTL + no self-invocation → §W

# Logging (§I)
grep -nE 'System\.out\.print|printStackTrace' $CHANGED                  # Blocker → §I
grep -nE 'log\.(info|warn|error)\s*\(\s*"[^"]*"\s*\+' $CHANGED         # string concat in log → §I

# NATS (§K)
grep -nE 'jetStream\.publish.*_INBOX\|nc\.publish.*JetStream' $CHANGED  # wrong publish mode → §K
grep -nE '\.durable\(' $CHANGED | grep -c . || echo "NATS: check for pull consumers without durable"

# Migrations (§F)
grep -nE 'NOT NULL' $MIG                                                 # check for backfill
grep -nE 'CREATE INDEX ' $MIG | grep -v 'CONCURRENTLY'                  # non-concurrent index → §F
grep -nE 'ON CONFLICT' $MIG | grep -v 'DO NOTHING\|DO UPDATE'          # bare conflict clause
# Check if any changeset file was modified (not added) — editing deployed changesets
git diff --find-renames --diff-filter=M --name-only "$MB"...HEAD -- 'app/src/main/resources/db/changelog/changes/*.sql' \
  | head && echo "WARNING: existing changeset(s) modified — checksum mismatch will fail on deploy"

# Conflict markers (§S)
git grep -nE '^(<{7}|={7}|>{7})' -- $CHANGED                           # BLOCKER if any hit

# Liquibase master (§F)
for f in $(echo "$MIG" | grep '\.sql$' | grep '/changes/'); do
  base=$(basename "$f")
  grep -q "$base" app/src/main/resources/db/changelog/db.changelog-master.yaml \
    || echo "NOT IN MASTER: $f"
done
```

Also manually verify (no grep catches these):
- **Pre-flight**: base branch detected; `AGENTS.md` and `docs/code-guide.md` consulted.
- **Severity floor**: every drafted finding's severity ≥ source rule's stated severity.
- **Bruno sync**: every changed controller has matching `bruno/ffrs-api/<resource>/*.bru`.
- **Migration chain**: every new changeset is listed in `db.changelog-master.yaml` in the correct order; no existing changeset was modified.
- **Constructor injection**: no `@Autowired` field/setter injection introduced.
- **N+1**: list endpoints with relationships use `@EntityGraph` or `JOIN FETCH`.
- **Long-held transactions**: no `@Transactional` method calling external HTTP/NATS.
- **Lombok entity safety**: no `@Data`, unguarded `@EqualsAndHashCode`, or `@ToString` on `@OneToMany` fields in entity classes.
- **Redis**: new `@Cacheable` methods have TTL configured; serializer uses `ObjectMapper` bean.
- **AI patterns (§Y)**: no entities returned from controllers; DTO mapping not inside loops on entity lists.

### Common drift — phrases that mean "I'm about to silently demote"

If you find yourself writing one of these, stop and re-flag at the source-rule severity:

- *"`@Autowired` is fine here, it's a test"* — AGENTS.md says all beans.
- *"The controller is short, inline SQL/logic is fine"* — §A is layer separation, not line count.
- *"`findAll()` won't return many rows in practice"* — "in practice" fails at scale.
- *"N+1 is OK, the list is small"* — Blocker for new list endpoints regardless.
- *"The migration doesn't need a rollback block, we'll never roll back"* — "we won't" is not a deploy guarantee.
- *"`@Transactional` on the private helper is fine, it's still called from the public method"* — it's silently ignored; the proxy never sees it.
- *"This `@Transactional` self-invocation is fine, the outer method is transactional"* — the inner method runs in whatever boundary the outer method establishes, not a new one; and if the outer method lacks `@Transactional`, neither has one.
- *"I swallowed the exception so we don't crash — the transaction was already committed"* — if you're inside a `@Transactional` method, swallowing an exception commits the partial write silently.
- *"`@Data` is fine, it's just a POJO"* — if `@Entity` is on the class, it's a Blocker.
- *"`@ToString` is fine, we don't call it in a transaction"* — `log.debug("{}", entity)` does.
- *"It's a one-time script, it won't be called again"* — don't commit it. Attach output to Jira.
- *"Hardcoded URL is just a fallback default"* — use `@ConfigurationProperties` with a documented default.
- *"JSON column is fine, the shape won't change"* — stable shape is exactly when a side table beats JSONB.
- *"Per-list table is clearer"* — past review rejected this; generic-with-source.
- *"Existing code uses `@Autowired`, this is consistent"* — legacy state is not a convention for new code.
- *"`log.info` on the search endpoint is fine, it's one line"* — per-keystroke × N users floods the aggregator.
- *"The transaction holds the DB connection during the HTTP call, but it's fast"* — "fast" doesn't survive load.
- *"CSRF is disabled everywhere in our apps"* — verify JWT-only auth before accepting this reasoning.
- *"Redis uses Java serialization, that's the default"* — it breaks after any class rename or field change.
- *"The cache has no TTL, the data never gets stale"* — memory is finite; entries should always expire.
- *"`@Cacheable` calls itself, it just loads once"* — self-invocation bypasses the proxy entirely; the cache is never written.

## 6. Output format

```
# be2-code-review

**Branch:** <current> → **Base:** <base>
**Scope:** <working diff | branch diff> — <N> files
**Tooling coverage:** <skipped categories, if any>
**Build:** <clean | compile errors | Spotless violations | skipped>
**Bruno sync:** <ok | N missing | n/a — no controller changes>
**Migration master:** <ok | N changesets not listed | modified deployed changeset | n/a>
**Verdict:** <ship | fix-before-ship | needs-rework>

## Blockers
- `path/to/File.java:42` — <one-line problem>. Fix: <one-line fix>.

## Suggestions
- `path/to/Other.java:10` — <one-line problem>. Fix: <one-line fix>.

## Nits
- `path/to/Yet.java:88` — <one-line problem>.

## Bruno sync
- (only if controller changed)

## Migration sync
- (only if entity/domain changed)

## Package hygiene
- (only if build.gradle.kts changed)

## Needs you
- (judgment-class findings the apply phase intentionally skips)

## One-time tip
- (optional, only when 3+ findings of one mechanical class)
```

If everything is clean: one line — `**Verdict:** ship — no issues found in <N> files.`

## 7. Offer to apply

After the report (skip when verdict is `n/a` / `ship`), call `AskUserQuestion` with options: **All** (Mechanical + Structural; Judgment → `## Needs you`), **Blockers only**, **No**. Use `AskUserQuestion` for any other decision in the run too.

### Categorize before applying

**Mechanical** (auto-apply, low risk): `@Autowired` field → constructor injection where only one constructor exists, `log.info(...)` string concat → parameterised form, `System.out.println` → `log.info`, `Optional.get()` → `.orElseThrow()` where semantics are obvious, `lambda` → method reference when direct, `instanceof` cast → pattern match, `List` result stream `.collect(Collectors.toList())` → `.toList()`, missing `@ResponseStatus(NO_CONTENT)` on a new `void` DELETE, conflict-marker removal when resolution is obvious, `@ToString.Exclude` added to lazy collection fields, `@JsonIgnoreProperties(ignoreUnknown=true)` added to external-response DTOs, `new ObjectMapper()` → inject `CommonObjectMapper`.

**Structural** (apply with care): SQL moved from controller to service, missing Bruno `.bru` file added, `@EntityGraph` added to fix N+1 on a new endpoint, Liquibase master YAML updated to include new changeset, `@Transactional` / `@Transactional(readOnly=true)` added, hardcoded URL moved to `@ConfigurationProperties`, extract repeated literal to constant, `findAll()` → paginated query, `Pageable` param added to repository method, `@Valid` added to `@RequestBody` params, `@Valid` added to nested DTO fields, Redis serializer updated to use `Jackson2JsonRedisSerializer` + injected bean, `ContextPropagatingTaskDecorator` added to async executor, `@Builder.Default` added to entity collection fields, `findById().get()` → `findById().orElseThrow(NotFoundException::new)`. Use `git mv` for moves; sweep importers with `git grep`.

**Judgment** (never auto-apply, → `## Needs you`): API contract changes on shipped endpoints, splitting a service, new exception hierarchy entries, transaction-boundary redesign (`@Transactional` self-invocation requires extracting to a new bean), retrofitting tests, hardcoded-reference-dict → DB table + migration + service + call sites, per-source table → generic table, JSONB column → normalised side table, FK/xref backfills, new `AuditLog` events in previously-unaudited code, squashing already-deployed migrations, Keycloak `JwtAuthenticationConverter` registration (security change), Redis TTL strategy changes (affects cache behaviour), `@Data` → manual `equals`/`hashCode` on entity (requires understanding business key).

### Apply phase

1. **Preview**: print proposed plan as `Mechanical (N)` / `Structural (M)` / `Skipping → Needs you (K)`.
2. **Apply Mechanical first**, then **Structural**. After each batch, run `./gradlew spotlessCheck compileJava` on changed files.
3. **Re-walk §5.5 spot-checks** against new state; surface anything new under `## Surfaced after apply`.
4. **Summary line**: `Applied <N> fixes across <M> files. Build: <pass/fail>. Spotless: <pass/fail>. Bruno: <synced/N missing>.`

Constraints:
- Edit in place. **Never** `git add` / commit / push / stash / amend.
- **Never** run `./gradlew liquibaseUpdate` or any database-mutating command.
- **Never** run `./gradlew bootRun` or hit live services.
- After Structural file moves/import rewrites, re-grep for stragglers.
- Bruno changes: verify file shape only — never execute the request.
- **No new comments by default** — only when the WHY is non-obvious, not captured by identifier names, and removing it would mislead a future reader.
- User picks **No** → end with: `Left untouched. Re-run /be2-code-review to verify after fixes.`

## 8. Don't do

- Don't comment on style outside the diff.
- Don't suggest large refactors of unchanged code.
- Don't run Liquibase migrations, `bootRun`, or any live service call.
- Don't open a PR, commit, push, or stash.
- Don't `./gradlew dependencies` or modify lock files — dependency state is the user's call.
- Don't generate test scaffolding automatically — moves to **Needs you**.

## Appendix A. Past-review precedents — citation pool

When a finding matches one of the patterns below, cite the precedent in the finding line.

| Pattern | Section | Precedent quote |
| --- | --- | --- |
| Hardcoded reference dict in Java code | §T | *"Let's keep all info in one place — PG in our case. Just add a column to the table and add those to a migration and drop the hardcoded map."* |
| Per-source list table (`section1286_*`) instead of generic | §F / §T | *"Need a generic table name where list1286 is just one of the possible 'source' values so that we won't be adding new tables for every new risk list."* |
| Free-text name reference instead of FK / xref | §T | *"We need more tight coupling with organizations here — a foreign key to org table or a xref table with that link."* |
| JSONB column of typed structured records on main table | §T | *"This should be normalized in a separate table with separate fields rather than JSON in main table."* |
| Debug / report endpoint shipped in production controllers | §B | *"No need in debug API — we will use it as one time execution result to ask for more data."* |
| One-off script connecting to prod DB | §U | *"Should be just a one time run of local utility and report in Jira ticket."* |
| `@Autowired` field injection | §G | AGENTS.md: *"Always use constructor injection for Spring beans with immutable dependencies."* |
| Cursor split across two query params | §B | *"You are already using cursor — use it everywhere instead of two fields."* |
| `nextCursor=null` on last page / empty result | §B | *"Cursor should always point to the last entry in resultset… If no results were loaded — cursor should be same we got in request."* |
| List endpoint bundles aggregate count | §B | *"No need to return count each time. If we need count on UI there should be a count endpoint with same filters returning only amount."* |
| Service method with too many positional params | §C | *"Use objects with named fields for method to be more self-descriptive."* |
| Merge conflict marker pushed in source | §S | *"Fix conflicts before merging."* |
| `@Transactional` method calling external HTTP client | §C / §E | *"Never hold a DB transaction open across a slow external call — DB connections are scarce."* |
| `@Data` on JPA entity | §D | Hibernate best-practices: *"Using @Data with Hibernate entities causes hash code to change after persist, silently corrupting Set/Map lookups."* |
| `@ToString` without `@ToString.Exclude` on lazy collection | §D | *"Calling toString() on an entity with a lazy collection fires N+1 or throws LazyInitializationException outside a transaction."* |
| Editing an already-applied Liquibase changeset | §F | *"Modifying a deployed changeset causes a checksum mismatch ValidationFailedException on the next startup."* |
| `repository.findById(id).get()` without `orElseThrow` | §C §Y | *"Optional.get() throws NoSuchElementException (HTTP 500) instead of NotFoundException (HTTP 404)."* |
| Entity returned directly from controller | §Y | *"Returning @Entity from a controller leaks the database schema and triggers lazy-load serialization bombs."* |
| `new ObjectMapper()` in a method | §D §Y | *"new ObjectMapper() ignores all Spring auto-configuration and is expensive to construct."* |
| Redis default Java serialization | §W | *"Java-serialized cache entries break with ClassCastException after any class rename or field change post-deploy."* |
| `@Cacheable` without TTL | §W | *"Cache entries without TTL grow unboundedly and return stale data indefinitely."* |
| Trace context lost in `@Async` | §X | *"@Async threads don't inherit TraceContext from the parent thread; use ContextPropagatingTaskDecorator."* |
| `@MockBean` used in unit tests | §O | *"@MockBean splits the Spring context per unique mock combination, making test suites 10-100x slower."* |
| `@Transactional` on integration test masks LazyInitializationException | §O | *"Tests pass green inside the test transaction but throw LazyInitializationException in production."* |

## Appendix B. References

- Authority order: `AGENTS.md` / `docs/code-guide.md` → this skill → idiomatic Java 25 / Spring Boot.
- Formatting: `./gradlew spotlessApply` (fixes brace style, import order, line endings).
- Build check: `./gradlew buildDockerImage` (per AGENTS.md).
- Bruno sync: `bruno/ffrs-api/<resource>/` — one `.bru` per route.
- Liquibase master: `app/src/main/resources/db/changelog/db.changelog-master.yaml`.
- Security principal: `FfrsPrincipal` — `getUserId()` returns `UUID`, `getOrgId()` returns `UUID`.
- Exception hierarchy: `ServiceException` → `NotFoundException` / `BadRequestException` / `ConflictException` / `ForbiddenException` / `ExternalServiceException` / `InternalServerErrorException`.
- NATS subjects: `AgentSubjects` utility class for agent RPC; `user.{userId}.*` hierarchy for user-scoped events.
- Config prefix: `finch` — all `@ConfigurationProperties` classes must use this prefix.
- Base package: `com.finchai` — all new classes must live under this package.
- Hibernate entity best-practices: avoid `@Data`, use `@EqualsAndHashCode(onlyExplicitlyIncluded=true)`, `@ToString.Exclude` on all lazy collections.
- Redis serialization: always inject `CommonObjectMapper` / auto-configured `ObjectMapper` into `RedisSerializer` constructors.
- Tracing: W3C propagation is the default in Spring Boot 3; `ContextPropagatingTaskDecorator` required for `@Async` trace continuity.
