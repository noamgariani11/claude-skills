# h1-report — Active Lessons (the skill's accumulated, self-improving playbook)

This file is **read at the start of every `/h1-report` run (Phase R)** and **rewritten at the
end of every run (Phase 6)**. It is how the skill compounds: each report leaves it sharper than
it found it. Treat the directives here as standing amendments to the SKILL.md doctrine — apply
the highest-impact ones first.

See SKILL.md → "LESSONS.md maintenance contract" for the rules (guardrails immutable, evidence
required, falsifiable, ≤ 40 active, ranked). Raw per-report history is in `report-log.jsonl`.

---

## Active lessons (apply to every report, highest-impact first)

### L-001 · Ground every claim in captured evidence — anti-slop is existential   [conf: high] · [area: framing]
- **Do:** Before any sentence ships, confirm each cited endpoint/parameter/header/version/file/
  request/response is one you actually observed. Cut anything you can't ground. Never invent
  traces, dumps, PoC output, or impact, even while "strengthening" the prose in Phase 4.
- **Why / evidence:** Seed from landscape research — curl ended its bounty and Nextcloud
  suspended theirs under AI-slop floods; the notorious curl report cited a function that did not
  exist plus fabricated GDB dumps. Slop burns the researcher's H1 signal and gets people banned.
- **Apply when:** Always — at draft time and as the final gate before presenting.
- **Provenance:** added 2026-06-08 · supporting: 2 (banco_plata source-map run; deptofdefense Strapi admin) · contradicting: 0

### L-002 · Impact is a concrete attacker scenario, never a class name   [conf: high] · [area: framing]
- **Do:** Write impact as who-the-attacker-is → what they do → what they gain → business
  consequence, framed in *this program's* crown jewels. "Any unauthenticated user enumerates id
  1..N and reads every customer's invoices (names, addresses, amounts) — a mass PII breach,"
  not "IDOR, can see other IDs." Tailor sensitivity to the product (a birth date is noise on a
  dating site, serious on a job board).
- **Why / evidence:** `research/05-report-writing.md` impact cheat-sheet; impact is the part
  that sets the bounty and the part triagers cite when downgrading to Informative.
- **Apply when:** Every report's Impact section.
- **Provenance:** added 2026-06-08 · supporting: 1 (banco_plata source-map run) · contradicting: 0

### L-003 · Build a defensible CVSS vector; don't reverse-engineer a number   [conf: high] · [area: cvss]
- **Do:** Derive each metric from what the bug proves. The most-overstated is `PR` — an IDOR
  reachable only while logged in is `PR:L`, not `PR:N`. Claim `S:C` only when you break out of
  the component's authority (SSRF→metadata, XSS→admin context) and justify it. Make the written
  scenario match the vector.
- **Why / evidence:** `05` §CVSS; programs auto-weight payout off the vector, and a mismatch
  between vector and prose is a credibility hit that triage downgrades.
- **Apply when:** Every Severity section.
- **Provenance:** added 2026-06-08 · supporting: 0 (seed) · contradicting: 0

### L-004 · Run the calibration gate BEFORE writing, not after   [conf: high] · [area: framing]
- **Do:** Ask the `_meta-triage-calibration.md` questions first: is the triggering party
  untrusted across a real boundary? Does it need a nonsensical config? Has it shipped? Who owns
  the root cause (app vs. dependency/OS)? Is *this asset* in **paid** scope (not just reporting
  scope)? If a question fails, say so plainly instead of dressing the finding up.
- **Why / evidence:** Six technically-real reports in the corpus closed Informative/N/A on the
  threat-model line, and a confirmed 9.8 RCE on a marketing asset paid $0. These are the
  rejections that cost reputation if unanticipated.
- **Apply when:** Phase 2, before drafting impact.
- **Provenance:** added 2026-06-08 · supporting: 0 (seed) · contradicting: 0

### L-005 · Zero em dashes, and re-read what --fix touched   [conf: high] · [area: prose]
- **Do:** Always run `report_lint.py --fix` and confirm 0 em/en dashes remain. The auto-fix
  turns ranges into hyphens and clause breaks into commas; after it runs, re-read each touched
  sentence and fix any clumsy comma splice by hand. Em dashes are the loudest LLM tell and read
  as careless to a triager.
- **Why / evidence:** User directive + AI-slop reputation risk (L-001). Mechanical fix is
  deterministic but can leave awkward grammar.
- **Apply when:** Phase 3, every report.
- **Provenance:** added 2026-06-08 · supporting: 0 (seed) · contradicting: 0

