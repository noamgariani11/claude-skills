# External evidence validation

Load this for a score above 99, detector calibration, expert-score studies,
representative sampling, usability testing, assistive-technology review, or
production field performance, or longitudinal reference snapshots.

## Contents

1. Evidence that cannot be synthesized
2. Held-out detector benchmark
3. Expert-score reliability and correlation
4. Representative surface sampling
5. Real-user task observations
6. Assistive-technology observations
7. Production field performance
8. Longitudinal calibration snapshots
9. Perfection-certificate wiring

## 1. Evidence that cannot be synthesized

The rig may prepare schemas and calculate results. It must not invent labels,
reviewers, participants, observed AT output, or an independent holdout set.
Missing external evidence reports `insufficient`, which does not pass.

This follows the separation in W3C evaluation guidance:

- [ACT test cases](https://www.w3.org/WAI/standards-guidelines/act/report/testcases/)
  publish expected passed, failed, and inapplicable outcomes for testing tool
  implementations. A false positive on a passed or inapplicable example breaks
  consistency.
- [WCAG-EM](https://www.w3.org/WAI/test-evaluate/conformance/wcag-em/)
  requires scope definition, site exploration, representative structured and
  random sampling, evaluation, and reporting. Complete processes stay whole.
- [ARIA-AT](https://w3c.github.io/aria-at/) uses manual assertions of expected
  screen-reader behavior against named patterns.
- [WAI user-evaluation guidance](https://www.w3.org/WAI/test-evaluate/involving-users/)
  says user evaluation finds problems conformance testing cannot, while also
  warning that a few participants cannot represent every disabled user.

Run all gates through:

```bash
S=/abs/designer-dude/scripts
python3 "$S/evidence-gates.py" MODE ... --out .design/MODE-evidence.json
```

The output is content-addressed in `perfectionCertification.artifactManifest`.
Each result also records a canonical SHA-256 of its parsed raw input (both
label and prediction documents for detector studies). Freeze those raw files
in the calibration snapshot as well. Command-line thresholds may tighten the
perfection policy below, never relax it. Source observations must be no more
than 90 days old; generating a new summary does not refresh an old study. Raw
input JSON must live under the output evidence directory; the gate records its
portable path and exact byte hash, and perfection reopens it.

## 2. Held-out detector benchmark

Keep labels and predictions in separate files. Freeze labels before running the
current detector; the prediction producer cannot be one of the labelers.

Labels:

```json
{
  "schema": "designer-dude-detector-labels/v1",
  "datasetId": "product-ui-holdout-2026q3",
  "labelsFrozenBeforePredictions": true,
  "frozenAt": "2026-07-01T00:00:00Z",
  "labelers": ["reviewer-a", "reviewer-b"],
  "items": [{
    "id": "focus-001",
    "rule": "focus-complete-obstruction",
    "expected": "positive",
    "split": "holdout",
    "sourceArtifact": "detector-cases/focus-001.html",
    "sourceSha256": "<64 lowercase hex>",
    "labels": [
      {"reviewer": "reviewer-a", "outcome": "positive"},
      {"reviewer": "reviewer-b", "outcome": "positive"}
    ]
  }]
}
```

Predictions:

```json
{
  "schema": "designer-dude-detector-predictions/v1",
  "datasetId": "product-ui-holdout-2026q3",
  "producer": "designer-dude-rig-commit-abc123",
  "generatedAt": "2026-07-02T00:00:00Z",
  "items": [{"id": "focus-001", "outcome": "positive"}]
}
```

```bash
python3 "$S/evidence-gates.py" detectors \
  --labels .design/labels.json --predictions .design/predictions.json \
  --out .design/detector-benchmark.json
```

Defaults require 100 cases, 50 positive, 40 negative/inapplicable, two
independent labelers, no false positive or false negative, at most 5%
`cannot-tell`, and 95% Wilson lower bounds of at least .94 for both precision
and recall. Every included rule needs both positive and negative/inapplicable
coverage; aggregate accuracy cannot hide a one-sided rule.

Do not tune against the holdout. Create a new version after changing labels or
source artifacts; hashes make silent relabeling visible.

For the accessibility rules that overlap W3C ACT, also run the independent
public corpus directly:

```bash
node "$S/act-benchmark.mjs" --out .design/act-benchmark.json
```

The adapter intentionally maps only rules whose applicability and outcome can
be reproduced by this rig: browser-computed button/form/link/menuitem names,
known primary language subtags, page language presence, and autocomplete token
validity. It hashes the W3C manifest and every fetched case, records the ACT
license, and requires zero false positives, zero false negatives and no more
than 5% transport `cannot-tell` outcomes. On 2026-08-03 the mapped corpus held
138 cases: 54 positive and 84 negative/inapplicable, all matched. Re-run it;
that dated result is not transferable to a changed probe or ACT manifest.

## 3. Expert-score reliability and correlation

The correlation study asks two separate questions:

1. Do independent expert reviewers agree enough to define a target?
2. Does the skill preserve their ordering of products?

```json
{
  "schema": "designer-dude-expert-ratings/v1",
  "ratingsBlindToToolScore": true,
  "study": {
    "coordinator": "researcher-a",
    "toolVersion": "designer-dude-commit-abc123",
    "protocolSha256": "<64 lowercase hex>",
    "conductedAt": "2026-08-03T12:00:00Z"
  },
  "reviewers": ["reviewer-a", "reviewer-b", "reviewer-c"],
  "reviewerProfiles": [
    {"id": "reviewer-a", "affiliation": "studio-a", "yearsExperience": 8,
     "expertise": ["product-design"]},
    {"id": "reviewer-b", "affiliation": "accessibility-lab", "yearsExperience": 6,
     "expertise": ["accessibility"]},
    {"id": "reviewer-c", "affiliation": "studio-c", "yearsExperience": 5,
     "expertise": ["product-design", "accessibility"]}
  ],
  "strata": {
    "productCategories": ["commerce", "content", "enterprise"],
    "surfaceTypes": ["marketing", "workflow", "settings"],
    "qualityBands": ["low", "mid", "high"],
    "viewportClasses": ["mobile", "desktop"]
  },
  "products": [{
    "id": "product-01",
    "artifact": "expert-products/product-01.png",
    "artifactSha256": "<64 lowercase hex>",
    "toolScore": 84,
    "strata": {
      "productCategory": "commerce", "surfaceType": "workflow",
      "qualityBand": "high", "viewportClass": "desktop"
    },
    "ratings": [
      {"reviewer": "reviewer-a", "score": 82},
      {"reviewer": "reviewer-b", "score": 86},
      {"reviewer": "reviewer-c", "score": 83}
    ]
  }]
}
```

```bash
python3 "$S/evidence-gates.py" ratings --input .design/expert-ratings.json \
  --out .design/expert-correlation.json
```

Defaults require 12 products and three reviewers. The gate calculates
Krippendorff alpha with interval distance, Spearman rank correlation against
the per-product expert median, a deterministic bootstrap 95% interval, Lin's
concordance correlation coefficient, mean absolute error, signed bias, and the
worst product error. It requires alpha >= .80, a Spearman lower bound >= .70,
concordance >= .90, MAE <=5 points, absolute bias <=3 points, and no product
error above 10 points. Rank agreement alone is insufficient: a tool that adds
15 points to every expert score is correlated but miscalibrated. Report the
interval and error measures, not only the point estimate. All declared strata
must be covered. The expert medians must span at least 80 points, including at
least two products at 20 or below and two at 90 or above, so the study actually
tests both ends of the scale—especially the end that can award perfection.
Low, mid and high bands each need at least three products. Mobile and desktop artifacts plus
at least three product categories and three surface types prevent a homogeneous
set from masquerading as general calibration.

Every reviewer has exactly one profile with at least three years of relevant
experience and declared expertise. The panel collectively covers product
design and accessibility, spans at least two affiliations, and excludes the
study coordinator. IDs may remain pseudonymous in the bundle; retain credential
verification in the accountable human report.

Reviewers see pinned product artifacts, not the skill score or findings. Change
product mix across marketing pages, dense applications, commerce, content,
mobile widths, themes, and quality levels; twelve near-identical dashboards do
not establish general validity.

## 4. Representative surface sampling

Create a sampling plan before collecting findings. List product scope,
technologies, page types, essential functions, structured samples, random
samples, and complete processes whose steps map back to samples. Record an
accountable `author` and ISO-8601 `createdAt`; a newly emitted gate result does
not make an old scope current.

Every sample includes an `artifact` path alongside `artifactSha256`. Paths are
portable, relative bundle paths: absolute paths and `..` traversal are rejected.
Every structured sample also states its selection `rationale`. A non-exhaustive
plan includes `randomSelection` with `method` (`simple-random` or
`systematic-random`), a reproducible `seed`, the explored `populationSize`, and
`selectedIds` exactly matching the random sample records. Merely writing
`"selection":"random"` does not establish random selection.

```bash
python3 "$S/evidence-gates.py" sampling --input .design/sampling-plan.json \
  --out .design/sampling-evidence.json
```

The default non-exhaustive gate requires three structured samples, two random
samples, full page-type/function coverage, and one complete multi-step process.
Each sample needs a URL and SHA-256 evidence. Set `exhaustive:true` only when
every in-scope surface was actually enumerated. An exhaustive plan needs an
`inventory` of `{id,url,artifactSha256}` entries and every sample needs the
matching `inventoryId`; every inventory entry must be sampled with the same URL
and hash. Exhaustive scope removes the structured/random count minimums, not
the coverage, inventory, or complete-process requirements.

## 5. Real-user task observations

Use pseudonymous participant identifiers and retain consent/recruitment records
outside the skill artifact. Do not store names, contact details, diagnoses, or
recordings in the JSON.

```json
{
  "schema": "designer-dude-usability-observations/v1",
  "study": {
    "facilitator": "researcher-a",
    "productVersion": "release-2026.08.1",
    "recruitmentScope": "target-role users including disabled participants",
    "conductedAt": "2026-08-03T12:00:00Z",
    "protocolSha256": "<64 lowercase hex>",
    "productArtifactSha256": "<64 lowercase hex>",
    "samplingPlanSha256": "<64 lowercase hex>",
    "protocolArtifact": "usability/protocol.md",
    "productArtifact": "products/release-2026.08.1.html",
    "samplingPlanArtifact": "sampling/plan.json"
  },
  "participants": ["p01", "p02", "p03"],
  "tasks": [{
    "id": "approve-invoice",
    "essentialFunction": "approve an invoice",
    "protocolTaskArtifact": "usability/tasks/approve-invoice.md",
    "protocolTaskSha256": "<64 lowercase hex>",
    "attempts": [
      {"participant": "p01", "completed": true, "criticalError": false}
    ]
  }]
}
```

The default perfection gate needs ten participants, three representative
tasks, ten unique attempts per task, no critical error, and a task-success 95%
Wilson lower bound of at least .70. These are evidence thresholds, not a claim
that ten people represent all users. Record participant characteristics and
study limitations in the human report.

## 6. Assistive-technology observations

ARIA snapshots do not substitute for AT output. Record the exact AT, browser,
platform, versions, task, expected output, observed output, outcome, and a
hashed transcript or recording reference. The document also requires
`tester`, `reviewedAt`, `productArtifactSha256`, `protocolSha256`, and
`samplingPlanSha256`; each task also carries `taskProtocolSha256`, so
observations cannot float free of the reviewed build, scope, or task wording.
The corresponding `protocolArtifact`, `productArtifact`,
`samplingPlanArtifact`, per-task `taskProtocolArtifact`, and transcript
`artifact` paths are carried into the result with their hashes.

```bash
python3 "$S/evidence-gates.py" assistive-tech --input .design/at-observations.json \
  --out .design/at-evidence.json
```

Defaults require three complete tasks across at least two AT/browser/platform
combinations and zero failed observations. AT and browser versions are part of
the variant identity, while breadth requires two distinct AT/browser/platform
stacks—two versions of NVDA/Firefox/Windows still count as one stack. Every
transcript hash is retained in the gate result. Choose combinations from supported product scope; common desktop
pairings include NVDA/Firefox/Windows and VoiceOver/Safari/macOS. Do not
reinterpret a browser accessibility-tree dump as a screen-reader transcript.

## 7. Production field performance

An Interaction A+ and literal 100 require field Core Web Vitals from a
production build, not a single warm local trace. Google defines the good p75
thresholds as LCP ≤2500 ms, INP ≤200 ms and CLS ≤0.1, segmented across mobile
and desktop. See [Web Vitals](https://web.dev/articles/vitals) and the
[threshold methodology](https://web.dev/articles/defining-core-web-vitals-thresholds).

```bash
python3 "$S/evidence-gates.py" performance \
  --input .design/performance-observations.json \
  --out .design/performance-evidence.json
```

Use schema `designer-dude-performance-observations/v1`. Its `study` records an
accountable collector, product version, current `conductedAt`,
`productionBuild:true`, `realUserMonitoring:true`, a ≥28-day window, and pinned
sampling-plan/environment artifacts. Provide at least three critical surfaces,
each with a pinned raw RUM export and at least 100 complete LCP/INP/CLS
observations for both `mobile` and `desktop`. The gate recomputes nearest-rank
p75 for each metric and device; one failing surface/device set fails the gate.
CLI options may make those requirements stricter, never weaker.

Do not substitute Lighthouse TBT for INP. Lab tools are useful for regression
work, but the official guidance identifies Core Web Vitals as field metrics and
notes that Lighthouse cannot measure INP without real interaction.

## 8. Longitudinal calibration snapshots

Freeze the raw probe JSON, screenshots, ARIA trees, report, environment JSON,
and any locally permitted reference HTML together:

```bash
python3 "$S/calibration-snapshot.py" freeze \
  --root .design/calibration/2026q3 \
  --source-url https://example.test/reference \
  --environment .design/calibration/environment.json \
  --label 2026q3 --out .design/calibration/2026q3/snapshot.json

python3 "$S/calibration-snapshot.py" verify \
  --manifest .design/calibration/2026q3/snapshot.json \
  --root .design/calibration/2026q3 --bundle-root .design \
  --max-age-days 90 \
  --out .design/calibration-verification.json
```

The environment JSON must record `os`, `architecture`, `playwrightVersion`,
`designerDudeVersion`, all three entries in `browserVersions`, and a
`fontFingerprintSha256`. A replayable snapshot contains at least one JSON
probe, PNG screenshot, YAML ARIA tree, and Markdown review report. Verification
emits portable bundle paths for the snapshot manifest and every frozen artifact
so the outer perfection manifest can rehash the complete set.

A live site can redesign; the pinned bytes preserve what was actually judged.
Re-capture rather than editing a manifest. Verification rejects missing,
changed, path-traversing, duplicated, future-dated, or stale evidence. It also
hashes the manifest itself, rejects artifacts that resolve outside the snapshot
root, and enforces a maximum 90-day age for perfection. `--max-age-days` may
select a shorter window, not a longer one.

## 9. Perfection-certificate wiring

A literal 100 requires passing artifacts for:

- `methodValidation.detectorBenchmark`
- `methodValidation.actBenchmark`
- `methodValidation.expertCorrelation`
- `representativeSampling`
- `usabilityReview`
- `assistiveTechReview`
- `performanceReview`
- `calibrationSnapshot`

It also requires the behavioral, locale, cross-engine and artifact-regression
evidence in `scoring.md`. Every reference is SHA-256 pinned. `insufficient` is
not `verified`; documented limitations belong in the report but cannot be used
to unlock the maximum score. Nested case files, rated-product captures,
sampling captures, task protocols, AT transcripts, and the calibration snapshot
manifest must each appear in `artifactManifest`; the scorer opens and rehashes
every one rather than trusting the summary's claim.
