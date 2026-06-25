---
name: user-test-massive
description: |
  Statistically-grounded 360-persona panel review with cross-run learning. 14 cohorts
  (including Small Portfolio Landlord, Tax Consultant/CPA, Non-English Speaker, and a
  26-persona disability cohort with dyscalculia sub-type). 8 task tracks including
  document upload/evidence management, multi-property batch protest, and return-visit
  follow-up. 60-persona universal S0 benchmark with 20 sequential funnel personas.
  Proportional adaptive task allocation. Super-cohort analysis (Low-access /
  Target-market / Excluded-risk). UX Score 0-100 with Functional/Inclusive split,
  hard-floor CRITICAL flag, and regression alerting. Parallel fix tickets with
  verification scenarios, before/after copy, WCAG references, P1 qualitative overrides,
  dedup pass, and quick-wins section. TTL-based false positive suppression.
  Rolling learnings.md window with velocity tracking.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# /user-test-massive — 360-Person Statistically-Representative Panel with Learning

**360 personas. 14 cohorts. 8 task tracks. Super-cohort analysis. UX Score with Functional/Inclusive split. Parallel fix tickets with verification scenarios. Learning loop that gets smarter every run.**

---

## Statistical Framing

**N=360, 95% confidence:** ±5.2% aggregate. Super-cohort: ±7.9–8.3%. Task-level: ±14–17% (n=34–46). Cohort-level: ±17–21% (directional).

**Design:** Between-subjects. Each persona does exactly one task (except 20 sequential funnel personas who do S0→S1). No order effects.

**Universal benchmark pool (S0):** 60 personas — the longitudinal anchor. MoE ±12.7% — tight enough to detect a 10-point trust change across runs. Of these, 20 are **funnel follow-ons** who also attempt S1 immediately after S0, measuring cold-landing → onboarding conversion.

**Super-cohort analysis** runs alongside 14-cohort breakdown:
| Super-cohort | Cohorts | n | MoE |
|---|---|---|---|
| Low-access | 1, 2, 6, 8, 14 | ~140 | ±8.3% |
| Target market | 3, 4, 5, 10, 12, 13 | ~152 | ±7.9% |
| Excluded risk | 7, 9, 11 | ~68 | ±11.9% |

**Validity boundaries:**

| Claim | Valid? |
|---|---|
| "Overall completion was 67% ±5%" | Yes |
| "Low-access cohort struggled more than target market" | Yes (super-cohort, ±8%) |
| "Seniors completed onboarding at roughly half the rate of young adults" | Directional only (cohort n≈38, ±17%) |
| "Tax protest had the highest abandonment" | Yes (task-level ±14%) |
| "S0 trust rate improved 12 pts since last run" | Yes (S0 n=60, ±12.7%, 12 pts > MoE) |
| "S0 trust rate improved 8 pts since last run" | Marginal — flag as "directionally improved, within noise" |

---

## UX Score (0–100)

Composite computed directly from raw session results. Two sub-scores:

**Functional (max 55)** — can users do the job?
| Component | Max | Formula |
|---|---|---|
| S0 trust rate | 25 | `trust_count / s0_n × 25` |
| S0 completion | 20 | `completed / s0_n × 20` |
| S0 return intent | 10 | `would_return_yes / s0_n × 10` |

**Inclusive (max 45)** — who gets left behind?
| Component | Max | Formula |
|---|---|---|
| Literacy equity (T1/T2) | 15 | `T1T2_completed / T1T2_n × 15` |
| Accessibility | 20 | `disability_completed / disability_n × 20` |
| Vocab clarity | 10 | `max(0, 10 − unique_jargon_count × 1.0)` |

**Display:** `UX Score: 71/100 (Functional 42/55 · Inclusive 29/45)`

**🚨 CRITICAL flag:** Appended when any component scores below 30% of its max (trust <7.5, completion <6, return <3, literacy <4.5, a11y <6, vocab <3). Visual grade caps at "Struggling" regardless of total.

**⚠ REGRESSION:** Triggered when total drops >8 pts OR any component drops >5 pts vs. prior run. When triggered: block the standard offer, replace with "Regression detected — implement P1 fix tickets before running again." Auto-promote all fix tickets touching the regressed dimension to P1.

**Score bands:**
- 90–100 Exceptional | 75–89 Good | 60–74 Needs work | 45–59 Struggling | <45 Broken

**Funnel conversion metric** (separate from score): `s0_to_s1_conversion = funnel_personas_completed_s1 / funnel_personas_n`. This is the single most important marketing metric — what fraction of cold-landing visitors successfully onboard?

---

## Learning System Overview

Every run produces:
- **`baseline.json`** — overwritten each run. Stores: aggregate rates, super-cohort + task + cohort verdicts, UX Score + breakdown + velocity, exit_trigger_clusters, per_task_dropout_step, confirmed_issue_run_counts, suppressed_false_positives with TTL.
- **`learnings.md`** — append-only. Active Window (last 3 runs full detail) + Run Archive (older runs single-line). Vocabulary debt tracks first_seen/last_seen; resolved terms auto-move to a Resolved section.

**Learning loop each run:**
1. Load prior baseline and extract TTL-valid false positive suppressions
2. Compute proportional adaptive allocation from prior completion rates
3. Run sessions, compute UX Score + Functional/Inclusive split + critical flag
4. Check regression vs. prior run; emit ⚠ REGRESSION if triggered
5. Synthesize cohorts + super-cohorts + tasks in parallel
6. Grand synthesis with delta table (FIXED/STILL_PRESENT/REGRESSED/NEW)
7. Generate parallel fix tickets (4 category agents + conditional trust agent + dedup pass)
8. Apply qualitative P1 overrides
9. Save updated baseline.json + append to learnings.md
10. Update Active Window; push old runs to archive

---

## Phase 0: Setup

### 0.1 — Detect URL
```bash
for port in 3000 3001 4000 5173 8080; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" 2>/dev/null)
  [ "$code" != "000" ] && echo "FOUND: http://localhost:$port" && break
done
```
Accept user-provided URL. Fall back to dev server. Stop and ask if nothing found.

### 0.2 — Auth wall check
```bash
curl -sI -L "$URL" 2>/dev/null | grep -Ei "^location:" | tail -1
curl -s "$URL" 2>/dev/null | grep -Ei "sign[ -]?in|log[ -]?in|please authenticate" | head -3
```
Auth wall → ask for credentials. No credentials → test pre-auth surface only; note prominently.

### 0.3 — App context read
Establish: what does this app do, what vocabulary does it assume, who is the apparent target user, what are the primary flows.

**Default task definitions:**

| ID | Name | Description | Time |
|---|---|---|---|
| S0 | Universal First Impression | Land cold. Understand what the app does. Try the primary CTA. Form a trust judgment. | 3 min |
| S1 | Onboarding / Discovery | First-time user. Get your first property set up or complete onboarding. | 8 min |
| S2 | Operational Core | Manage several properties. Check rent status, review a lease, pull a report. | 8 min |
| S3 | Tax Protest Workflow | Assessed value came in high. File an informal protest or set up a protest. | 10 min |
| S4 | Mobile Snapshot | On your phone between meetings. Check open work orders and upcoming lease expirations. | 5 min |
| S5 | Trust / Pricing Decision | Evaluating whether to pay. Find pricing, understand what you get, decide. | 6 min |
| S6 | Document Upload & Evidence | Upload appraisal evidence for a protest. Attach photos, a lease, or a comp report. | 8 min |
| S7 | Multi-Property Batch Protest | You own 8 properties. File protests on all of them without doing each one individually. | 10 min |
| S8 | Return Visit / Notification | You got an email notification. Click through and find where you left off. | 5 min |

### 0.4 — Setup output
```bash
_DATE=$(date +%Y%m%d-%H%M%S)
mkdir -p .gstack/user-test-massive-reports
_REPORT_FILE=".gstack/user-test-massive-reports/massive-${_DATE}.md"
_FIXES_FILE=".gstack/user-test-massive-reports/fix-tickets-run${RUN_NUMBER}.md"
_BASELINE_FILE=".gstack/user-test-massive-reports/baseline.json"
_LEARNINGS_FILE=".gstack/user-test-massive-reports/learnings.md"
```

### 0.5 — Load Prior State

