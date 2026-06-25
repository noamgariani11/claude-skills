# vuln-research — Active Lessons (self-improving white-box playbook)

Read at the **start of every `/vuln-research` run (Phase R)** and rewritten at the **end (Phase 9)**.
Standing amendments to the SKILL.md doctrine — apply the highest-impact ones first, every run.

## Maintenance contract (read before editing)
- **Guardrails are immutable by this loop.** Lessons sharpen technique/coverage/tooling/ordering
  only — never relax scope, offline-first, read-only-first live confirmation, stop-at-proof, or
  no-auto-submit. A lesson that weakens a guardrail is invalid; delete it. Guardrail-text changes are
  human-only (propose to monk11).
- **Evidence or it didn't happen.** Every lesson cites the run(s) + journal/retro evidence. Record
  what wasted time, not just wins. "No new lesson this run" is a valid outcome.
- **Falsifiable & bounded.** Each lesson carries confidence + supporting/contradicting counts;
  contradicted twice → retire. Keep **≤ 40 active**, ranked highest-impact first. Raw history lives
  in `retro-log.jsonl`, never here.

### Lesson schema
```
### L-NNN · <short imperative title>   [conf: high|med|low] · [area: review/re/fuzz/variant/process]
- **Do:** <concrete behavior change>
- **Why / evidence:** <what happened; cite program + run ts / journal / retro>
- **Apply when:** <trigger condition>
- **Provenance:** added <date> · supporting runs: N · contradicting: M
```

---

## Active lessons (apply every run, highest-impact first)

### L-001 · bug ≠ vulnerability — gate every sink on the 4 questions before it's a finding   [conf: high] · [process]
- **Do:** For each lead, confirm source-attacker-controlled + sink-reachable-on-deployed-path +
  guards-bypassable + crosses-a-security-boundary (`27` §3). If any "no", it's a lead, not a report.
- **Why / evidence:** Book Ch 0 — curl CVE-2020-19909 and Postgres CVE-2020-21469 were *rejected*
  because the "attacker" already had the privilege / it crossed no boundary. Reporting scary-looking
  sinks that aren't exploitable is the #1 white-box slop and burns monk11's signal.
- **Apply when:** Always, before any candidate becomes a finding.
- **Provenance:** added 2026-05-30 · supporting runs: 0 (seed, from book) · contradicting: 0

### L-002 · Sink-to-source beats source-to-sink — start at the dangerous function   [conf: high] · [review]
- **Do:** Begin at the sinks (banned funcs / the `27` §1 table) and trace backward to attacker
  sources; don't enumerate every path forward (path explosion). Include widely-reused wrapper funcs
  (`*_copy`/`*_memcpy`) as sinks; skip rare one-offs.
- **Why / evidence:** Book Ch 1 — "solve the maze from the center"; the dhcp6relay/CVE-2022-0324
  rediscovery worked sink-first. Forward taint branches exponentially on real codebases.
- **Apply when:** Any manual code-review pass.
- **Provenance:** added 2026-05-30 · supporting runs: 0 (seed, from book) · contradicting: 0

### L-003 · Turn one root cause into N with a variant rule across sibling repos   [conf: high] · [variant]
- **Do:** After confirming a bug, encode its root cause as a Semgrep `mode: taint` rule (or CodeQL
  query) and run `sast_scan.py --variant-rule` across every obtainable repo + the program's siblings
  + forks. Patched-here-not-there / forked-but-unpatched are the highest-yield hits.
- **Why / evidence:** Book Ch 3 — variant analysis is the discipline's biggest multiplier; the
  OpenOffice-vs-LibreOffice fork case. The repo's `variant_analysis.py` mines disclosed *patterns*;
  this closes the loop to actual source sweeps.
- **Apply when:** Whenever you confirm a bug or read a disclosed root cause and ≥1 sibling repo exists.
- **Provenance:** added 2026-05-30 · supporting runs: 0 (seed, from book) · contradicting: 0

### L-004 · Managed/script clients (Electron/.NET/Java/Python) decompile to near-source — start there   [conf: high] · [re]
- **Do:** Before fighting native RE, check whether the in-scope client is Electron/asar, .NET, Java,
  or Python. `unpack_app.py` gives near-source; then it's code review (`27`). These hide hardcoded
  secrets, broken pinning, insecure IPC/deeplink/URL-scheme handlers, and client-trusted auth logic.