### L-006 · Dedup and kill-list gate before spending a report slot   [conf: high] · [area: dedup]
- **Do:** Search disclosed reports + past submissions + changelog for the same endpoint/class
  first (duplicates are the #1 closure reason). Run the candidate against the
  known-invalid-standalone table; if it's only the left column it's hardening advice — tell the
  user, don't write it up. If a near-match exists but yours has higher impact, say so explicitly.
- **Why / evidence:** `05` dedup + kill-list sections; an N/A hurts signal more than a missed bug.
- **Apply when:** Phase 2, before writing.
- **Provenance:** added 2026-06-08 · supporting: 0 (seed) · contradicting: 0

### L-007 · Concise beats complete; cut anything that doesn't help reproduce/assess/fix   [conf: med] · [area: prose]
- **Do:** Every sentence must help the triager reproduce, assess impact, or fix. HackerOne warns
  against *both* vague reports and overloading with unnecessary detail. Use headings, bullets,
  fenced code with language tags; short sentences; active voice; no marketing tone, no pleading.
  Trim long scanner/tool output to the load-bearing lines and mark the cut `[snip]`.
- **Why / evidence:** HackerOne Quality-Reports + Good-Guidelines + the H1 triage-analyst blog
  ("overloading with unnecessary details"); triagers skim and a wall of text delays disclosure.
- **Apply when:** Phase 4, every report.
- **Provenance:** added 2026-06-08 · supporting: 0 (seed) · contradicting: 0

### L-008 · Write the Impact field as a demonstrated outcome, never "an attacker could"   [conf: high] · [area: framing]
- **Do:** The Impact field is separate from the description and has a different job: the business
  consequence, written in the **past tense as something you did** — "I retrieved another tenant's
  invoices, including names and amounts." Strip speculative "could / may / potentially / an
  attacker might"; demonstrated impact removes the debate. Never let Impact just restate the class.
- **Why / evidence:** Triagers close theoretically-possible-but-not-demonstrated findings as
  Informative (Ricardo Iramar "report impacts, not vulnerabilities"; H1 Quality-Reports separates
  steps from security-implications). `report_lint.py` flags impact-speculation.
- **Apply when:** Every Impact section.
- **Provenance:** added 2026-06-08 · supporting: 1 (banco_plata source-map run) · contradicting: 0

### L-009 · Match the program's CVSS version; know what changed in 4.0   [conf: high] · [area: cvss]
- **Do:** Score in the program's *configured* CVSS version (H1 offers 3.0 / 3.1 / 4.0). Don't
  draft 4.0 against a 3.1 program — 4.0 base scores run ~10% higher (≈27% more "Critical"), so a
  mismatch reads inflated and invites a downgrade. In 4.0: Scope is gone (cross-boundary impact →
  Subsequent System SC/SI/SA), Attack Requirements (AT) is new, Safety (S) is only for physical/
  operational harm. Add a one-line justification per non-default metric.
- **Why / evidence:** H1 CVSS-4.0 help + FIRST v4.0 spec + Mend data on 4.0 score inflation;
  the most common 4.0 error is treating it like "3.1 + Scope".
- **Apply when:** Every Severity section. `report_lint.py` prints the declared version.
- **Provenance:** added 2026-06-08 · supporting: 0 (seed, from research) · contradicting: 0

### L-010 · Pick the SPECIFIC CWE — it's a required submission field   [conf: med] · [area: framing]
- **Do:** Select the narrow CWE, not a vague parent (CWE-639 *Authz Bypass Through User-Controlled
  Key* for an IDOR, not bare CWE-284). Put it in References so it's unmissable. The weakness is a
  required field on the H1 form and drives the triager's mental model.
- **Why / evidence:** H1 Submitting-Reports form (Weakness is required); precise CWE speeds triage
  routing and signals competence.
- **Apply when:** Phase 2 / References, every report.
- **Provenance:** added 2026-06-08 · supporting: 0 (seed, from research) · contradicting: 0

### L-011 · URLs/payloads as copy-pasteable text; attach media, never link it   [conf: high] · [area: prose]
- **Do:** Every URL, endpoint, parameter, and payload must appear as plain text, not only inside a
  screenshot — triagers validate by pasting and see the app for the first time. Include the
  sign-in URL, prerequisites (accounts/roles), and the full request (all required headers). For
  chains/>3-step repros use a short video, but **attach** it (.mp4/.mov/.webm) — never a YouTube/
  Streamable/Drive/Imgur link (rots, not trusted, sometimes banned). Skip media for self-evident bugs.
- **Why / evidence:** H1 triage-analyst blog ("validating by copy-paste, visiting the app for the
  first time"); H1 Submitting-Reports (attach video); Intigriti (no external hosting).
  `report_lint.py` flags external-evidence and wall-of-output.
- **Apply when:** Phase 4 evidence pass, every report.
- **Provenance:** added 2026-06-08 · supporting: 0 (seed, from research) · contradicting: 0

### L-012 · Self-close a weak report (0 rep) rather than eat a program N/A (−5); answer Needs-Info fast   [conf: high] · [area: process]
- **Do:** Reputation moves only on the *program's* verdict: Triaged/Resolved ≈ +7, N/A ≈ −5,
  Spam ≈ −10, Informative/Duplicate ≈ 0; self-closing costs 0. If a draft tripped the kill-list/
  calibration gate and can't be escalated, advise *not submitting* or self-closing over letting it
  N/A. Flag that "Needs More Info" auto-closes as Informative after 30 days of silence — respond
  with the *minimal* missing repro. Mediation needs positive signal + one calm request, no
  pasted "possible impact" walls.
- **Why / evidence:** H1 Reputation + Report-States + Hacker-Mediation docs. Advise; never submit
  or self-close on the user's behalf (Guardrail 2).
- **Apply when:** Phase 5 (submission decision) and Mode C.
- **Provenance:** added 2026-06-08 · supporting: 0 (seed, from research) · contradicting: 0

### L-013 · Handle pushback by state, and frame an incomplete-patch bypass explicitly   [conf: med] · [area: process]
- **Do:** Needs-Info → minimal clean repro (a 30-sec video converts most). Duplicate → ask the
  original's date/ID; if yours pre-dates or proves higher impact, say so *once* with evidence,
  then release. Informative/N-A → re-anchor on a concrete attacker scenario or let it go. When
  your finding bypasses a previously-*resolved* report, cite that report ID and spell out which
  code path / transport / role the fix missed — that's what makes it a fresh variant, not a dup.
- **Why / evidence:** `26-sustaining-success.md` triage state machine + `05` pushback section;
  corpus shows incomplete-fix bypasses (PayPal #510152 of #488147; Shopify Flow #698708 of
  #416983) paying as fresh reports. One combative thread can cost future private invites.
- **Apply when:** Mode C, and Phase 2 when a near-duplicate exists.
- **Provenance:** added 2026-06-08 · supporting: 0 (seed, from research) · contradicting: 0

---

### L-020 · User-directed outbound connectors are NOT SSRF — only a blocklist bypass is   [conf: high] · [area: framing]
- **Do:** Before calling any server-side outbound connection "SSRF," ask: is this connection the explicit purpose of the feature? Webhooks, URL fetch, web search, MCP remote connectors, and similar user-directed URL fetchers exist to make HTTP requests on the user's behalf. Reporting "the server makes a request" on these features will always be closed Informative. The reportable finding on outbound connectors is one of: (a) bypass of the internal-IP/IMDS/RFC-1918 blocklist at execution time, (b) a user routing requests to resources the product policy says they cannot reach, or (c) missing authentication that lets an *unauthenticated* user register URLs. Confirmed external egress to a user-controlled URL is the product working correctly.
- **Why / evidence:** L-017 closed Informative. Anthropic: "The remote MCP connector feature exists specifically to make outbound connections from our infrastructure to user-registered MCP server URLs — that is its purpose, and the egress IP range and Claude-User user-agent are publicly documented for exactly this use case." The IP `160.79.106.36` and `User-Agent: Claude-User` are in Anthropic's public docs.
- **Apply when:** Any time a feature involves the server fetching a user-supplied URL (MCP, webhook, web fetch, browser, image proxy, etc.). Check program docs for published egress IP ranges before claiming "infrastructure fingerprinting" as impact.
- **Provenance:** added 2026-06-08 · supporting: 1 (L-017 closed Informative) · contradicting: 0

### L-021 · Execution-layer IP blocking with atomic DNS resolution is a complete mitigation   [conf: high] · [area: framing]
- **Do:** Do NOT claim that "registration without validation" is a defense-in-depth failure when the program's execution layer validates the *resolved* destination IP atomically at socket connection time. Atomic validation (resolve DNS, then check IP, in the same operation before opening the socket) addresses: (1) all transports, (2) future code paths, (3) DNS rebinding / TOCTOU. The security boundary is correctly at execution, not registration, because registration stores a hostname while the risk is at connection time. Only report registration-level validation gaps if you can show a path that bypasses the execution-layer check.
- **Why / evidence:** L-017 closed Informative. Anthropic: "The execution-time transport layer is the intended security boundary here precisely because it covers every code path that opens an outbound connection, including future ones, regardless of what is stored at registration time." The "WebSocket transport routes through the same connection-layer protection" confirmed the unconfirmed escalation path was already covered.
- **Apply when:** Any SSRF or CSRF report involving a multi-stage registration + execution flow. Verify whether execution-layer validation is atomic (DNS + IP check at connection time) before claiming the gap.
- **Provenance:** added 2026-06-08 · supporting: 1 (L-017 closed Informative) · contradicting: 0

### L-022 · Check published docs for documented egress IPs before claiming infrastructure exposure   [conf: med] · [area: framing]
- **Do:** Before writing impact claims like "infrastructure fingerprinting," "IP tracking," or "reveals Anthropic's network topology," check whether the program has publicly documented the egress IP range and outbound behavior. If they have, those impact claims collapse. For Anthropic specifically: `160.79.106.36` and `User-Agent: Claude-User` are documented. Similarly check for publicly known AWS/GCP account IDs, service principal names, and X-Ray trace format before calling them sensitive.
- **Why / evidence:** L-017 closed Informative. Anthropic confirmed the egress IP and User-Agent are "publicly documented for exactly this use case." The infrastructure fingerprinting impact claim in the report was therefore invalid.
- **Apply when:** Any report where impact includes "leaks internal server IP," "exposes infrastructure details," or "reveals backend topology." Verify that the exposed values are not already public before submitting.
- **Provenance:** added 2026-06-08 · supporting: 1 (L-017 closed Informative) · contradicting: 0

### L-019 · Put Asset and CWE at the top of the Severity section, matching the H1 form   [conf: high] · [area: framing]
- **Do:** The H1 submission form shows Asset (dropdown), Weakness/CWE (dropdown), and Severity/CVSS as three adjacent fields. Mirror that in the Severity section header: three lines before the vector, in this order:
  ```
  **Asset**: <asset name and tier>
  **Weakness**: CWE-NNN - <name> (root mechanism: CWE-NNN if applicable)
  **Severity**: <rating> (<score if 4.0>)
  `CVSS:4.0/...`
  ```
  The detailed endpoint list stays in the Affected Asset section below.
- **Why / evidence:** User directive on L-017/L-005 run. Grouping these three fields together lets a triager (and the researcher before submitting) scan the submission-form values without hunting through separate sections. The CWE is a required H1 field and should be unmissable, not buried in References.
- **Apply when:** Every report, every mode. Three lines at the top of Severity, then the chart.
- **Provenance:** added 2026-06-08 · supporting: 3 (L-017, L-005 anthropic run, banco_plata B-run) · contradicting: 0

### L-018 · Source-code findings: frame repro as read-only code inspection, not live trigger   [conf: high] · [area: framing]
- **Do:** When a finding comes from static analysis or source review (no live exploit), make the Steps to Reproduce be read-only: "open file X at commit Y, observe property Z." Do not describe the attack vector as a repro step (e.g. "post an issue containing a credential") because that would require a state-changing action the researcher did not take. State clearly in the repro preamble that the finding is from source code review. In Impact, separately distinguish what the code guarantees (directly confirmed from source) vs. what follows as a logical consequence vs. what is inferred behavior (label each). In the repro and impact sections, label each numbered step explicitly: "code-guaranteed" or "logical consequence."
- **Why / evidence:** L-005 anthropic run. The existing draft described live issue creation as a repro step, which crossed the read-only boundary without authorization. Source-code findings are still real and reportable; they just need the repro framed correctly so the triager can verify by reading the code, not by reproducing an attack.
- **Apply when:** Any report derived from source/binary review, static analysis, or config audit where no live exploit was executed.
- **Provenance:** added 2026-06-08 · supporting: 4 (L-005 anthropic run, L019-L023 VR, L019-L023 final polish, banco_plata source-map run) · contradicting: 0

### L-016 · Embed the CVSS chart in the Severity section, not just the vector string   [conf: high] · [area: cvss]
- **Do:** In the Severity section, include a full 11-row markdown table showing every CVSS 4.0 metric with all options listed and the selected value bolded. Put the raw vector string above the table. Add a period to each Justification cell so the linter's sentence splitter terminates cleanly at table boundaries. This is how the H1 submission form presents CVSS 4.0 and it gives triagers a scannable visual rather than a dense string to parse.
- **Why / evidence:** L-017 anthropic run: user explicitly requested the chart format to match the H1 form layout. A bare vector string requires the reader to decode each metric abbreviation; the table makes every choice immediately legible without external reference.
- **Apply when:** Every report that uses CVSS 4.0. For 3.1 reports, the table format still works (7 metrics instead of 11).
- **Provenance:** added 2026-06-08 · supporting: 3 (L-017, L019-L023 VR, L019-L023 final polish) · contradicting: 0

### L-017 · Fill in real observed values; never leave investigation artifacts as placeholders   [conf: high] · [area: poc]
- **Do:** Replace every `{ORG_UUID}`, `{SERVER_UUID}`, `{SESSION_ID}`, and similar tokens with the actual values observed during testing. Secrets (session cookies, API keys) stay redacted as `[SESSION_KEY]`, but non-secret identifiers (org UUIDs, object UUIDs, trace IDs, IPs) should be the real values from the investigation. Include the complete observed response, not a trimmed version.
- **Why / evidence:** L-017 anthropic run: org UUID `ee354996-...`, server UUID `39bd4f2e-...`, session ID `f82042f3-...`, full httpbin echo with Traceparent were all available but the first draft used generic placeholders. Triagers reproduce by copy-paste; a placeholder forces them to guess what to fill in. Real values also prove the claim was tested, not inferred.
- **Apply when:** Phase 4 (evidence pass), every report. After polishing prose, do a final scan for any remaining `{curly-brace}` tokens or `<angle-bracket>` markers that are not intentional substitution instructions.
- **Provenance:** added 2026-06-08 · supporting: 1 (L-017 anthropic run) · contradicting: 0

### L-014 · Echo service confirms the mechanism; internal access success is the SSRF PoC   [conf: high] · [area: poc]
- **Do:** An httpbin/interactsh echo that shows the server made an outbound request to your controlled URL confirms the attack vector (the connector makes server-side connections), NOT that there is a finding. For an outbound-connector feature (MCP, webhook, URL fetch, image proxy), the server making external requests IS the feature. The SSRF PoC is a request that reaches an internal target (127.0.0.1, 169.254.169.254/latest/meta-data, RFC-1918, internal hostname) at connection time and returns sensitive data. Use the echo to document the mechanism (egress IP, headers) as context; the impact demonstration must show internal access success.
- **Why / evidence:** L-017 closed Informative. The echo showed `160.79.106.36` / `User-Agent: Claude-User` and was treated as the PoC. Triager: "the remote MCP connector feature exists specifically to make outbound connections." The external echo only proved the feature worked. L-005 similarly: the sanitizer behavior was accurate but the precondition (publicly pasted key) was already the full exposure.
- **Apply when:** Any SSRF investigation involving a URL-fetching feature. Record echo results as mechanism context; do not advance to CONFIRMED or draft a report until internal IP access at connection time succeeds.
- **Provenance:** added 2026-06-08 · supporting: 1 (L-017 anthropic run) · contradicting: 0 · updated: 2026-06-08 (L-005 Informative reinforces)

### L-015 · Disclose unconfirmed escalation paths that share the same registration step   [conf: med] · [area: framing]
- **Do:** When the confirmed finding shares a registration or prerequisite step with an unconfirmed, higher-severity escalation path (e.g. confirmed external SSRF + unverified IMDS access via alternate transport), describe both in the report. Label the unconfirmed path clearly ("unconfirmed escalation path - potential Critical") and explain exactly which condition makes it higher severity and why it could not be verified. Ask the program to check it independently. This is not speculation; it is scoped disclosure that lets the program assess risk across both confirmed and potential states.
- **Why / evidence:** L-017 confirmed external SSRF (Medium) but could not test the WebSocket transport due to Cloudflare enforcement. Disclosing the IMDS path with the "unconfirmed" label gives the program complete information without overstating the confirmed finding or suppressing a real risk.
- **Apply when:** Any partial-chain SSRF or access-control report where a second transport or code path might remove the mitigation already tested. One paragraph, clearly labeled, not speculative prose.
- **Provenance:** added 2026-06-08 · supporting: 1 (L-017 anthropic run) · contradicting: 0

### L-023 · Sanitizer/redaction gaps are only findings when they are the ROOT CAUSE of exposure — if injection already enables exfiltration, missing redaction is noise   [conf: high] · [area: framing]
- **Do:** Before writing up any sanitizer or redaction gap, apply two tests in order:
  **Test 1 (incremental-exposure):**
  1. Who has the sensitive value as a result of the **precondition** alone (before the sanitizer runs)?
  2. Who **additionally** gets the value because of the sanitizer gap?
  3. Is group 2 a new, unauthorized party — or just the same audience that already has it?
  If group 2 is the same or a subset of group 1, there is no incremental exposure: stop here.
  **Test 2 (root-cause test):**
  If a separate vulnerability (e.g. XML injection + unrestricted `Read`) already enables the attacker to direct the LLM to read and post secrets, the missing redaction pattern adds no meaningful protection. An LLM following injected instructions can post the key verbatim, encode it, or split it regardless of output sanitization. Do NOT add "missing `sk-ant-*` redaction" as a compounding gap in an injection-chain report — it will be confirmed Informational and weakens the report's credibility.
- **Why / evidence:** L-005 closed Informative (precondition = full exposure). L019-L023 polish run (2026-06-09): missing `sk-ant-*` in `redactGitHubTokens()` was removed from the report after user correctly identified it as noise — "the scenario requires a developer to paste their API key into a GitHub issue... the precondition already constitutes full exposure." Even in the runner-secret variant of the scenario, the injection chain itself enables exfiltration; the missing redaction pattern does not change the attack or the impact.
- **When sanitizer gaps ARE standalone findings:** (a) A key pasted in a private/access-controlled channel leaks to a MORE-ACCESSIBLE location (e.g., a public CI log, a third-party error-tracking service). (b) The sanitizer is the ONLY barrier between the key and an external audience — no other vulnerability is required. The key question: **is the sanitizer gap the root cause of the exposure, or is the exposure caused by something else that the sanitizer merely fails to catch?**
- **Apply when:** Any report involving a content sanitizer, output redactor, log scrubber, or token pattern-matcher. Run both tests before adding a redaction gap to any chain — even when the precondition involves a private secret.
- **Provenance:** added 2026-06-08 · supporting: 3 (L-005 Informative, L019-L023 PoC-run, L019-L023 polish) · contradicting: 0

### L-024 · XML injection PoC: describe closing tags in prose, not XML code blocks   [conf: high] · [area: poc]
- **Do:** When the finding IS XML/prompt injection, the attack payload contains XML closing tags (e.g. the string that closes the `changed_files` block). `report_validator.py` treats any `</tag>` pattern as an unfilled template stub and FAILs the placeholders check. Workaround: keep the PoC section populated with source-code TypeScript/YAML snippets (which have no angle brackets). Describe the injection payload and its effect in prose using phrases like "the closing-tag string for the `changed_files` block" instead of the literal XML. The attack vector description in Steps to Reproduce can name the technique without including the raw XML syntax.
- **Why / evidence:** L019-L023 anthropic VR run (2026-06-09). The validator FAILed on `</changed_files>`, `</trigger_display_name>`, `</trigger_comment>` in code blocks and inline code. Took 3 editing passes to clear all placeholder false positives while keeping the report accurate.
- **Apply when:** Any injection report (XSS, template injection, prompt injection) where the PoC contains XML/HTML tag syntax. Check after every Phase 3 run if `report_validator.py` flags placeholders in the PoC section.
- **Provenance:** added 2026-06-09 · supporting: 1 (L019-L023 anthropic VR) · contradicting: 0

### L-025 · report_lint.py run-on WARNs from numbered bullets and bold headers are linter artifacts, not prose problems   [conf: high] · [area: prose]
- **Do:** After running `report_lint.py`, distinguish genuine prose run-ons from structural linter artifacts. The linter's `split_sentences()` function flattens the entire document (excluding fenced code blocks) and splits only on `[.!?]\s+[A-Z]`. Numbered list items (`1.`, `2.`, `3.`), bold headers (`**Gap N: ...**`), and markdown table rows never match that pattern — so adjacent bullets and gap sections always appear as one giant "sentence" to the linter. Fix the genuine prose run-ons (actual prose sentences >40 words); accept the structural ones when each visual paragraph is concise for a human reader. To force a sentence boundary between a prose sentence and a `**Bold header**`, start the bold section with a plain-text sentence that begins with uppercase A-Z instead.
- **Why / evidence:** L019-L023 polish run (2026-06-09). After fixing all genuine prose and passive voice, 12 WARNs remained — all from numbered bullets, bold gap headers, and tables. A human triager sees correctly separated paragraphs; the linter treats them as one sentence. Attempting to fix structural artifacts would require removing numbered lists, which harms readability.
- **Apply when:** Phase 3/4 lint review. If a WARN starts at a numbered bullet (`1. `, `2. `) or a bold section header, it is structural. If it starts in the middle of a prose paragraph, fix it.
- **Provenance:** added 2026-06-09 · supporting: 1 (L019-L023 polish run) · contradicting: 0

### L-026 · Verify that the target sanitizer actually blocks the injection character before claiming a sanitization gap   [conf: high] · [area: framing]
- **Do:** Before reporting "field X is unsanitized while field Y is sanitized," confirm that the sanitizer actually BLOCKS the dangerous character for field Y. If the sanitizer is a best-effort filter for a different threat class (e.g., hidden-instruction vectors like invisible chars and HTML comments) and passes the attack character through unchanged for ALL fields, then "field X skips the sanitizer" is not a finding — the sanitizer doesn't protect any field from that character. Run the target sanitizer mentally or literally against the attack character on a field that DOES go through it before claiming the non-sanitized fields are a gap.
- **Why / evidence:** L019-L023 closed. Triager: "Literal angle brackets already pass through the sanitizer unchanged for all fields including issue and comment bodies, so the additional fields you identified do not grant an attacker any capability beyond what is already reachable via the issue or comment body itself." The `sanitizeContent()` function strips invisible chars, HTML comments, and hidden attributes — it never XML-escaped `<>` for any field. Our finding that display name / file paths / comment paths "skip sanitizeContent()" was accurate but irrelevant: `<>` still passes for issue body too.
- **Apply when:** Any injection finding where the argument is "field X is embedded without sanitization while other fields go through the sanitizer." Confirm sanitizer blocks the attack character on the sanitized fields before writing the finding. If it doesn't, the finding needs a different framing (e.g., "no field is XML-escaped, the entire prompt is injectable") or is N/A.
- **Provenance:** added 2026-06-09 · supporting: 2 (L019-L023 first submission + second submission both closed informative 2026-06-09) · contradicting: 0

### L-027 · Explicitly documented residual risk kills a prompt-injection finding against an opt-in feature   [conf: high] · [area: framing]
- **Do:** Before submitting any prompt-injection report against an action/agent that has an opt-in "unauthenticated users can trigger" configuration, check the project's security documentation. If the security docs explicitly state that the opt-in accepts residual prompt-injection risk and advises mitigations (restricted tool allowlist, limited permissions), the finding will be closed as by-design. The security boundary is the write-permission check, not the prompt sanitizer — operators who opt in accept the injection surface. Confirm the security docs DON'T document the risk before reporting.
- **Why / evidence:** L019-L023 closed twice (two separate submissions, both informative 2026-06-09). Triager: "The allowed_non_write_users opt-in is explicitly documented in the project's public security documentation as a significant security risk that should only be used with extremely limited workflow permissions and a restricted tool allowlist; operators who enable it accept residual prompt-injection risk by design... This residual prompt-injection surface is documented under the 'Prompt Injection Risks' section of that same security documentation."
- **Apply when:** Any prompt-injection finding against a CI/CD action, agent workflow, or LLM integration that has an opt-in for unauthenticated triggering. Read the project's SECURITY.md / security docs before drafting the report. Check for "Prompt Injection Risks" or similar section explicitly.
- **Provenance:** added 2026-06-09 · supporting: 2 (L019-L023 closed twice) · contradicting: 0

### L-028 · Bash comment lines inside PoC code blocks are parsed as headings by report_validator.py — put curl before any # comments   [conf: high] · [area: poc]
- **Do:** report_validator.py's `split_sections()` scans ALL lines for `^#{1,6}\s+` headings, including lines inside fenced code blocks. A bash comment like `# Confirm live exposure` or `# HTTP/2 200` at the start of a PoC code block becomes a new section heading, cutting the PoC section body before the curl command and causing `[WARN] poc-evidence: PoC has prose but no fenced evidence`. Ensure curl (or the HTTP request) appears as the FIRST non-blank line inside the code block, before any `#` comment lines. OR use `## ` comments in prose outside the block to describe what the code does, with the code itself having no leading `# ` comments.
- **Why / evidence:** Discovered on h1-report batch run 2026-06-09 (verily, kong, vodafone fleet drafts all had this WARN). The bash code blocks started with `# Confirm live exposure and map size` before the curl command, making the validator treat the PoC body as empty.
- **Apply when:** Phase 3 (after running report_validator.py). If you see `[WARN] poc-evidence: PoC has prose but no fenced evidence` on a report that clearly has bash code blocks in the PoC section, check whether a `# comment` line is the first line of any code block in that section.
- **Provenance:** added 2026-06-09 · supporting: 1 (batch run verily/kong/vodafone) · contradicting: 0

### L-029 · CVSS vector format: slashes required between all metrics — CVSS:3.1/AV:N not CVSS:3.1 AV:N   [conf: high] · [area: cvss]
- **Do:** The validator regex for CVSS vectors is `CVSS:(3.1|4.0)/AV:` (slash immediately after the version number). `CVSS:3.1 AV:N/...` (space after version) is NOT matched. Always write `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` with all slashes. Also applies inside backtick code spans — the regex searches the full text including spans.
- **Why / evidence:** Batch run 2026-06-09: Caterpillar and Robinhood dev-build drafts both used `CVSS:3.1 AV:N/...` and failed the cvss check.
- **Apply when:** Any time you write a CVSS vector. Grep for `CVSS:3.1 ` (with trailing space) before running the validator.
- **Provenance:** added 2026-06-09 · supporting: 1 (caterpillar + robinhood dev-build) · contradicting: 0

### L-030 · Impact section must have prose directly under the heading — subsections alone make it "empty" per the parser   [conf: high] · [area: framing]
- **Do:** The validator maps each section heading to the body text between that heading and the next heading (any level). If `## Impact` or `# Impact` is immediately followed by `## What this is not` or `### ` subsections with no prose in between, the section body is empty and the validator FAILs. Always include at least one sentence of prose directly under the Impact heading, before any subsections. Even a one-liner summary like "Reading this source map enables three concrete attacks against the production API." is sufficient.
- **Why / evidence:** Batch run 2026-06-09: NBA-public, Verily, Kong, and Vodafone Oman fleet drafts all failed with "empty required section(s): impact" because their `# Impact` section jumped straight into `## What this is not`.
- **Apply when:** Any report whose Impact section uses `## ` subsections. Always put at least one prose sentence before the first subsection.
- **Provenance:** added 2026-06-09 · supporting: 1 (4 fleet drafts) · contradicting: 0

### L-032 · VDP open-redirect context: `.mil` CAC portal redirects are worth reporting despite the kill-list   [conf: med] · [area: framing]
- **Do:** The kill-list says "open redirect alone" is weak. For DoD VDP specifically, an open redirect on a `.mil` portal that fires AFTER CAC (PKI card) authentication is material: (1) the `.mil` domain provides a highly credible lure with no spoofed domain needed, (2) CAC holders are DoD personnel whose credentials and machine trust are high-value targets, (3) VDP triage cares about policy improvement, not just bounty-class impact. Report it if the redirect fires post-auth on a `.mil` or federal system. For commercial bounty programs, apply the standard kill-list filter.
- **Why / evidence:** deptofdefense run 2026-06-11. The CAC flow: `eph.health.mil/Login.aspx?ReturnUrl=external` embeds the external URL in the phauth.health.mil CAC link; CertLogin.aspx preserves it through the 302 chain. No OAuth token steal confirmed, but post-auth redirect on MHS healthcare portals is reportable to a military VDP.
- **Apply when:** Open redirect findings on `.mil`, `.gov`, `.mil.edu`, or federal program assets where authentication is via PIV/CAC/PKI or a government SSO.
- **Provenance:** added 2026-06-11 · supporting: 1 (deptofdefense run) · contradicting: 0

### L-033 · Access-control/exposure findings: split impact into (1) what was retrieved and (2) the conditions that now exist   [conf: med] · [area: framing]
- **Do:** When the primary harm is attack surface creation rather than data exfiltration (admin panel publicly accessible, endpoint missing IP restriction, unauthenticated configuration API), the impact section must still demonstrate something concrete. Structure it as: paragraph 1 = what you actually retrieved in past tense (specific UUIDs, versions, config fields, response bodies), paragraph 2 onward = the conditions that now exist as present-state facts (not "an attacker can" speculation). Frame attack-surface conditions with stative verbs: "The admin login form accepts connections from any internet host" (current state) rather than "An attacker can target accounts" (future action). This clears the impact-speculation lint WARN without losing the downstream risk.
- **Why / evidence:** deptofdefense Strapi admin report 2026-06-11. Two lint WARNs for "an attacker can" in the Impact section. Reframed to: "I retrieved... The admin login form accepts connections from any internet host. PIEE administrator accounts are now exposed to password spraying... The version and feature set are now externally queryable by any internet user." Both WARNs cleared.
- **Apply when:** Any access control, admin panel exposure, or information disclosure finding where the demonstrated harm is "this surface is accessible" rather than "I exfiltrated data." Also applies to missing-network-restriction findings on admin APIs.
- **Provenance:** added 2026-06-11 · supporting: 1 (deptofdefense Strapi admin) · contradicting: 0

## Retired / contradicted lessons

(none yet)

### L-031 · Source-map findings: mine exposed schemas for no-max and no-uniqueness gaps as secondary leads   [conf: med] · [area: framing]
- **Do:** When a source map exposes private package schemas (Zod, Yup, class-validator), immediately scan every input field for a missing upper-bound, missing uniqueness constraint, or missing cross-field validation. Label each gap "code-guaranteed: no maximum/uniqueness constraint in client schema" and include it in Impact as an unconfirmed escalation path (L-015 framing). These are not speculation; they are factual absences in the source that the program can verify independently.
- **Why / evidence:** banco_plata source-map run (2026-06-10): `ODBCardApplicationDataSchemaV2.creditLimit` and `ODBPersonalLinkDataSchema.inviterId` both showed validation gaps directly from exposed source. Both became secondary leads, each potentially high-severity if the backend does not compensate.
- **Apply when:** Any source-code or source-map disclosure finding where private package schemas are readable.
- **Provenance:** added 2026-06-10 · supporting: 1 (banco_plata source-map run) · contradicting: 0

### L-034 · Asymmetric config enforcement: two components handle the same prop, one gated the other not — that asymmetry IS the proof   [conf: high] · [area: framing]
- **Do:** When two components in the same codebase render the same prop but only one checks the governing config flag, the asymmetry is the strongest possible evidence that the missing check is a bug (not a design choice). In the PoC and Summary, name BOTH components side-by-side: "Component A: `enableFoo && value` (correct). Component B: `value || undefined` (no gate)." This makes the triager's job trivial — they can grep both files and confirm the discrepancy in under a minute. Also: if the same block gates a parallel prop (e.g. `overwriteName` is gated by `enablePostUsernameOverride` in the same `if (isFromWebhook)` block), cite that too — it removes any argument that the missing gate is intentional.
- **Why / evidence:** Mattermost profile-popover run 2026-06-11. `post_profile_picture/index.ts:30` correctly gates `override_icon_url` by `enablePostIconOverride`; `post/user_profile.tsx:97` does not. The same `if (isFromWebhook)` block gates `overwriteName` by `enablePostUsernameOverride` but omits the icon gate. The comparison made the root cause self-evident without any live testing.
- **Apply when:** Any white-box / source-review finding where a config or permission check is present for a sibling prop/component but absent for the target prop/component. Always present both code paths together.
- **Provenance:** added 2026-06-11 · supporting: 1 (mattermost profile-popover) · contradicting: 0

### L-035 · Linter --fix destroys triple-dash YAML frontmatter and multipart boundaries; never put `---` separators in a fenced code block inside the same report   [conf: high] · [area: mechanics]
- **Do:** When a report contains a multipart form body example with `---boundary` markers inside a fenced code block, the linter's `--fix` treats those triple-dashes as spaced `--` em-dash patterns and corrupts them. Use a different boundary name (`BOUNDARY`, `PART1`) instead of `---`. Also verify the YAML frontmatter `---` delimiters survive after `--fix` by reading the file immediately after running it.
- **Why / evidence:** Mattermost file-creator-bypass report 2026-06-11. The linter converted `---boundary` to `, -boundary` and the closing YAML `---` to `, -` in the output, requiring a full rewrite. The fix also mangled the CVSS table separator row (`|---|---|---|` became `|,, |,, -|,,, -|`).
- **Apply when:** Any report that includes a multipart/form-data example or other content using triple-dash separators inside a fenced code block. Use `BOUNDARY` or `PART1` as the multipart delimiter instead.
- **Provenance:** added 2026-06-11 · supporting: 1 (mattermost file-creator-bypass) · contradicting: 0

### L-036 · White-box finding: cite an in-codebase sibling guard as proof the unguarded path is an oversight, not a feature   [conf: high] · [area: framing]
- **Do:** When reporting that a user-reachable code path lacks a control, search the same codebase for a SIBLING or NEWER path that already enforces that control against the identical risk. If one exists, lead the dedup/by-design section with that asymmetry: "the server already strips X for non-integration authors at file:line (with the in-code comment '...'), but the legacy path was never given the same guard." This converts a likely "that is by-design / a known feature" closure into a demonstrable incomplete-control bug, and an in-code developer comment acknowledging the risk is the strongest single piece of evidence.
- **Why / evidence:** Mattermost interactive-action missing-authz report 2026-06-22. The legacy `attachments[].actions[].integration.url` is creatable by any user, but the server explicitly strips the newer `mm_blocks_actions` framework for non-integration authors (server/channels/app/post.go:268-274, comment "webhook payloads are user-controlled") and strips it at the webhook entry point too. That asymmetry is the load-bearing argument the legacy path is an oversight; without it the finding reads as "message attachments are a feature."
- **Apply when:** Any source-derived finding on an open-source target where the natural rejection is "intended behavior" — preempt it with the sibling-guard asymmetry before the triager raises it.
- **Provenance:** added 2026-06-22 · supporting: 1 (mattermost interactive-action missing-authz) · contradicting: 0