```bash
cat .gstack/user-test-massive-reports/baseline.json 2>/dev/null || echo "NO_BASELINE"
cat .gstack/user-test-massive-reports/learnings.md 2>/dev/null || echo "NO_LEARNINGS"
```

**Adaptive task allocation (proportional formula):**

Default allocations: `S1=40, S2=38, S3=46, S4=36, S5=38, S6=34, S7=34, S8=34` (total=300)

If prior baseline exists, adjust each task:
```
delta_i = round((0.5 − completion_rate_i) × 40)
  → maps: 0%→+20, 25%→+10, 50%→0, 75%→−10, 100%→−20
new_i = clamp(prior_allocation_i + delta_i, 30, 78)
```
After clamping, rebalance to total=300: if over, subtract from largest; if under, add to lowest-completion tasks.

**TTL false positive extraction:**
From prior baseline `suppressed_false_positives` array, keep only entries where `suppressed_until_run > run_number`. Pass the surviving strings as `verified_false_positives` to grand synthesis.

If no baseline: use default allocations. Run #1. Note prominently.

Print adaptive allocation table before generating personas.

---

## Phase 1: Persona Pool (360 personas)

### The 14 Cohorts

| # | Cohort | n | Anchor | MoE |
|---|---|---|---|---|
| 1 | **Senior Low-Tech** | 38 | 65+, ~60% low/medium digital literacy | ±17% |
| 2 | **Low-Digital Mainstream** | 36 | PIAAC Level 1–2, ages 40–65 | ±17% |
| 3 | **Capable Mainstream** | 32 | Modal US adult 25–54, suburban, medium literacy | ±17% |
| 4 | **Domain Experts** | 26 | Investors, large-portfolio managers, tax attorneys | ±19% |
| 5 | **Young Mobile-Native** | 26 | 18–34, 97% smartphone, mobile-first | ±19% |
| 6 | **Smartphone-Only / Constrained** | 24 | No home broadband, data limits | ±20% |
| 7 | **Accessibility / Disability** | 26 | 26% of US adults have a disability (CDC) | ±19% |
| 8 | **Rural / Flyover** | 20 | 21% rural, 71% broadband | ±22% |
| 9 | **Skeptic Researcher** | 18 | High TRI discomfort/insecurity | ±23% |
| 10 | **Power User / Early Adopter** | 16 | PIAAC Level 3+, tech-curious | ±25% |
| 11 | **Adjacent Non-Owner** | 24 | Renters, low domain vocabulary | ±20% |
| 12 | **Small Portfolio Landlord** | 30 | Owns 2–10 units, not a professional, emotionally invested in assessments | ±18% |
| 13 | **Tax Consultant / CPA** | 22 | Acts on behalf of clients, keyboard-heavy, compares to competing tools | ±21% |
| 14 | **Non-English Speaker** | 22 | Primary language not English; ~14% of US adults; overrepresented in TX/DCAD market | ±21% |

**Total: 360 personas** | Aggregate MoE: ±5.2%

### Disability Cohort (Cohort 7, n=26)

| Sub-type | n | Behavioral instructions |
|---|---|---|
| **Cognitive / ADHD / Dyslexia** | 7 | Loses focus mid-flow, re-reads, overwhelmed by dense text, skips instructions, loses track of progress |
| **Dyscalculia** | 5 | Numerical processing difficulty. Assessed values, cap rates, % reductions, and dollar comparisons are confusing. Needs clear plain-English framing of numbers. ~6% of adults, directly impactful for financial/RE apps. |
| **Low Vision** | 6 | 150% zoom. Cannot read small text. Relies on labels not icons. Color-only indicators invisible. |
| **Motor / Keyboard-Only** | 5 | Tab/Enter navigation only. No drag-and-drop. Hover-only menus are hard stops. Reports `keyboard_navigated` true/false. |
| **Deaf / Hard of Hearing** | 3 | Notes audio-only alerts, uncaptioned video, sound-dependent feedback. |

### Task Assignment Matrix

**Universal pool (60 personas):** Proportionally stratified across all 14 cohorts. 20 are flagged `funnel_follow_on: true` (they also complete S1 after S0).

**Scenario tasks (300 total, use adaptive allocation):**

| Task | Primary cohorts | Secondary |
|---|---|---|
| S1 Onboarding | 1, 2, 11, 14 | 3, 12 |
| S2 Operational Core | 3, 4, 12 | 7 (a11y on core flow) |
| S3 Tax Protest | 4, 9, 10, 13 | 3, 12 |
| S4 Mobile Snapshot | 5, 6, 8 | 7 (disability on mobile) |
| S5 Trust / Pricing | 9, 11 | 2, 3, 14 |
| S6 Document Upload | 4, 12, 13 | 7 (a11y on upload) |
| S7 Batch Protest | 4, 12, 13 | 10 |
| S8 Return Visit | 1, 2, 3, 14 | 5 (mobile return) |

**Rules:** Never assign newcomers to S3/S7. Never assign smartphone-only to S2/S7.

### Per-Persona Fields

Name, age, cohort, task_assigned, device, smartphone_only, disability_type, digital_literacy_tier (T1–T4), domain_expertise (professional/adjacent/newcomer), **backstory** (one sentence: occupation + why here today + how they heard about it), **assigned_jargon_term** (one term pre-assigned from vocabulary debt list — forces variance), **prior_experience** (first_visit | returning_stuck | returning_success), goal, time_limit, biggest_concern, funnel_follow_on (true/false).

Print a compact summary table before launching.

---

## Phase 2: Launch the Workflow