- **Why / evidence:** Book Ch 4 — DbGate (Electron `eval` sink), LiteDB (.NET), Pixel Wheels (Java),
  Galaxy Attack (Android) all yielded via decompile-to-source, not assembly.
- **Apply when:** Any in-scope thick client. Reach for Ghidra/Frida only for native/stripped/firmware.
- **Provenance:** added 2026-05-30 · supporting runs: 0 (seed, from book) · contradicting: 0

### L-005 · Fuzz the LOCAL copy with ASAN — never the live host   [conf: high] · [fuzz]
- **Do:** Fuzz a parser/protocol only on a local build with ASAN/UBSAN, a thin harness, valid
  minimized seeds, and fuzz-blocker patches in the local build. Triage crashes to the dangerous
  variant before claiming a bug. Pointing a fuzzer at the live host is a DoS (RoE guardrail 4).
- **Why / evidence:** Book Part III — coverage-guided fuzzing of libxls/LibreDWG/NanoMQ is an
  offline build-instrument-fuzz loop; ASAN turns silent corruption into a located, reportable crash.
- **Apply when:** An in-scope asset parses a format/protocol whose parser is obtainable.
- **Provenance:** added 2026-05-30 · supporting runs: 0 (seed, from book) · contradicting: 0

### L-006 · Run n-day (osv_check) before reading code — fastest source-confirmed wins   [conf: med] · [process]
- **Do:** Map shipped deps to known CVEs first (`osv_check.py`), pursue under the three gates, then
  spend the deep code-review budget on 0-day. Cheap n-day often pays before any 0-day lands.
- **Why / evidence:** Book Ch 0 (attack the OSS *dependencies*, not the hardened core) + repo
  doctrine; n-day is the lowest-effort grounded finding when the version is confirmed reachable.
- **Apply when:** Any target with an obtainable dependency manifest.
- **Provenance:** added 2026-05-30 · supporting runs: 0 (seed) · contradicting: 0

### L-007 · SAST scanners fire on security-warning documentation — prune before triaging   [conf: high] · [review]
- **Do:** When a SAST/regex scan fires on `*patterns.py`, `*llm.py`, or any file whose purpose is to GENERATE security reminders, discard all hits immediately — the scanner detected `eval(` in a string like `"Warning: eval() is dangerous"`. Run `grep -l "reminder\|Warning.*dangerous" <file>` to identify these false-positive sources before manual triage.
- **Why / evidence:** VR Run 1 (2026-06-09, anthropic) — 30/30 claude-code leads and 15/48 claude-plugins-official leads were documentation-string false positives in `plugins/security-guidance/hooks/{llm,patterns}.py`. Wasted triage time on zero real sinks.
- **Apply when:** Any Python codebase that ships security-guidance tooling alongside the actual product code.
- **Provenance:** added 2026-06-09 · supporting runs: 1 · contradicting: 0

### L-008 · `vr_planner.py` lists ALL org repos — the documentation/examples repo is NOT the CLI source   [conf: high] · [process]
- **Do:** Before cloning the top-starred repo from `vr_planner`, read its README to confirm it is the actual product source and not a documentation or example repo. The `anthropics/claude-code` repo (131k stars) is an EXAMPLES/DOCS repo — the actual CLI binary is distributed as a compiled Bun binary, not open source. For compiled-binary products, use `unpack_app.py` on the downloaded artifact, not `sast_scan.py` on the docs repo.
- **Why / evidence:** VR Run 1 (2026-06-09, anthropic) — spent scan time on the examples repo and found no real product sinks. The actual CLI binary needs `unpack_app.py`.
- **Apply when:** Any program where the top-starred repo could be documentation rather than source.
- **Provenance:** added 2026-06-09 · supporting runs: 1 · contradicting: 0

### L-009 · Prompt injection finding quality = injection surface (code-level) × completeness of impact chain   [conf: med] · [review]
- **Do:** For any prompt-injection finding, separately score (a) the code-level injection surface (missing sanitization — definite, reportable on its own) and (b) the end-to-end exploitation chain (model-dependent — requires live PoC). File the report on the basis of the code-level gap; note that full exploitation is model-dependent. Also verify the redaction/sanitization layer at the SINK — a comment sanitizer that redacts GitHub tokens but not Anthropic API keys is itself a gap.
- **Why / evidence:** VR Run 1 (2026-06-09, anthropic) — L-019 found `user.name` embedded without `sanitizeContent()` (definite code gap) + `redactGitHubTokens()` missing `sk-ant-*` pattern (definite gap). Combined these into a reportable chain without needing a confirmed live end-to-end PoC.
- **Apply when:** Any prompt injection / LLM pipeline injection finding.
- **Provenance:** added 2026-06-09 · supporting runs: 1 · contradicting: 0

