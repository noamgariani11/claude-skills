# fleet-hunt — standing lessons (read in Phase R, write back in Phase 6)

These are standing amendments to the skill doctrine, learned across sweeps. They sharpen
technique, host-scoring weights, and coverage **only** — they never relax a guardrail
(scope, read-only-first, stop-at-impact, no-auto-submit). Retire any lesson that conflicts.

## Active lessons
- **L-001 (standing doctrine):** the agent proposes, deterministic logic confirms. A candidate
  becomes a finding only when Phase 4 captures the machine-checkable **artifact** named in doc 29
  (`research/29-autonomous-validation-recipes.md`). Prose/confidence is never proof. This is the
  whole moat — never weaken it for throughput.
- **L-002:** dedup + score BEFORE spending solver budget (`host_scorer.py`). Subdomain-takeover and
  origin-leak are the top-priority signals; two-layer simhash+favicon dedup collapses mirror herds.
- **L-003:** ~half of even XBOW's submissions were dupes/informative/N-A. Phase 4.5 self-triage
  (scope + dedup-vs-disclosed + severity) is what protects acceptance rate — run it every time.
- **L-004 (frontier):** autonomous tools are weak at long business-logic *chains* (XBOW's own gap).
  Don't force them in the fleet — flag for a `/bug-hunt` deep run. This is the differentiation edge.
- **L-005 (recon reliability — 2026-06-05):** `hunt.sh` recon via Workflow agents is fragile at fleet
  scale. Three failure modes hit on the first Large sweep: (a) httpx **`-favicon`** flag fires an
  *un-timed* favicon fetch per host and HANGS on slow/dev hosts → whole probe returns **0 live** even
  though hosts are up. (b) Agents that daemonize a detached `_seq_driver.sh` loop survive `TaskStop`
  and saturate the box (**load 24 on 20 cores**); under saturation httpx times out and returns 0 →
  *false-negative recon*. (c) Consumer-brand programs with **explicit host lists** (nba 200, coupang 45,
  starbucks, temu) had their agent hunt.sh runs die empty. **Fix / standing recipe:** for explicit-host
  programs, skip enumeration — `dnsx`-resolve the `scope.md` `in:` hosts, then `httpx` the resolved set
  **WITHOUT `-favicon`** (`-timeout 10 -retries 1`); host_scorer dedups on simhash+title+size+server fine
  without favicon. Keep aggregate concurrency low; verify load < ~6 before probing. klarna-style BYOIP
  reverse-DNS (`*.v4.byoip.klarna.com`) swamps enum — filter it out.

## host_scorer.py weight tuning
Record here when a host signal converts to a real finding (raise its weight) or only ever
produces noise (lower it). The scorer's tables live in `research/tools/host_scorer.py`
(`RISKY_TECH`, `INTERESTING_TITLE`, `INTERESTING_HOST`). Tune from evidence, not intuition.

| signal | observed conversion | action |
|---|---|---|
| TAKEOVER-FINGERPRINT(+20) | **0/23** real (2026-06-05). Matched CloudFront/Akamai `"ERROR: The request could not be satisfied"` 403 page. Every CNAME resolved to a LIVE claimed distribution. | **BUG — fix scorer:** gate the takeover +20 on the host's CNAME target being **NXDOMAIN/unclaimed** (real dangling). A served CDN 403 error page is NOT a takeover. Until fixed, deterministically DNS-validate the whole ≥20 band (dig CNAME → A) before any solver budget; it's a pure FP generator on CDN-fronted estates. |
| possible-origin(cdn-fronted-siblings)(+4) | fired on most nba/verily hosts; did not convert this sweep | keep but low weight; it's a weak prior, not a finding |
| tech:globalprotect(+9) | flagged vls-efw-p.verily.com (24) correctly as high-value, but gateway `/ssl-vpn/*`=503 → not exploitable | keep weight; add a check: GlobalProtect *portal* w/ gateway 503 ≠ CVE-2024-3400 surface |

## Programs: keep vs. skip
| program | last swept | outcome | next sweep |
|---|---|---|---|
| robinhood | 2026-06-05 | CONFIRMED source-map disclosure (brokerportal/issuer-test.say.rocks, low); rich say.rocks/saytechnologies surface | **keep** |
| vodafone_oman | 2026-06-05 | CONFIRMED outdated WP6.2.2/EventON4.4(CVE-2024-0235)/WPML/WPBakery on www.vodafone.om | **keep** (confirm unauth endpoint + n-day policy) |
| kong | 2026-06-05 | konghq.com ES key (likely by-design) + internal Payload CMS admin URL; v3.13.0.2-ee | **keep → /bug-hunt** deep run |
| coupang_tw | 2026-06-05 | developers.tw.coupangcorp.com Rails+OpenAPI = BOLA target (DENY_REGEX bug fixed) | **keep → /bug-hunt** |
| verily | 2026-06-05 | huge surface (2434), GlobalProtect portal not exploitable | keep, re-sweep |
| nba-public | 2026-06-05 | WP hosts hardened+patched; cares.nba.com cache-contamination (needs active repro) | keep (cares handoff) |
| klarna | 2026-06-05 | BYOIP noise; 13 CloudFront-403 takeover FPs; mTLS APIs; scanner-banned | re-sweep authed only |
| twilio/superbet/meesho/3cx | 2026-06-05 | only active/needs-approval candidates | reconsider |
| starbucks_japan/temu/coinhako/wisdomtree/1password | 2026-06-05 | minimal/no surface | **skip** next sweep |
| okta (BC PAM) | 2026-06-22 | all surfaces auth-gated; needs provisioned PAM test account | **skip** without creds |
| chime (BC) | 2026-06-22 | QA envs reachable but all auth-gated; employer portal worth /bug-hunt with self-signup account | skip fleet; try /bug-hunt with creds |
| etoro-mbb-og (BC) | 2026-06-22 | API docs public; all app surfaces behind auth | skip fleet |
| fivetran-mbb-og (BC) | 2026-06-22 | all staging behind Google oauth2_proxy; no external surface | **skip** next sweep |
| fireblocks-mbb-og (BC) | 2026-06-22 | JWT required; no surface without API keys | **skip** without creds |
| rapyd (BC) | 2026-06-22 | 100+ sandboxapi IDOR candidates; needs 2 sandbox accounts for differential | **keep → /bug-hunt** with creds |

## Config-generation bugs to avoid (Phase 0)
- The per-program config agent set **over-broad `DENY_REGEX`** twice: coupang `(^|\.)coupang\.com$` denied
  the in-scope `tw.coupang.com` hosts; 3cx negative-lookahead denied `portal.3cx.com` itself. Both ALLOW
  regexes were already exact-anchored whitelists, so **DENY was redundant + harmful**. Rule: when ALLOW is
  an exact-anchored host whitelist, leave DENY empty unless excluding a specific in-allow host.
- Two agents returned `handle:"monk11"` (the researcher handle) instead of the program handle in structured
  output — harmless (paths were hardcoded) but verify file landing, don't trust the returned `handle` field.

## Validator false-positive patterns (auto-reject candidates)
- **CDN 403 "request could not be satisfied" ≠ subdomain takeover.** Auto-reject unless CNAME target is unclaimed (see weight table).
- **Non-resolving CNAME target ≠ takeover (the big one, 2026-06-05).** A dangling-CNAME scan over 11.5k klarna/verily/robinhood/twilio subdomains gave 253 "non-resolving target" hits → **0 real takeovers.** ~240 were internal-by-design: `internal-*.elb.amazonaws.com` (internal LBs, random suffixes — NOT claimable), `*.c2c.klarna.net`/`*.mk8s.klarna.net` (internal platform, private DNS), org-owned `*.cdn.cloudflare.net`. The other 13 pointed to 3rd-party SaaS but all **non-claimable patterns**: SendGrid assigned user IDs (`uXXXXX.wlYYY`), Amplify random app IDs (`dXXXX.amplifyapp.com`), Marketo/Freshdesk/Pendo org-bound instances. **Rule: takeover needs BOTH (a) deprovisioned target AND (b) attacker can REGISTER that exact resource. Internal LBs, random cloud IDs, and *.<org>.net are never (b).** Only user-chosen names (Heroku apps, GitHub Pages, classic S3 buckets) are claimable — verify provider-by-provider before flagging.
- **dnsx stalls at fleet scale** — `dnsx -cname -json` / `-resp-only` over 11k+ hosts hung at 0 output (twice). Use parallel `dig +short CNAME @1.1.1.1` via `xargs -P` instead, BUT under high `-P` dig captures resolver-timeout strings (`;; communications error`) as fake CNAMEs — filter `grep -vE 'communications error|Warning:|;;'` and re-verify survivors with retries + multiple resolvers before trusting.
- **Source maps convert unauthenticated** — a read-only `.js.map` existence sweep over 82 app hosts hit 12 hosts / 7 programs (incl. production robinhood brokerage portals + nba `id.nba.com` identity app). Low sev but the highest-yield no-account class. Pair with `trufflehog filesystem --only-verified` on the downloaded JS (0 FPs — verified-only is the right gate; it returned nothing across the whole fleet).
- **Frontend-embedded "secrets" that are public by design** (Segment write-key, scoped Elasticsearch/Algolia *search* keys doing client-side `_search` on one index) — not findings unless the key proves over-privileged. Check privilege/scope before reporting.
- **`SECRET_DO_NOT_PASS_THIS_OR_YOU_WILL_BE_FIRED`** in JS = axios's internal placeholder constant, not a leaked secret. Auto-ignore in secret scans.
- **Version disclosure on a *patched/current* version** (e.g. WP 6.9.4 in 2026) = info, not n-day. Map to CVE before queuing.

## 2026-06-22 BC sweep — new lessons

**L-006 (BugCrowd API migration):** `bc_recon.py` and `bc_program.py` were fully broken — BugCrowd replaced `/programs.json` with `/engagements.json`, changed the record shape (`briefUrl` replaces `program.url`; `rewardSummary.maxReward` replaces `rewards.maximum`), and the program-level API now requires auth. **Fixes shipped:** both tools updated to use `/engagements.json`; `_normalize_engagement()` converts the new shape; `fetch_target_groups()` now skips error-dict responses (`{"errors":[...]}` was passing the `isinstance(data, dict)` check and returning `[]` early, blocking the crowdstream fallback); crowdstream fallback parses `target` fields from recent public submissions. Tools are green as of 2026-06-22.

**L-007 (crowdstream scope fallback — when it works and when it doesn't):** Programs with active public submissions yield useful crowdstream-derived scope (5–20 targets). Programs with empty crowdstreams (zendesk, launchdarkly-mbb-og in this sweep) are auth-walled and must be dropped. If crowdstream returns nothing, the scope is unresolvable — drop the program rather than guessing.

**L-008 (httpx multi-port flag hangs):** `-ports 80,443,3000,4443,8000,8888` in the httpx call caused all 6 parallel jobs to hang for 5+ hours (0 output). Root cause: many dev/staging hosts time out on non-standard ports but httpx waits per-connection even with `-timeout 10` when probing 8 ports × 277 hosts at `-rl 10`. **Standing rule:** NEVER pass `-ports` to httpx in fleet mode — use default (80 + 443 only). The LESSONS.md already has L-005 about `-favicon`; add ports to the same rule.

**L-009 (host_scorer glob crossover):** `--glob 'output/targets/*/artifacts/*/httpx.jsonl'` picks up ALL programs ever hunted, not just the current fleet. On a mature workspace this mixes klarna/robinhood/verily/nba into the fleet queue. Always use explicit `--httpx path:prog` flags when the workspace has pre-existing data.

**L-010 (program selection — auth-walled fintech):** okta/chime/etoro/fivetran/fireblocks/rapyd are all professionally hardened. Every unauthenticated surface in this 6-program sweep was either a static SPA, a Cloudflare 403, or a standard public docs page. **None yielded reportable findings.** These programs pay high bounties *because* they're hard — the ROI is only good with valid API/app credentials. Next BC fleet should prefer programs that (a) have public API keys for sandbox (rapyd does, but requires 2 accounts for IDOR), (b) have self-signup (etoro, chime), or (c) have explicit researcher test account provisioning. Alternatively, pick lower-payout programs with more exposed attack surface.

**L-011 (program-specific recon notes):**
- **Okta PAM** (`personal.trexcloud.com`): Only interesting with a provisioned PAM test account; `oinmanager.trexcloud.com` is a public landing page only; `personal-admin.trexcloud.com` requires OIDC session. Skip in future sweeps without creds.
- **Fireblocks** (`sandbox-api.fireblocks.io`): JWT required for all calls; error returns 401 `{"message":"Unauthorized: JWT is missing"}`. Skip without test API keys.
- **Rapyd** (`sandboxapi.rapyd.net`): HMAC-SHA256 for all calls. Has rich IDOR surface (100+ historical sandboxapi customer/payment IDs in historical URLs) but needs two registered sandbox accounts for differential test. Worth a `/bug-hunt` deep run with creds.
- **Fivetran** (`staging.fivetran.com`, etc.): All staging/internal envs behind Google oauth2_proxy (corporate SSO). No external access path. Skip.
- **Chime**: QA envs exist and are reachable but all require Cloudflare + Rails/Next.js session auth. `workplace-qa.chime.com` (employer portal) is the highest-value surface; `/employer_portal/login` is accessible but not the API. Worth `/bug-hunt` with a registered employer account if self-signup is available.