```javascript
export const meta = {
  name: 'user-test-massive',
  description: 'Run 360-persona representative panel with UX Score, super-cohorts, and fix tickets',
  phases: [
    { title: 'Sessions', detail: '360 persona sessions via pipeline' },
    { title: 'Synthesis', detail: 'Cohort + super-cohort + task agents in parallel' },
    { title: 'Grand Synthesis', detail: 'Delta analysis, UX Score, regression check' },
    { title: 'Actionable Fixes', detail: '4-5 parallel fix agents + dedup pass' },
  ],
}

const PERSONA_SCHEMA = {
  type: 'object',
  required: ['name', 'cohort', 'cohort_name', 'task_assigned', 'device', 'smartphone_only',
             'digital_literacy_tier', 'domain_expertise', 'goal', 'outcome',
             'arrival_impression', 'would_return', 'trust_verdict', 'trust_reason',
             'key_quote', 'pages_visited'],
  properties: {
    name: { type: 'string' },
    cohort: { type: 'number' },
    cohort_name: { type: 'string' },
    task_assigned: { type: 'string' },
    device: { type: 'string', enum: ['desktop', 'mobile'] },
    smartphone_only: { type: 'boolean' },
    funnel_follow_on: { type: 'boolean' },
    funnel_outcome: { type: ['string', 'null'], enum: ['completed', 'partial', 'gave_up', null] },
    funnel_friction: { type: ['string', 'null'] },
    disability_type: { type: ['string', 'null'] },
    accessibility_barrier: { type: ['string', 'null'] },
    keyboard_navigated: { type: ['boolean', 'null'] },
    digital_literacy_tier: { type: 'string', enum: ['T1_reluctant', 'T2_assisted', 'T3_capable', 'T4_power'] },
    domain_expertise: { type: 'string', enum: ['professional', 'adjacent', 'newcomer'] },
    prior_experience: { type: 'string', enum: ['first_visit', 'returning_stuck', 'returning_success'] },
    age: { type: 'number' },
    goal: { type: 'string' },
    outcome: { type: 'string', enum: ['completed', 'partial', 'gave_up'] },
    steps_completed: { type: ['number', 'null'] },
    arrival_impression: { type: 'string' },
    jargon_confusion: { type: ['string', 'null'] },
    assigned_jargon_encountered: { type: ['boolean', 'null'] },
    biggest_friction: { type: ['string', 'null'] },
    biggest_delight: { type: ['string', 'null'] },
    would_return: { type: ['boolean', 'string'] },
    trust_verdict: { type: 'string', enum: ['trust', 'neutral', 'distrust'] },
    trust_reason: { type: 'string' },
    key_quote: { type: 'string' },
    pages_visited: { type: 'array', items: { type: 'string' } },
    confusion_moment: { type: ['string', 'null'] },
    exit_trigger: { type: ['string', 'null'] },
  }
}

const COHORT_SCHEMA = {
  type: 'object',
  required: ['cohort_number', 'cohort_name', 'n', 'completion_rate', 'return_rate',
             'trust_rate', 'margin_of_error', 'top_friction', 'top_delight',
             'cohort_verdict', 'representative_quote'],
  properties: {
    cohort_number: { type: ['number', 'string'] },
    cohort_name: { type: 'string' },
    n: { type: 'number' },
    tasks_covered: { type: 'array', items: { type: 'string' } },
    completion_rate: { type: 'number' },
    return_rate: { type: 'number' },
    trust_rate: { type: 'number' },
    margin_of_error: { type: 'number' },
    top_friction: { type: 'string' },
    top_delight: { type: 'string' },
    jargon_failures: { type: 'array', items: { type: 'string' } },
    accessibility_barriers: { type: 'array', items: { type: 'string' } },
    cohort_verdict: { type: 'string', enum: ['loves_it', 'mixed', 'struggles', 'bounces'] },
    representative_quote: { type: 'string' },
  }
}

const TASK_SCHEMA = {
  type: 'object',
  required: ['task_id', 'task_name', 'n', 'completion_rate', 'margin_of_error',
             'top_friction', 'top_delight', 'task_verdict', 'demographic_split'],
  properties: {
    task_id: { type: 'string' },
    task_name: { type: 'string' },
    n: { type: 'number' },
    completion_rate: { type: 'number' },
    partial_rate: { type: 'number' },
    gave_up_rate: { type: 'number' },
    modal_dropout_step: { type: ['string', 'null'] },
    margin_of_error: { type: 'number' },
    top_friction: { type: 'string' },
    top_delight: { type: 'string' },
    jargon_failures: { type: 'array', items: { type: 'string' } },
    task_verdict: { type: 'string', enum: ['works_well', 'needs_work', 'broken'] },
    demographic_split: {
      type: 'object',
      properties: {
        expert_completion: { type: 'number' },
        newcomer_completion: { type: 'number' },
        mobile_completion: { type: 'number' },
        desktop_completion: { type: 'number' },
        low_literacy_completion: { type: 'number' },
        high_literacy_completion: { type: 'number' },
      }
    },
    representative_quote: { type: 'string' },
  }
}

const LEARNING_SCHEMA = {
  type: 'object',
  required: ['run_number', 'baseline_json', 'run_summary_md', 'delta_table'],
  properties: {
    run_number: { type: 'number' },
    baseline_json: { type: 'object' },
    run_summary_md: { type: 'string' },
    delta_table: {
      type: 'array',
      items: {
        type: 'object',
        required: ['finding', 'status', 'count', 'cohorts'],
        properties: {
          finding: { type: 'string' },
          status: { type: 'string', enum: ['FIXED', 'STILL_PRESENT', 'REGRESSED', 'NEW'] },
          count: { type: 'number' },
          run_count: { type: 'number' },
          cohorts: { type: 'array', items: { type: 'string' } },
          severity_trend: { type: 'string', enum: ['worsening', 'stable', 'improving'] },
          notes: { type: 'string' },
        }
      }
    },
    exit_trigger_clusters: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          cluster_name: { type: 'string' },
          count: { type: 'number' },
          example_triggers: { type: 'array', items: { type: 'string' } },
          tasks_affected: { type: 'array', items: { type: 'string' } },
        }
      }
    },
    per_task_dropout_step: { type: 'object' },
    next_run_recommendations: { type: 'array', items: { type: 'string' } },
    new_false_positives_to_suppress: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          finding: { type: 'string' },
          suppressed_until_run: { type: 'number' },
          reason: { type: 'string' },
        }
      }
    },
  }
}

const FIXES_SCHEMA = {
  type: 'object',
  required: ['fixes'],
  properties: {
    fixes: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'priority', 'category', 'title', 'problem', 'specific_fix',
                   'file_hint', 'personas_affected', 'effort', 'metric_impact', 'verification_scenario'],
        properties: {
          id: { type: 'string' },
          priority: { type: 'string', enum: ['P1', 'P2', 'P3'] },
          p1_override_reason: { type: ['string', 'null'] },
          category: { type: 'string', enum: ['copy', 'ux', 'accessibility', 'mobile', 'onboarding', 'trust'] },
          title: { type: 'string' },
          problem: { type: 'string' },
          specific_fix: { type: 'string' },
          before_after: {
            type: ['object', 'null'],
            properties: {
              before: { type: 'string' },
              after: { type: 'string' },
            }
          },
          wcag_criterion: { type: ['string', 'null'] },
          file_hint: { type: 'string' },
          personas_affected: { type: 'number' },
          effort: { type: 'string', enum: ['XS', 'S', 'M', 'L'] },
          metric_impact: { type: 'string' },
          verification_scenario: { type: 'string' },
        }
      }
    }
  }
}

const { url, personas, tasks, prior_baseline, verified_false_positives, run_number } = args

phase('Sessions')

const results = await pipeline(
  personas,
  (persona) => agent(
    `You are ${persona.name}, ${persona.age} years old.
Backstory: ${persona.backstory}
Cohort: "${persona.cohort_name}"
Task: ${persona.task_assigned} — ${tasks[persona.task_assigned]}
Prior experience with this app: ${persona.prior_experience === 'first_visit' ? 'First time here.' : persona.prior_experience === 'returning_stuck' ? 'You used this before and got stuck. You\'re back to try again, skeptical.' : 'You\'ve used this before successfully. You\'re back for a specific follow-up.'}

Digital literacy: ${persona.digital_literacy_tier}
${persona.digital_literacy_tier === 'T1_reluctant' ? '→ Struggle with unfamiliar software. Anxious when unclear. Give up rather than explore.' : ''}
${persona.digital_literacy_tier === 'T2_assisted' ? '→ Follow instructions but get stuck on jargon and multi-step flows.' : ''}
${persona.digital_literacy_tier === 'T3_capable' ? '→ Comfortable, figure things out, push through occasional confusion.' : ''}
${persona.digital_literacy_tier === 'T4_power' ? '→ Explore deeply, read everything, find edge cases, have high expectations.' : ''}

Domain expertise: ${persona.domain_expertise}
${persona.domain_expertise === 'professional' ? '→ Know property management, real estate, and tax representation deeply.' : ''}
${persona.domain_expertise === 'adjacent' ? '→ Some familiarity but not a specialist.' : ''}
${persona.domain_expertise === 'newcomer' ? '→ "ARB," "NOI," "cap rate," "homestead exemption" are unfamiliar terms.' : ''}

Watch specifically for the term "${persona.assigned_jargon_term}" — note if you encounter it and whether it confused you (record in assigned_jargon_encountered).

Device: ${persona.device}${persona.smartphone_only ? ' (SMARTPHONE ONLY — no home broadband, data limits, prone to interruptions)' : ''}

${persona.disability_type ? `Disability: ${persona.disability_type}
${persona.disability_type === 'cognitive_adhd' ? '→ ADHD: lose focus mid-flow, overwhelmed by dense text, lose track of progress.' : ''}
${persona.disability_type === 'dyscalculia' ? '→ Dyscalculia: numbers, percentages, assessed values, and cap rates are confusing. You need plain-English framing of all numerical content. Dollar amounts that aren\'t explicitly labeled are disorienting.' : ''}
${persona.disability_type === 'low_vision' ? '→ 150% zoom. Small text invisible. Rely on text labels not icons. Color-only indicators indistinguishable.' : ''}
${persona.disability_type === 'motor_keyboard' ? '→ Keyboard only (Tab, Enter, arrows). No drag-and-drop. Hover-only menus are hard stops. Set keyboard_navigated true/false.' : ''}
${persona.disability_type === 'deaf_hoh' ? '→ Note audio-only alerts, uncaptioned video, or sound-dependent feedback.' : ''}` : ''}

${persona.funnel_follow_on ? `FUNNEL TEST: After completing S0, immediately attempt S1 (Onboarding). Report your S0 experience in the standard fields and your S1 attempt in funnel_outcome + funnel_friction.` : ''}

Your goal: ${persona.goal}
Time limit: ${persona.time_limit}
Biggest concern: ${persona.biggest_concern}