### L-010 · Python 3.12+ extractall() is safe against classic + absolute-path zip-slip — test locally first   [conf: high] · [review]
- **Do:** Before flagging `zipfile.extractall()` as a zip-slip vulnerability, run the local test: create a zip with a `../../../` traversal entry and check if extraction escapes the target dir. Python 3.12 strips traversal components; Python ≤3.11 does NOT. Confirm the server Python version before treating it as exploitable.
- **Why / evidence:** VR Run 1 (2026-06-09, anthropic) — 15 skills leads flagged extractall(); local test on Python 3.12.3 confirmed `../../../tmp/file.txt` extracted to `<tmpdir>/tmp/file.txt` (inside the target). Symlink-based variant also blocked (not treated as symlink). Saved from false positive report.
- **Apply when:** Any Python zip-extraction sink.
- **Provenance:** added 2026-06-09 · supporting runs: 1 · contradicting: 0

### L-011 · Hardcoded-secret SAST hits on SDK/doc repos are almost always OAuth constants or doc examples   [conf: high] · [review]
- **Do:** When a `hardcoded-secret` HIGH hit lands in an SDK repo, read the flagged line before escalating. SDK credential files almost universally contain OAuth grant type strings (`"refresh_token"`, `"urn:ietf:params:oauth:..."`) and JSDoc `@example` token values (`'ghp_exampletoken'`, `'bearer_exampletoken'`) that pattern-match secret detectors. Prune these immediately. A real hardcoded secret in SDK code is very rare — scan the file context, not just the line.
- **Why / evidence:** VR Run 1 (2026-06-09, anthropic) — `anthropic-sdk-typescript` had 3 HIGH leads: all were `GRANT_TYPE_REFRESH_TOKEN = 'refresh_token'`, `'bearer_exampletoken'` in @example, `'ghp_exampletoken'` in @example. `anthropic-sdk-python` had 4 HIGH leads: all were env var name string constants (`"ANTHROPIC_API_KEY"` → string, not value). `claude-code-base-action` had 3 HIGH leads: all were `--secret ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"` in test scripts (env var refs, not literal values).
- **Apply when:** Any SDK (TypeScript/Python/Go/Java/PHP) or test-script HIGH hardcoded-secret lead.
- **Provenance:** added 2026-06-09 · supporting runs: 1 · contradicting: 0

### L-012 · `double-fetch-toctou` SAST rule fires on sequential reads of the same struct/map field — always FP in single-threaded request parsers   [conf: high] · [review]
- **Do:** When `double-fetch-toctou` leads appear in Go/Rust HTTP servers, check the context: if the two reads are on DIFFERENT fields of the same struct (e.g., `request.Params.Arguments["page"]` then `request.Params.Arguments["perPage"]`), it is a false positive — the struct is populated once at parse time, and sequential reads are not a race. A real TOCTOU requires the SAME resource being read twice with a modifiable state between reads. Rule: if the "two fetches" are two different keys or fields, it's FP.
- **Why / evidence:** VR Run 1 (2026-06-09, anthropic) — connect-rust (12 FP), github-mcp-server (26 FP), knowledge-work-plugins (8 FP) all fired on sequential reads of different struct fields. All were FP. Wasted initial triage time.
- **Apply when:** Any `double-fetch-toctou` class lead in any language.
- **Provenance:** added 2026-06-09 · supporting runs: 1 · contradicting: 0

### L-013 · Variant analysis across action family = highest yield for prompt injection   [conf: high] · [variant]
- **Do:** When a prompt injection root cause is found in one GitHub Action (e.g., unsanitized field X embedded in XML prompt), immediately check every surface in the SAME action where user-controlled data is embedded without sanitization. A single root cause (missing XML escaping) typically maps to 3-5 injection surfaces in the same action. Use `grep -rn "sanitizeContent\|escapeXml" src/` to find sanitized fields, then check which fields are NOT in that list.
- **Why / evidence:** VR Run 1 (2026-06-09, anthropic) — one root cause in `claude-code-action` (missing sanitization on `user.name`) mapped to 4 distinct injection surfaces: L-019 (`<trigger_display_name>`), L-021 (coAuthorLine in instruction section), L-022 (`file.path` in `<changed_files>`), L-023 (`comment.path` in `<review_comments>`). Each is a separate exploitation path.
- **Apply when:** Any prompt injection finding in a GitHub Action or LLM pipeline that constructs prompts from multiple GitHub data sources.
- **Provenance:** added 2026-06-09 · supporting runs: 1 · contradicting: 0

### L-014 · VDP programs (no bounty) have mostly closed-source assets — check obtainability before investing   [conf: high] · [process]
- **Do:** Before committing to a VDP program, enumerate the public GitHub repos and confirm they represent actual deployed production code (not just research/hackathon tools). If the org's GitHub is mostly demos/experiments and the real production code is closed-source, estimate the expected white-box yield as LOW and pivot to /bug-hunt + disclosed-report variant analysis instead.
- **Why / evidence:** DoD VDP run 2026-06-10 — `deptofdefense` GitHub has 63 repos but only 2 were relevant (Crossfeed, ATAK-CIV). Crossfeed's vulnerable 2021 code was already fixed in the cisagov/crossfeed current version. Most DoD production code (ASP.NET apps, VPN appliances) is not obtainable.
- **Apply when:** Evaluating any government/military VDP program with a broad scope like "all publicly accessible systems."
- **Provenance:** added 2026-06-10 · supporting runs: 1 · contradicting: 0

### L-015 · For broad-scope VDPs, disclosed-report variant analysis is the highest-yield white-box technique   [conf: med] · [variant]
- **Do:** When the program scope is "all publicly accessible [org] information systems" (i.e., no specific asset list), focus white-box effort on extracting vulnerability CLASSES from the disclosed reports, not individual repo review. Encode the top-3 classes as bug-hunt patterns. For DoD VDP: ASP.NET ResolveUrl XSS (≥5 instances), GlobalProtect CVE-2025-0133 (≥3 instances), Telerik ReportViewer.axd. Each class has a known payload; the work is live enumeration, not source review.
- **Why / evidence:** DoD VDP run 2026-06-10 — 19/25 sample disclosed reports were XSS, representing 2-3 distinct root causes replicated across many .mil subdomains. Each root cause = a sweep pattern for /bug-hunt.
- **Apply when:** Any program where the H1 hacktivity shows the same class appearing on many different subdomains.
- **Provenance:** added 2026-06-10 · supporting runs: 1 · contradicting: 0

### L-016 · Check if a GitHub org's repo is the CURRENT production deployment before sinking time into it   [conf: high] · [process]
- **Do:** After cloning a repo, immediately check if the owning org has moved to a new org/repo (e.g., deptofdefense → cisagov for Crossfeed). For any finding, fetch the equivalent file from the current version and verify the vulnerability still exists before writing it up as a lead. A 5-minute fetch to `github.com/new-org/repo/path/to/file` saves hours of lead writing for dead-end findings.
- **Why / evidence:** DoD VDP run 2026-06-10 — spent ~30 min reviewing `deptofdefense/Crossfeed` reports.ts missing authz, only to find `cisagov/crossfeed` completely rewrote that file with proper org membership checks. L-CF-001 was a wasted lead.
- **Apply when:** Any time you find a significant finding in a repo that was last pushed 2+ years ago. Check for a newer fork or org migration.
- **Provenance:** added 2026-06-10 · supporting runs: 1 · contradicting: 0

### L-017 · Android ImageEditReceiver pattern: exported receivers with no permission guard need a UID/state oracle to exploit   [conf: med] · [re]
- **Do:** When an Android receiver is `exported="true"` with no permission, check if its `onReceive` handler has a state guard (like matching a UUID of a currently-displayed item). If yes, the standalone finding is LOW — to elevate it to reportable, find a second bug that leaks the state (another exported component, log leakage, intent snooping). Document both components as a chain, not individual bugs.
- **Why / evidence:** ATAK-CIV ImageEditReceiver — exported=true, no permission, filepath→file:// construction, but `ImageDropDownReceiver` requires `newUID.equals(_uid)` matching the currently displayed image UUID. External app cannot guess a UUID.
- **Apply when:** Any Android exported broadcast receiver with a stateful processing guard.
- **Provenance:** added 2026-06-10 · supporting runs: 1 · contradicting: 0