Navigate to ${url}. Attempt your task. 3–5 interactions max (up to 8 for complex workflows).
Return structured JSON only.`,
    {
      label: `${persona.name} (C${persona.cohort} ${persona.digital_literacy_tier} ${persona.task_assigned})`,
      phase: 'Sessions',
      schema: PERSONA_SCHEMA,
      model: 'haiku',
      effort: 'low',
    }
  )
)

const valid = results.filter(Boolean)
log(`${valid.length}/360 persona sessions completed`)

// UX Score computation
const s0All = valid.filter(r => r.task_assigned === 'S0')
const s0TrustRate = s0All.length > 0 ? s0All.filter(r => r.trust_verdict === 'trust').length / s0All.length : 0
const s0CompletionRate = s0All.length > 0 ? s0All.filter(r => r.outcome === 'completed').length / s0All.length : 0
const s0ReturnRate = s0All.length > 0 ? s0All.filter(r => r.would_return === true || r.would_return === 'yes' || r.would_return === 'Yes').length / s0All.length : 0
const lowLit = valid.filter(r => r.digital_literacy_tier === 'T1_reluctant' || r.digital_literacy_tier === 'T2_assisted')
const lowLitCompletion = lowLit.length > 0 ? lowLit.filter(r => r.outcome === 'completed').length / lowLit.length : 0
const disabilityP = valid.filter(r => r.disability_type !== null && r.disability_type !== undefined)
const a11yCompletion = disabilityP.length > 0 ? disabilityP.filter(r => r.outcome === 'completed').length / disabilityP.length : 0
const uniqueJargon = [...new Set(valid.filter(r => r.jargon_confusion).map(r => r.jargon_confusion))]
const vocabScore = Math.max(0, 10 - uniqueJargon.length)

const trustPts = Math.round(s0TrustRate * 25)
const completionPts = Math.round(s0CompletionRate * 20)
const returnPts = Math.round(s0ReturnRate * 10)
const litPts = Math.round(lowLitCompletion * 15)
const a11yPts = Math.round(a11yCompletion * 20)
const vocabPts = Math.round(vocabScore)

const functionalScore = trustPts + completionPts + returnPts
const inclusiveScore = litPts + a11yPts + vocabPts
const uxScore = functionalScore + inclusiveScore

const criticalFlag = trustPts < 7 || completionPts < 6 || returnPts < 3 || litPts < 4 || a11yPts < 6 || vocabPts < 3

const uxScorePrior = prior_baseline && prior_baseline.ux_score ? prior_baseline.ux_score.total : null
const uxScoreDelta = uxScorePrior !== null ? uxScore - uxScorePrior : null
const priorBreakdown = prior_baseline && prior_baseline.ux_score && prior_baseline.ux_score.breakdown
const regressionDetected = uxScoreDelta !== null && (
  uxScoreDelta < -8 ||
  (priorBreakdown && (
    trustPts - priorBreakdown.trust_s0.score < -5 ||
    a11yPts - priorBreakdown.accessibility.score < -5 ||
    litPts - priorBreakdown.literacy_equity.score < -5 ||
    completionPts - priorBreakdown.completion_s0.score < -5
  ))
)

// Funnel conversion
const funnelPersonas = valid.filter(r => r.funnel_follow_on === true)
const funnelConversion = funnelPersonas.length > 0
  ? funnelPersonas.filter(r => r.funnel_outcome === 'completed').length / funnelPersonas.length
  : null

log(`UX Score: ${uxScore}/100 (Functional ${functionalScore}/55 · Inclusive ${inclusiveScore}/45)${criticalFlag ? ' 🚨 CRITICAL' : ''}${uxScoreDelta !== null ? ` | ${uxScoreDelta >= 0 ? '+' : ''}${uxScoreDelta} vs run #${prior_baseline.run_number}` : ' | baseline'}`)
if (regressionDetected) log('⚠ REGRESSION DETECTED — score or component dropped significantly vs prior run')
if (funnelConversion !== null) log(`Funnel conversion (S0→S1): ${Math.round(funnelConversion * 100)}% of ${funnelPersonas.length} funnel personas`)

phase('Synthesis')

const byCohort = {}
const byTask = {}
for (const r of valid) {
  if (!byCohort[r.cohort]) byCohort[r.cohort] = []
  byCohort[r.cohort].push(r)
  if (!byTask[r.task_assigned]) byTask[r.task_assigned] = []
  byTask[r.task_assigned].push(r)
}

const SUPER_COHORT_DEFS = [
  { name: 'Low-access', key: 'low_access', cohorts: [1, 2, 6, 8, 14], description: 'Senior, low-digital, smartphone-only, rural, non-English speaker' },
  { name: 'Target market', key: 'target_market', cohorts: [3, 4, 5, 10, 12, 13], description: 'Capable mainstream, domain experts, mobile-native, power users, small landlords, tax consultants' },
  { name: 'Excluded risk', key: 'excluded_risk', cohorts: [7, 9, 11], description: 'Disability, skeptic researcher, adjacent non-owner' },
]

const allSynthesis = await parallel([
  ...Object.entries(byCohort).map(([cohortNum, cohortResults]) => () =>
    agent(
      `Synthesize ${cohortResults.length} persona results for cohort ${cohortNum} ("${cohortResults[0].cohort_name}").
Tasks covered: ${[...new Set(cohortResults.map(r => r.task_assigned))].join(', ')}
Results: ${JSON.stringify(cohortResults, null, 2)}
Compute: completion_rate, return_rate, trust_rate. margin_of_error = 1.96*sqrt(0.25/${cohortResults.length}).
top_friction, top_delight. jargon_failures (terms confusing 2+ personas).
accessibility_barriers: all accessibility_barrier values. cohort_verdict: loves_it/mixed/struggles/bounces.`,
      { label: `cohort-${cohortNum}`, phase: 'Synthesis', schema: COHORT_SCHEMA }
    )
  ),
  ...SUPER_COHORT_DEFS.map(sc => () => {
    const scPersonas = valid.filter(r => sc.cohorts.includes(r.cohort))
    return agent(
      `Synthesize ${scPersonas.length} personas for super-cohort "${sc.name}" (${sc.description}).
Results: ${JSON.stringify(scPersonas, null, 2)}
Compute completion_rate, return_rate, trust_rate, margin_of_error = 1.96*sqrt(0.25/${scPersonas.length}).
top_friction, top_delight. cohort_verdict. MoE is ~±${Math.round(196 * Math.sqrt(0.25 / scPersonas.length))}% — statistically usable.`,
      { label: `supercohort-${sc.key}`, phase: 'Synthesis', schema: COHORT_SCHEMA }
    )
  }),
  ...Object.entries(byTask).map(([taskId, taskResults]) => () =>
    agent(
      `Synthesize ${taskResults.length} persona results for task "${taskId}".
Results: ${JSON.stringify(taskResults, null, 2)}
Compute: completion_rate, partial_rate, gave_up_rate, margin_of_error.
modal_dropout_step: the most common step at which personas with outcome=gave_up stopped (e.g. "step 2 of 5 — after seeing upload form").
demographic_split: experts vs newcomers, mobile vs desktop, T1/T2 vs T3/T4.
task_verdict: works_well (>70%), needs_work (40–70%), broken (<40%).
NEVER compare completion rates across different tasks.`,
      { label: `task-${taskId}`, phase: 'Synthesis', schema: TASK_SCHEMA }
    )
  ),
])

const nCohorts = Object.keys(byCohort).length
const cohortReports = allSynthesis.slice(0, nCohorts).filter(Boolean)
const superCohortReports = allSynthesis.slice(nCohorts, nCohorts + 3).filter(Boolean)
const taskReports = allSynthesis.slice(nCohorts + 3).filter(Boolean)
log(`${cohortReports.length} cohort + ${superCohortReports.length} super-cohort + ${taskReports.length} task reports synthesized`)

phase('Grand Synthesis')

const hasPrior = prior_baseline && prior_baseline.top_frictions

const grandReport = await agent(
  `You are synthesizing run #${run_number} of a 360-persona panel review of ${url}.
Aggregate MoE ±5.2%. Super-cohort MoE ±8–12% (statistically usable). Cohort MoE ±17–25% (directional). Task MoE ±14–17%.
CRITICAL: Never compare completion rates across different tasks.
${verified_false_positives && verified_false_positives.length > 0 ? `Suppress these verified false positives: ${verified_false_positives.join('; ')}` : ''}
${regressionDetected ? `⚠ REGRESSION DETECTED: UX Score dropped ${Math.abs(uxScoreDelta)} pts. Highlight prominently at top.` : ''}
${criticalFlag ? `🚨 CRITICAL: At least one UX Score component is below 30% of its max. Identify which and flag prominently.` : ''}