### L-018 · Always check the data model's permission fields against the view — "designed but not wired" is the most common Django BOLA pattern   [conf: high] · [review]
- **Do:** When reviewing Django/DRF apps, first enumerate all permission-like fields on models (`*_permission`, `*_role`, `is_manager`, `can_*`). Then check every view that touches that model's data to confirm the permission fields appear in the queryset filter or `permission_classes`. Missing application = BOLA. `UserInWarehouse.d6t_permission/cor_permission` existed in Solo's model but was never checked in the serializer validation — classic "designed but not wired."
- **Why / evidence:** Solo (deptofdefense/solo) run 2026-06-10 — `UserInWarehouse` had explicit `d6t_permission` and `cor_permission` BooleanFields. `UpdateStatusD6TSerializer.validate()` fetched documents by `sdn` with zero membership check. Resulted in lead L-DOD-005 (HIGH).
- **Apply when:** Any Django/DRF or ORM-backed REST app — check model fields first, then grep views/serializers for uses of those fields.
- **Provenance:** added 2026-06-10 · supporting runs: 1 · contradicting: 0

### L-020 · PHP file upload + nginx PHP-FPM: always check if UPLOAD_DIR is under the PHP-executing web root   [conf: high] · [review]
- **Do:** In PHP file-upload services, trace `UPLOAD_DIR` to its absolute path relative to the nginx `root`, then check if a `location ~ \.php$` (or similar) includes that subtree. If `ALLOWED_FILE_FORMATS` is empty or missing, the product accepts ALL types. An attacker can upload a `.php` webshell and execute it by requesting the file URL. Also check whether auth can be disabled (look for `nginx_auth_disabled.conf` or equivalent).
- **Why / evidence:** Malcolm (cisagov/Malcolm) run 2026-06-10 — `config.php` had `ALLOWED_FILE_FORMATS = array()`, `UPLOAD_DIR = __DIR__ . '/files'` = `/var/www/upload/php/files/`, and nginx executed ALL `.php` files under `/var/www/upload/` including uploaded ones. Lead L-DOD-007 (CRITICAL/HIGH).
- **Apply when:** Any PHP file-upload service (filepond, dropzone, etc.) — check upload dir vs nginx root + PHP location.
- **Provenance:** added 2026-06-10 · supporting runs: 1 · contradicting: 0

### L-019 · Django DRF 3.x default DEFAULT_PERMISSION_CLASSES is IsAuthenticated — missing setting is NOT unauthenticated access   [conf: high] · [review]
- **Do:** When `REST_FRAMEWORK` dict lacks `DEFAULT_PERMISSION_CLASSES`, DRF's built-in default is `['rest_framework.permissions.IsAuthenticated']` (confirmed in DRF 3.9+). Missing setting = authenticated-only, not AllowAny. The real bug is missing *object-level* authorization, not the permission class itself.
- **Why / evidence:** Solo settings.py had no DEFAULT_PERMISSION_CLASSES; DRF 3.11 (confirmed from requirements.txt) defaults to IsAuthenticated. Time not wasted writing up a false unauthenticated-access finding.
- **Apply when:** Any Django REST Framework codebase where DEFAULT_PERMISSION_CLASSES is absent from settings.
- **Provenance:** added 2026-06-10 · supporting runs: 1 · contradicting: 0

### L-021 · For CI reporter libs, OTLP data path to API is high-value XSS surface — check ALL span fields, not just exception.message   [conf: high] · [review]
- **Do:** When a CI reporter library sends test telemetry to a dashboard API, the XSS surface is broader than just `exception.message`. The OTLP **span display name itself** (`span.name`) is set to the test case name — which in many renderers is the most prominent field (test list header, trace view title). Check: `span.name`, `test.case.name`, `code.function.name`, `code.filepath`, `exception.type`, `exception.message`, `exception.stacktrace`. Also check suite-level spans (their `name` comes from `<testsuite name="...">`). For JUnit XML input: `quick_xml`'s `attr.unescape_value()` converts `&lt;script&gt;` → `<script>` before API upload — XML entities are transparently decoded.
- **Why / evidence:** Mergify VR run 2026-06-11 deep Rust dive — `spans.rs:152` sets `span.name = case.name` (attacker-controlled via `<testcase name="">`). Three independent reporter implementations (Python/TypeScript/Rust) all confirmed with zero sanitization. XML entity decode means a JUnit attacker can deliver literal `<script>` to the API using XML-encoded payload.
- **Apply when:** Any CI reporter / test telemetry SDK — trace every field that reaches the API's wire format, not just the "obvious" error fields.
- **Provenance:** added 2026-06-11 (strengthened from original L-021) · supporting runs: 1 · contradicting: 0