Cohort reports: ${JSON.stringify(cohortReports, null, 2)}
Super-cohort reports: ${JSON.stringify(superCohortReports, null, 2)}
Task reports: ${JSON.stringify(taskReports, null, 2)}
All ${valid.length} results: ${JSON.stringify(valid, null, 2)}
${hasPrior ? `Prior baseline (run #${prior_baseline.run_number}): ${JSON.stringify(prior_baseline, null, 2)}` : ''}
${funnelConversion !== null ? `Funnel conversion (S0→S1): ${Math.round(funnelConversion * 100)}% of ${funnelPersonas.length} personas` : ''}

Produce markdown synthesis:

${regressionDetected ? '## ⚠ REGRESSION ALERT\nSpecify which component(s) dropped and by how much. This section appears first.\n\n' : ''}
## STATISTICAL FRAMING
## SUPER-COHORT SPLIT (primary analytical unit)
Low-access vs Target-market vs Excluded-risk — completion, trust, return rates. Which group drives the aggregate number up or down?
## OVERALL METRICS (S0 pool, n=60, ±12.7%)
Trust, completion, return. Funnel conversion if available.
## TASK-BY-TASK VERDICTS (±14–17%)
Verdict, completion, modal dropout step, top friction, demographic gap, quote.
## DOMAIN EXPERTISE SPLIT + VOCABULARY DEAD ZONES
Every jargon term confusing 3+ newcomers. Dyscalculia-specific number-confusion moments.
## DIGITAL LITERACY SPLIT
At what tier does the experience become acceptable?
## ACCESSIBILITY AUDIT
By sub-type (cognitive, dyscalculia, low vision, motor/keyboard, deaf/HoH). Keyboard nav pass rate.
## DEVICE / CONNECTION SPLIT
## MARKET FIT MAP (all 14 cohorts)
## CONSENSUS FRICTION (≥54 personas = 15%)
Top 5. Exclude verified false positives.
## CONSENSUS DELIGHT (≥54 personas)
Top 5.
## TRUST ANALYSIS
${hasPrior ? `## CHANGES SINCE RUN #${prior_baseline.run_number}
FIXED / STILL_PRESENT / REGRESSED / NEW. Prior S0 trust: ${prior_baseline.universal_s0?.trust_rate ? Math.round(prior_baseline.universal_s0.trust_rate * 100) + '%' : 'no data'}.` : '## FIRST RUN BASELINE'}
## THE 7 MOST IMPORTANT QUOTES
Low-literacy | Domain expert | Disability (dyscalculia preferred) | Skeptic | Mobile-only | Delighted | Devastated
## ONE-SENTENCE VERDICT`,
  { label: 'grand-synthesis', phase: 'Grand Synthesis' }
)

const learningUpdate = await agent(
  `Update learning record for run #${run_number} of ${url}.

Current metrics:
- n=${valid.length}, UX Score ${uxScore}/100 (F:${functionalScore}/55 I:${inclusiveScore}/45)${criticalFlag ? ' CRITICAL' : ''}${regressionDetected ? ' REGRESSION' : ''}
- Tasks: ${JSON.stringify(taskReports.map(t => ({ id: t.task_id, verdict: t.task_verdict, completion: t.completion_rate, friction: t.top_friction, dropout_step: t.modal_dropout_step })))}
- Cohorts: ${JSON.stringify(cohortReports.map(c => ({ id: c.cohort_number, name: c.cohort_name, verdict: c.cohort_verdict })))}
- Super-cohorts: ${JSON.stringify(superCohortReports.map(s => ({ name: s.cohort_name, verdict: s.cohort_verdict, completion: s.completion_rate })))}
- Top frictions: ${JSON.stringify(valid.filter(r => r.biggest_friction).map(r => r.biggest_friction).slice(0, 50))}
- Exit triggers: ${JSON.stringify(valid.filter(r => r.exit_trigger).map(r => r.exit_trigger).slice(0, 50))}
- Vocab debt: ${JSON.stringify(uniqueJargon)}
- S0 results: ${JSON.stringify(s0All.map(r => ({ trust: r.trust_verdict, outcome: r.outcome, would_return: r.would_return })))}
- Prior baseline: ${hasPrior ? JSON.stringify(prior_baseline) : 'null'}

Produce a learning_update with:

baseline_json structured as:
{
  run_number: ${run_number},
  url: "${url}",
  n_completed: ${valid.length},
  aggregate: { completion_rate, return_rate, trust_rate },
  universal_s0: { completion_rate, trust_rate, return_rate, n: ${s0All.length} },
  funnel_conversion: ${funnelConversion},
  ux_score: {
    total: ${uxScore}, prior: ${uxScorePrior}, delta: ${uxScoreDelta},
    functional: ${functionalScore}, inclusive: ${inclusiveScore},
    critical_flag: ${criticalFlag}, regression_detected: ${regressionDetected},
    breakdown: {
      trust_s0: { score: ${trustPts}, max: 25, rate: ${s0TrustRate} },
      completion_s0: { score: ${completionPts}, max: 20, rate: ${s0CompletionRate} },
      return_s0: { score: ${returnPts}, max: 10, rate: ${s0ReturnRate} },
      literacy_equity: { score: ${litPts}, max: 15, rate: ${lowLitCompletion} },
      accessibility: { score: ${a11yPts}, max: 20, rate: ${a11yCompletion} },
      vocab_clarity: { score: ${vocabPts}, max: 10, unique_terms: ${uniqueJargon.length} }
    },
    velocity: compute 3-run slope per component if run_number >= 3 and prior baseline has prior-prior data, else null
  },
  by_task: { [taskId]: { completion_rate, verdict, top_friction, modal_dropout_step, n, allocation_used } },
  by_cohort: { [cohortNum]: { verdict, completion_rate, top_friction } },
  by_super_cohort: { low_access: {...}, target_market: {...}, excluded_risk: {...} },
  top_frictions: [top 5 strings],
  top_delights: [top 5 strings],
  vocabulary_debt: [unique jargon terms with first_seen_run and last_seen_run],
  exit_trigger_clusters: [cluster name, count, example triggers, tasks affected],
  per_task_dropout_step: { [taskId]: modal_dropout_step string },
  confirmed_issue_run_counts: { [finding_slug]: consecutive_run_count },
  task_allocation_used: { S1, S2, S3, S4, S5, S6, S7, S8 },
  suppressed_false_positives: carry over from prior baseline TTL entries still valid
}

delta_table: each finding gets status FIXED/STILL_PRESENT/REGRESSED/NEW, run_count (consecutive appearances), severity_trend (worsening/stable/improving based on persona count change).

exit_trigger_clusters: group the raw exit triggers into 3–6 named patterns with counts.

per_task_dropout_step: for each task, the modal step description at which personas abandoned.

run_summary_md: markdown block for learnings.md:

---
## Run #${run_number} — [date] — ${url}
**N:** ${valid.length}/360 | **UX Score:** ${uxScore}/100 (F:${functionalScore}/55 · I:${inclusiveScore}/45)${criticalFlag ? ' 🚨 CRITICAL' : ''}${regressionDetected ? ' ⚠ REGRESSION' : ''} | vs prior: ${uxScoreDelta !== null ? (uxScoreDelta >= 0 ? '+' : '') + uxScoreDelta : 'baseline'}${funnelConversion !== null ? ` | Funnel: ${Math.round(funnelConversion * 100)}%` : ''}

### UX Score Breakdown
| Component | Score | Max | Rate | vs Prior |
|---|---|---|---|---|
[rows with ▲/▼/— deltas]

### Super-Cohort Split
| Super-cohort | Completion | Trust | Verdict |
|---|---|---|---|
[rows]

### Task Verdicts
| Task | Verdict | Completion | Dropout Step | vs Prior |
|---|---|---|---|---|
[rows]

### Delta
| Finding | Status | Run # | Trend |
|---|---|---|---|
[FIXED/STILL_PRESENT/REGRESSED/NEW with run_count and severity_trend]

### Exit Trigger Clusters
[cluster name: count — example]

### Vocab Debt
[term (first seen run N, last seen run N)]

### Next Run Focus
[3 bullet points]
---

new_false_positives_to_suppress: findings confirmed not real this run (each gets suppressed_until_run = ${run_number + 5}).
next_run_recommendations: 3 specific items.`,
  { label: 'learning-update', phase: 'Grand Synthesis', schema: LEARNING_SCHEMA }
)