### L-022 · Jinja2 templates treat PR data as string VALUES, not re-evaluated templates — SSTI via PR author is unlikely without double-rendering   [conf: high] · [review]
- **Do:** When Jinja2 is confirmed as a template engine and PR attributes (title, body) are available as template variables, standard Jinja2 behavior renders PR data as safe string values — `Template("{{ body }}").render(body="{{ 7*7 }}")` → `{{ 7*7 }}` (not "49"). SSTI via PR author requires a double-render implementation pattern (render → string → render again) which is unusual but possible. Fast live test: create PR with title = `{{ 7*7 }}`, trigger a Mergify comment action with `{{ title }}`, observe if the comment says "49".
- **Why / evidence:** Mergify VR run 2026-06-11 — docs confirm Jinja2 (data-types.mdx:261). Standard Jinja2 behavior is safe. SSTI via PR author is low-probability without seeing server-side implementation.
- **Apply when:** Any app using Jinja2/Twig/Handlebars templates with user-controlled data as template variables.
- **Provenance:** added 2026-06-11 · supporting runs: 1 · contradicting: 0

### L-023 · Rust `Command::new().args()` is fundamentally different from TypeScript `execSync(template_string)` — read the subprocess API before flagging cmd injection   [conf: high] · [review]
- **Do:** Before tagging any subprocess call as a command injection candidate, determine which API is used: (a) array/args-based (`Command::args()`, `subprocess.run([...])`, `child_process.execFile()`) — these pass arguments directly to the OS without a shell and are safe by construction; (b) shell-string-based (`execSync(template)`, `os.system(f"...")`, `child_process.exec(str)`) — these go through a shell and require escaping. In Rust, `std::process::Command` is always array-based. In TypeScript/Node.js, `execSync(string)` uses a shell; `execFileSync(string, args_array)` does not.
- **Why / evidence:** Mergify VR run 2026-06-11 — `git.rs` uses `Command::new("git").args(args)` throughout. This looks identical to a dangerous pattern at a glance but is architecturally safe. The TypeScript `execSync(`git ${args.join(' ')}`)` in `utils.ts` was the dangerous-looking one (but turned out to have hardcoded args). Saved time by checking the actual API type early.
- **Apply when:** Any subprocess call in any language — first identify shell-string vs array/exec API before investigating the data flow to that sink.
- **Provenance:** added 2026-06-11 · supporting runs: 1 · contradicting: 0

### L-024 · `http.rs`-style `join()` guards exist in some Rust HTTP clients — verify path-injection defense before tagging a token-leakage finding   [conf: med] · [review]
- **Do:** When a Rust HTTP client builds URLs from caller-supplied `path` strings, check whether the client wraps `Url::join()` with an absolute-URL guard (rejecting `//host/...` and `https://...` inputs). Mergify's `http.rs:join()` blocks both via `path.starts_with("//") || Url::parse(path).is_ok()`. If present, the token leakage to an attacker-controlled host is mitigated at the client layer even if a `path` parameter is attacker-reachable. Note: the `upload.rs` OTLP endpoint bypasses this guard by using `format!()` directly — but the `api_url` and `repository` are caller-controlled, not attacker-controlled.
- **Why / evidence:** Mergify VR run 2026-06-11 — `http.rs:245-258` has the guard, tested with `wiremock` in the same file. Saved from a false positive on path-injection leading to token leakage.
- **Apply when:** Any Rust HTTP wrapper that takes a `path: &str` and builds a URL — look for the `Url::join` guard before flagging path injection.
- **Provenance:** added 2026-06-11 · supporting runs: 1 · contradicting: 0

---

## Retired / disproven (do not relearn these)
_(none yet — when a lesson is contradicted twice, move it here with the reason.)_