phase('Actionable Fixes')

const topFrictions = valid.filter(r => r.biggest_friction).map(r => r.biggest_friction)
const exitTriggers = valid.filter(r => r.exit_trigger).map(r => r.exit_trigger)
const confusionMoments = valid.filter(r => r.confusion_moment).map(r => r.confusion_moment)
const a11yBarriers = valid.filter(r => r.accessibility_barrier).map(r => ({ type: r.disability_type, barrier: r.accessibility_barrier, outcome: r.outcome }))
const smartphoneFailures = valid.filter(r => r.smartphone_only && r.outcome !== 'completed').map(r => ({ friction: r.biggest_friction, exit: r.exit_trigger }))
const jargonAll = valid.filter(r => r.jargon_confusion).map(r => r.jargon_confusion)
const keyboardPersonas = disabilityP.filter(r => r.disability_type === 'motor_keyboard')
const keyboardFailed = keyboardPersonas.some(r => r.keyboard_navigated === false)

const FIX_PROMPT_SUFFIX = `Each fix must include:
- id: short-kebab-case slug
- priority: P1 (blocks 15%+ personas), P2 (5–15%), P3 (<5%)
- title: max 8 words, verb-first
- problem: one sentence — what users experienced and measured impact
- specific_fix: exact change, specific enough to act on without follow-up questions
- file_hint: page/component area (e.g. "protest wizard step 2 label")
- personas_affected: conservative count out of 360
- effort: XS (<1h), S (1–4h), M (4–16h), L (>16h)
- metric_impact: UX Score dimension + estimated point gain
- verification_scenario: persona-typed test — "Give a [literacy tier] [domain expertise] the [task]; success = [measurable condition]"
Generate at most 5. Only include fixes clearly supported by the data.`

const fixAgents = [
  () => agent(
    `UX engineer generating copy & vocabulary fixes for a property management / tax protest web app (Next.js, Tailwind).
Category: Copy & Vocabulary
Data:
vocabulary_debt: ${JSON.stringify(uniqueJargon)}
jargon_instances: ${JSON.stringify(jargonAll.slice(0, 40))}
confusion_moments: ${JSON.stringify(confusionMoments.slice(0, 20))}
dyscalculia_issues: ${JSON.stringify(valid.filter(r => r.disability_type === 'dyscalculia').map(r => ({ barrier: r.accessibility_barrier, friction: r.biggest_friction })))}

For copy fixes, before_after is REQUIRED — provide the exact existing text and the exact replacement text.
${FIX_PROMPT_SUFFIX}`,
    { label: 'fixes-copy', phase: 'Actionable Fixes', schema: FIXES_SCHEMA }
  ),
  () => agent(
    `UX engineer generating UX flow & onboarding fixes for a property management / tax protest web app.
Category: UX Flow & Onboarding
Data:
top_frictions: ${JSON.stringify(topFrictions.slice(0, 40))}
exit_triggers: ${JSON.stringify(exitTriggers.slice(0, 30))}
task_reports: ${JSON.stringify(taskReports.map(t => ({ id: t.task_id, completion: t.completion_rate, friction: t.top_friction, verdict: t.task_verdict, dropout_step: t.modal_dropout_step })))}
funnel_conversion: ${funnelConversion !== null ? Math.round(funnelConversion * 100) + '%' : 'not measured'}
${FIX_PROMPT_SUFFIX}`,
    { label: 'fixes-ux', phase: 'Actionable Fixes', schema: FIXES_SCHEMA }
  ),
  () => agent(
    `UX engineer generating accessibility & keyboard fixes for a property management / tax protest web app.
Category: Accessibility & Keyboard
Data:
a11y_barriers: ${JSON.stringify(a11yBarriers)}
keyboard_result: ${keyboardPersonas.map(r => ({ navigated: r.keyboard_navigated, outcome: r.outcome, barrier: r.accessibility_barrier }))}
dyscalculia_personas: ${JSON.stringify(valid.filter(r => r.disability_type === 'dyscalculia').map(r => ({ outcome: r.outcome, barrier: r.accessibility_barrier, friction: r.biggest_friction })))}

For accessibility fixes, wcag_criterion is REQUIRED (e.g. "WCAG 2.1.1 Keyboard", "WCAG 1.4.3 Contrast").
${FIX_PROMPT_SUFFIX}`,
    { label: 'fixes-a11y', phase: 'Actionable Fixes', schema: FIXES_SCHEMA }
  ),
  () => agent(
    `UX engineer generating mobile & smartphone-only fixes for a property management / tax protest web app.
Category: Mobile & Smartphone-Only
Data:
smartphone_failures: ${JSON.stringify(smartphoneFailures)}
mobile_results: ${JSON.stringify(valid.filter(r => r.device === 'mobile').map(r => ({ outcome: r.outcome, friction: r.biggest_friction, exit: r.exit_trigger, smartphone_only: r.smartphone_only })).slice(0, 40))}
${FIX_PROMPT_SUFFIX}`,
    { label: 'fixes-mobile', phase: 'Actionable Fixes', schema: FIXES_SCHEMA }
  ),
]

// Conditional trust agent — only if S0 trust rate below 60%
if (s0TrustRate < 0.6) {
  fixAgents.push(() => agent(
    `UX engineer generating trust & credibility fixes. S0 trust rate is ${Math.round(s0TrustRate * 100)}% — critically low.
Category: Trust
Data:
s0_distrust_personas: ${JSON.stringify(s0All.filter(r => r.trust_verdict === 'distrust').map(r => ({ reason: r.trust_reason, quote: r.key_quote, cohort: r.cohort_name })))}
skeptic_results: ${JSON.stringify(valid.filter(r => r.cohort === 9).map(r => ({ outcome: r.outcome, trust: r.trust_verdict, friction: r.biggest_friction })))}
${FIX_PROMPT_SUFFIX}`,
    { label: 'fixes-trust', phase: 'Actionable Fixes', schema: FIXES_SCHEMA }
  ))
}

const fixResults = await parallel(fixAgents)
const rawFixes = fixResults.filter(Boolean).flatMap(r => r.fixes || []).filter(Boolean)

// Dedup + cap at 12
const DEDUP_SCHEMA = { type: 'object', required: ['fixes'], properties: { fixes: FIXES_SCHEMA.properties.fixes } }
const dedupResult = await agent(
  `You have ${rawFixes.length} fix tickets generated by parallel agents. Some may be near-duplicates (same file_hint + overlapping problem from different category angles).
Your job: collapse near-duplicates into a single ticket with the more specific specific_fix. Keep the lower (more severe) priority. Preserve all unique fixes. Cap final output at 12 tickets.
Input: ${JSON.stringify(rawFixes, null, 2)}
Output the deduplicated list as structured JSON.`,
  { label: 'fixes-dedup', phase: 'Actionable Fixes', schema: DEDUP_SCHEMA }
)
const dedupedFixes = dedupResult?.fixes || rawFixes.slice(0, 12)

// Qualitative P1 overrides
const finalFixes = dedupedFixes.map(fix => {
  let overrideFix = { ...fix }
  // Rule 1: keyboard navigation failure → always P1
  if (fix.category === 'accessibility' && keyboardFailed && fix.wcag_criterion && fix.wcag_criterion.includes('Keyboard')) {
    overrideFix = { ...overrideFix, priority: 'P1', p1_override_reason: 'WCAG 2.1.1 keyboard failure — legal exposure' }
  }
  // Rule 2: primary CTA abandonment → always P1
  if ((fix.file_hint || '').match(/onboarding|primary.cta|sign.up|get.started/i) && valid.some(r => r.task_assigned === 'S0' && r.outcome === 'gave_up')) {
    overrideFix = { ...overrideFix, priority: 'P1', p1_override_reason: 'Primary CTA abandonment in S0 universal pool' }
  }
  // Rule 3: S0 distrust rate >20% + trust category → always P1
  if (fix.category === 'trust' && s0TrustRate < 0.8 && s0All.filter(r => r.trust_verdict === 'distrust').length / s0All.length > 0.2) {
    overrideFix = { ...overrideFix, priority: 'P1', p1_override_reason: 'S0 distrust >20% — first-impression blocker' }
  }
  return overrideFix
})

finalFixes.sort((a, b) => {
  const pOrder = { P1: 0, P2: 1, P3: 2 }
  if (pOrder[a.priority] !== pOrder[b.priority]) return pOrder[a.priority] - pOrder[b.priority]
  return b.personas_affected - a.personas_affected
})

const quickWins = finalFixes.filter(f => f.effort === 'XS' || f.effort === 'S').sort((a, b) => b.personas_affected - a.personas_affected)

log(`${finalFixes.length} fix tickets (${finalFixes.filter(f => f.priority === 'P1').length} P1, ${finalFixes.filter(f => f.priority === 'P2').length} P2, ${finalFixes.filter(f => f.priority === 'P3').length} P3 | ${quickWins.length} quick wins)`)

return {
  grand_report: grandReport,
  cohort_reports: cohortReports,
  super_cohort_reports: superCohortReports,
  task_reports: taskReports,
  learning_update: learningUpdate,
  all_results: valid,
  all_fixes: finalFixes,
  quick_wins: quickWins,
  ux_score: {
    total: uxScore, functional: functionalScore, inclusive: inclusiveScore,
    prior: uxScorePrior, delta: uxScoreDelta, critical_flag: criticalFlag, regression_detected: regressionDetected,
    breakdown: {
      trust_s0: { score: trustPts, max: 25, rate: s0TrustRate },
      completion_s0: { score: completionPts, max: 20, rate: s0CompletionRate },
      return_s0: { score: returnPts, max: 10, rate: s0ReturnRate },
      literacy_equity: { score: litPts, max: 15, rate: lowLitCompletion },
      accessibility: { score: a11yPts, max: 20, rate: a11yCompletion },
      vocab_clarity: { score: vocabPts, max: 10, unique_terms: uniqueJargon.length },
    }
  },
  funnel_conversion: funnelConversion,
  summary: {
    run_number, n_completed: valid.length, aggregate_moe: 0.052,
    by_task: Object.fromEntries(Object.entries(byTask).map(([t, rs]) => [t, { n: rs.length, completion_rate: rs.filter(r => r.outcome === 'completed').length / rs.length }])),
    by_domain_expertise: { professional: valid.filter(r => r.domain_expertise === 'professional').length, adjacent: valid.filter(r => r.domain_expertise === 'adjacent').length, newcomer: valid.filter(r => r.domain_expertise === 'newcomer').length },
    by_digital_literacy: { T1: valid.filter(r => r.digital_literacy_tier === 'T1_reluctant').length, T2: valid.filter(r => r.digital_literacy_tier === 'T2_assisted').length, T3: valid.filter(r => r.digital_literacy_tier === 'T3_capable').length, T4: valid.filter(r => r.digital_literacy_tier === 'T4_power').length },
    smartphone_only_count: valid.filter(r => r.smartphone_only).length,
    disability_count: valid.filter(r => r.disability_type).length,
    a11y_barriers: valid.filter(r => r.accessibility_barrier).map(r => ({ type: r.disability_type, barrier: r.accessibility_barrier, outcome: r.outcome })),
  }
}
```

---

## Phase 3: Save Report + Update Learning Artifacts

Write full report to `$_REPORT_FILE`:

```markdown
# Massive User Test — Run #[N] — [App Name / URL]
*[Date] | 360 personas | 14 cohorts | 8 task tracks | Between-subjects*
*Aggregate MoE: ±5.2% | Super-cohort: ±8–12% | Task: ±14–17% | Cohort: ±17–25%*

[IF REGRESSION: ## ⚠ REGRESSION ALERT
UX Score dropped [N] pts vs run #[N-1]. [Component] fell from [N] to [N]. Implement P1 fix tickets before next run.]

## One-Sentence Verdict
[From grand synthesis]

## UX Score: [N]/100 (Functional [N]/55 · Inclusive [N]/45) [▲/▼N vs run #N-1]
[IF CRITICAL: 🚨 CRITICAL — [component] below minimum threshold]

| Component | Score | Max | Rate | vs Prior |
|---|---|---|---|---|
| Trust (S0) | N | 25 | N% | ▲/▼/— |
| Completion (S0) | N | 20 | N% | |
| Return intent (S0) | N | 10 | N% | |
| Literacy equity (T1/T2) | N | 15 | N% | |
| Accessibility | N | 20 | N% | |
| Vocab clarity | N | 10 | N terms | |

Funnel conversion (S0→S1): N% (n=20) — [first run / vs prior N%]

## Changes Since Last Run
[FIXED / STILL_PRESENT / REGRESSED / NEW table with run_count and severity_trend]

## Super-Cohort Split (primary analytical unit — statistically usable)
| Super-cohort | n | MoE | Completion | Trust | Return | Verdict |
|---|---|---|---|---|---|---|
| Low-access | ~140 | ±8.3% | | | | |
| Target market | ~152 | ±7.9% | | | | |
| Excluded risk | ~68 | ±11.9% | | | | |

## Universal Benchmark (n=60, ±12.7%)
[Trust / completion / return vs prior run]

## Task-by-Task Verdicts (±14–17%)
| Task | n | Completion | Verdict | Dropout step | vs Prior |
|---|---|---|---|---|---|
[S0–S8 rows]

## Domain Expertise Split + Vocabulary Dead Zones
[Professionals vs adjacent vs newcomers]
[Dyscalculia-specific number confusion moments]
Vocabulary debt: [terms with first_seen/last_seen run]

## Digital Literacy Split
[T1/T2 vs T3/T4 — threshold tier]

## Accessibility Audit (n=26)
| Sub-type | n | Completion | Key barriers |
|---|---|---|---|
| Cognitive / ADHD | 7 | % | |
| Dyscalculia | 5 | % | |
| Low Vision | 6 | % | |
| Motor / Keyboard-only | 5 | % | Keyboard nav pass: N% |
| Deaf / HoH | 3 | % | |

## Market Fit Map (14 cohorts, directional)
[Full cohort table with MoE]

## Exit Trigger Clusters
[cluster name: count — example triggers]

## Consensus Friction (≥54 personas)
[Top 5]

## Consensus Delight (≥54 personas)
[Top 5]

## Trust Analysis
## The 7 Most Important Quotes
## Top Recommendations (ordered by personas affected)
## Methodology
```

Write fix tickets to `$_FIXES_FILE`:

```markdown
# Fix Tickets — Run #[N] — [Date]
*[N] fixes from 360-persona panel. Implement P1s before next run.*
*UX Score target next run: [current + 10]/100*

## Quick Wins (XS/S effort — ship this sprint)
[All XS/S fixes sorted by personas_affected desc, regardless of priority]
| # | ID | Title | Effort | Personas | Priority | Score impact |
|---|---|---|---|---|---|---|
[rows]

---

[For each fix in finalFixes:]

### [P1/P2/P3] [id] — [title]
[IF p1_override_reason: **P1 override:** [reason]]
**Category:** [category] | **Effort:** [effort] | **Personas:** [personas_affected]/360
**Problem:** [problem]
**Fix:** [specific_fix]
[IF copy: **Before:** [before] → **After:** [after]]
[IF accessibility: **WCAG:** [wcag_criterion]]
**Where:** [file_hint]
**Score impact:** [metric_impact]
**Verify:** [verification_scenario]

---
```

**Save `baseline.json`** — write `learning_update.baseline_json` to `$_BASELINE_FILE`.

**Update `learnings.md`:**

If new file, create with header:
```
# user-test-massive Learnings

## Run History
| Run | Date | URL | N | UX Score | F/I | Trust | Funnel | Notes |

## UX Score History
| Run | Total | Trust | Completion | Return | Literacy | A11y | Vocab | Regression? |

## Active Window (last 3 runs — full detail)
[maintained rolling; older runs move to archive]

## Run Archive
[single-line per run: Run #N — date — score — one-sentence verdict]

## Confirmed Issues (2+ runs)
[finding — run_count — severity_trend]

## Fixed Issues

## Verified False Positives
[finding — suppressed_until_run: N — reason]

## Vocabulary Debt
[term — first_seen: run N — last_seen: run N]

## Resolved Vocabulary Debt
[term — first_seen: N — resolved: N]

## Task Allocation History
| Run | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | Rationale |

---
```

Append `learning_update.run_summary_md` to `$_LEARNINGS_FILE`.

Maintain Active Window: keep last 3 run summaries in full; move older ones to Run Archive as single lines.

Update Run History, UX Score History, Task Allocation History tables.

Update Vocabulary Debt: set `last_seen` to current run for all terms appearing this run. Move terms not seen in 2+ runs to Resolved Vocabulary Debt.

Update Confirmed Issues: increment run_count for STILL_PRESENT findings; update severity_trend.

Update Fixed Issues for FIXED delta entries.

Update Verified False Positives: add new_false_positives_to_suppress from learning_update with their TTL.

---

## Phase 4: In-Chat Summary

```
---
Massive User Test: Run #N — [URL]
360 personas | 14 cohorts | 8 tasks | [N] completed | ±5.2% MoE

[IF REGRESSION: ⚠ REGRESSION — score dropped N pts. Implement P1 fixes before re-running.]
[IF CRITICAL: 🚨 CRITICAL — [component] below minimum threshold]

UX Score: N/100 (Functional N/55 · Inclusive N/45) [▲/▼N vs run #N-1 / BASELINE]
  Trust (S0):        N/25  (N%)   [▲/▼]
  Completion (S0):   N/20  (N%)   [▲/▼]
  Return intent:     N/10  (N%)   [▲/▼]
  Literacy equity:   N/15  (N%)   T1/T2  [▲/▼]
  Accessibility:     N/20  (N%)   disability cohort  [▲/▼]
  Vocab clarity:     N/10  (N unique jargon terms)  [▲/▼]
Funnel (S0→S1):      N%   (n=20)  [▲/▼ vs prior / baseline]

Super-cohort split:
  Low-access (n≈140 ±8%):    N% completion | N% trust
  Target market (n≈152 ±8%): N% completion | N% trust
  Excluded risk (n≈68 ±12%): N% completion | N% trust

Task verdicts:
  S1 Onboarding:     [verdict] N%  dropout: [step]  [▲/▼]
  S2 Operational:    [verdict] N%  dropout: [step]
  S3 Tax Protest:    [verdict] N%  dropout: [step]
  S4 Mobile:         [verdict] N%
  S5 Trust/Pricing:  [verdict] N%
  S6 Doc Upload:     [verdict] N%  dropout: [step]
  S7 Batch Protest:  [verdict] N%
  S8 Return Visit:   [verdict] N%

Changes since run #N-1:
  FIXED:         [finding]
  STILL PRESENT: [finding] (run N, [trend])
  REGRESSED:     [finding]
  NEW:           [finding]

Domain: Professionals N% | Newcomers N%
Vocab debt (N terms): [top 3 with counts]
Accessibility: N/26 disability personas completed
Literacy: T1/T2 N% | T3/T4 N%

Quick wins ([N] XS/S fixes to ship this sprint):
  1. [id] — [title] (Effort [X], N personas, [metric_impact])
  2. [id] — [title]
  3. [id] — [title]

Top P1 fixes:
  1. [id] — [title] ([P1_override_reason if set])

Verdict: [one sentence]
Report:      [path]
Fix tickets: [path] (N fixes: P1=N P2=N P3=N | N quick wins)
Baseline:    [path] (updated)
Learnings:   [path] (appended, active window maintained)
---
```

After printing the summary, call AskUserQuestion with:
- If regression: one question asking which P1 fixes to implement (multiSelect: true), with options built from the top P1 fix ticket titles (up to 4) plus "All P1 fixes" and "None — just save reports". Preface: "Regression detected. Select fixes to implement now:"
- If no regression: two questions:
  1. "Which fixes should I implement now?" (multiSelect: true) — options from top P1+P2 tickets (up to 4 by personas_affected), plus "None / just save reports"
  2. "Anything else?" (multiSelect: true) — options: "Dig deeper into a cohort", "Mark a finding as false positive (TTL 5 runs)", "Explain a UX Score component", "Nothing else"
Then implement any selected fixes immediately, following the file_hint and specific_fix fields from the fix ticket. Use surgical edits only.

---

## Operating Principles

### Statistical
- **Never compare completion rates across different tasks.** S3 at 50% ≠ S1 at 50%.
- **Super-cohorts are the primary analytical unit.** At ±8–12% MoE they're statistically usable. 14-cohort breakdown is directional context.
- **S0 (n=60, ±12.7%) is the longitudinal anchor.** Only S0 trust/completion/return are valid trendlines. Scenario task rates are not comparable across runs (different adaptive allocations).
- **Consensus threshold at N=360:** ≥54 personas (15%) notable; ≥108 (30%) significant.
- **Funnel conversion is separate from UX Score.** Track it as a standalone metric.

### UX Score
- **Functional/Inclusive split tells you WHY the score moved.** A rising functional + falling inclusive means you're optimizing for experts and losing everyone else.
- **Vocab clarity hits 0 at 10 jargon terms.** Every term removed from the debt list is +1 pt. Fastest available win in a B2B app.
- **Accessibility is weighted 20 pts** because it is simultaneously the most impactful and most neglected dimension.
- **Critical flag ≠ failing score.** A 72 total with a critical accessibility floor is worse than a 65 spread evenly.
- **Regression auto-promotes.** When ⚠ REGRESSION fires, every fix ticket touching the regressed dimension becomes P1 regardless of raw count.

### Learning Loop
- **TTL false positives expire.** After `suppressed_until_run` passes, a finding re-enters as `NEW`. This prevents permanent suppression from hiding real regressions after redesigns.
- **Severity trend matters.** STILL_PRESENT with `worsening` trend is more urgent than STILL_PRESENT with `stable`. Surface it.
- **Vocabulary debt is time-stamped.** A term last seen 4 runs ago is probably fixed; move it to Resolved. A term seen every run is vocabulary architecture debt.
- **Active Window keeps learnings.md useful at scale.** After run 4, don't let engineers read through 15 appended summaries — maintain the rolling 3-run window.
- **Exit trigger clusters are the engineering interface.** Raw exit triggers are noise; clusters are named patterns that engineers can target ("jargon-wall at protest step 2" is actionable; "confused" is not).

### Actionable Fixes
- **P1 qualitative overrides bypass the count threshold.** Keyboard nav failure and primary CTA abandonment are P1 regardless of how many personas hit them.
- **Dedup prevents category contamination.** The 4-5 parallel agents will surface the same ARB jargon fix from copy AND ux angles. The dedup pass keeps the stronger, more specific version.
- **Quick wins ship in the same sprint.** Never let an XS copy fix sit in the backlog behind a 3-month architecture change.
- **Verification scenarios make FIXED confirmable.** If a fix doesn't include a verification scenario, the next run can't confirm it worked.

### Persona Variance
- **Backstory breaks cohort homogeneity.** Without it, all T2_assisted personas return near-identical sessions. The backstory + pre-assigned jargon term forces variance.
- **Prior experience changes trust dynamics.** A `returning_stuck` persona has different trust and patience than a `first_visit` persona with identical demographics.
- **Dyscalculia requires explicit numerical framing.** Assessed values, cap rates, and % reductions need plain-English labels — not just tooltips for unfamiliar terms.

---

## Demographic Reference (US adults — Census 2024 / Pew 2025 / PIAAC 2023 / CDC)

**Age:** 18–24: 12% | 25–34: 17% | 35–44: 17% | 45–54: 15% | 55–64: 16% | 65+: 23%
**Income:** <$30k: 21% | $30–60k: 20% | $60–100k: 21% | $100–150k: 17% | $150k+: 21%
**Education:** No HS: 9% | HS only: 27% | Some college/AA: 25% | Bachelor's+: 39%
**Geography:** Suburban: 52% | Urban: 27% | Rural: 21% | South: 39% | West: 24% | Midwest: 21% | Northeast: 16%
**Race/Ethnicity:** White non-Hispanic: 57% | Hispanic: 19% | Black: 12% | Asian: 7% | Other: 4%
**Digital Literacy (PIAAC 2023):** Level 0–1: 28% | Level 2: 29% | Level 3+: 44%
**Device:** Mobile-primary: 58% | Desktop: 42% | Smartphone-only: 16%
**Disability (CDC BRFSS):** Any: 26% | Cognitive: 12.8% | Mobility: 13.7% | Vision: 4.6% | Hearing: 5.9%
**Homeownership:** Own: 65% | Rent: 35%
**Employment:** Full-time: 49% | Part-time: 11% | Self-employed: 8% | Not in labor force: 30%
**Language:** English-only at home: ~79% | Other primary language: ~21% (Spanish largest at ~13%)
