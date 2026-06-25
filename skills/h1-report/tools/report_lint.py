#!/usr/bin/env python3
"""Prose linter for a HackerOne report draft: kill em dashes, catch grammar/style/AI-slop.

This is the PROSE half of the /h1-report gate. The repo's
`research/tools/report_validator.py` is the STRUCTURE/anti-slop-evidence half (Title,
Severity+CVSS vector, numbered repro, grounded PoC, redaction). This tool never decides
whether a bug is real — it only makes the writing read like a careful human researcher
wrote it, not a chatbot.

Two jobs:

  1. Em dashes — DELETE THEM ALL. Em dash (U+2014 —), horizontal bar (U+2015 ―), en dash
     (U+2013 –), and the ASCII "--" double-hyphen are the single loudest "an LLM wrote this"
     tell, and they read as sloppy to a triager. `--fix` rewrites every one into ordinary
     punctuation (comma / colon / hyphen / range) and GUARANTEES zero remain. Without
     `--fix` each is reported with line + context so you can rewrite by hand.

  2. Grammar & style — heuristic checks for AI-slop vocabulary, hedging/weasel words,
     passive voice, run-on sentences, filler intensifiers, vague titles, condescending
     "clearly/obviously", doubled words, and whitespace noise. Each is a WARN with a line
     number and a concrete suggestion. No external dependencies (no proselint/LanguageTool
     needed) so it runs anywhere.

Exit status:
  0  no em dashes, no FAILs (style WARNs allowed)
  1  em dashes present (run --fix), or any FAIL, or --strict with any WARN

Usage:
  report_lint.py draft.md                 # report only
  report_lint.py draft.md --fix           # rewrite em dashes in place, then report
  report_lint.py draft.md --fix -o out.md # write the fixed copy elsewhere
  report_lint.py draft.md --strict        # style WARNs also fail (use as a hard gate)
  report_lint.py draft.md --json          # machine-readable
  cat draft.md | report_lint.py -         # read stdin
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

# --- Em-dash family -------------------------------------------------------------------
# Every dash that is not a plain hyphen-minus. These must all be gone after --fix.
EMDASH_CHARS = "—―‒–⸺⸻"  # — ― ‒ – ⸺ ⸻
EMDASH_CHAR_RE = re.compile(f"[{EMDASH_CHARS}]")
ASCII_DDASH_RE = re.compile(r"(?<=\s)--(?=\s)")  # spaced " -- " used as an em dash


def fix_em_dashes(text: str) -> tuple[str, int]:
    """Replace every em/en/horizontal-bar dash and spaced -- with plain punctuation.

    Heuristics, applied in order:
      * digit RANGE  "10–20" / "10 — 20"      -> "10-20"
      * word RANGE   "Mon–Fri"                -> "Mon-Fri"   (en dash, no spaces, alnum sides)
      * clause break " word — word "          -> ", word"    (the common interruption use)
      * leftover bare dash                    -> ", "
    Then normalise the doubled commas / stray spaces the replacements can create.
    """
    n = len(EMDASH_CHAR_RE.findall(text)) + len(ASCII_DDASH_RE.findall(text))

    cls = f"[{EMDASH_CHARS}]|--"
    # numeric range: keep it a range
    text = re.sub(rf"(\d)\s*(?:{cls})\s*(\d)", r"\1-\2", text)
    # tight word range (en/em with no surrounding spaces, alnum on both sides): hyphenate
    text = re.sub(rf"(?<=[A-Za-z0-9])(?:{cls})(?=[A-Za-z0-9])", "-", text)
    # everything else (clause-level interruption, spaced or trailing): comma
    text = re.sub(rf"\s*(?:{cls})\s*", ", ", text)

    # tidy artefacts: ", ," -> ",", " ," -> ",", duplicate spaces, leading ", " after open paren
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r"\(\s*,\s*", "(", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r",\s*([.;:!?])", r"\1", text)  # ", ." -> "."
    return text, n


# --- Style / grammar heuristics --------------------------------------------------------
# AI-slop vocabulary: the words chatbots over-use. A real researcher rarely writes these.
AI_SLOP = [
    "delve", "delves", "delving", "leverage", "leverages", "leveraging", "utilize",
    "utilizes", "utilizing", "seamless", "seamlessly", "robust", "robustly", "boasts",
    "boasting", "realm", "tapestry", "landscape of", "in today's", "in the world of",
    "it's worth noting", "it is worth noting", "it's important to note",
    "it is important to note", "needless to say", "as we all know", "comprehensive",
    "myriad", "plethora", "facilitate", "facilitates", "underscore", "underscores",
    "paramount", "pivotal", "intricate", "intricacies", "navigate the", "elevate",
    "unlock", "unlocking", "game-changer", "cutting-edge", "state-of-the-art",
    "in conclusion", "to summarize", "furthermore", "moreover", "additionally,",
    "firstly", "secondly", "thirdly", "ever-evolving", "ever-changing", "harness the",
    "a testament to", "rich tapestry", "embark", "the power of", "dive into", "deep dive",
]
# Hedging / weasel words that weaken an impact claim.
HEDGES = [
    "maybe", "perhaps", "possibly", "potentially", "might be able to", "could possibly",
    "it seems", "it appears", "i think", "i believe", "i guess", "sort of", "kind of",
    "somewhat", "more or less", "to some extent", "arguably", "presumably",
]
# Condescending / filler words triagers dislike (it's "clearly" not clear to them).
CONDESCENDING = ["clearly", "obviously", "simply", "just ", "of course", "trivially", "needless to say"]
INTENSIFIERS = ["very", "really", "extremely", "incredibly", "highly ", "totally", "absolutely", "basically", "literally"]
# Vague titles that fail H1's "clear and concise title" bar.
VAGUE_TITLE_RE = re.compile(r"\b(found a bug|security (issue|bug|problem)|vulnerability found|a vulnerability|some issue|bug report)\b", re.I)
# Passive voice: be-verb + past participle (heuristic; -ed/-en or common irregulars).
PASSIVE_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|being|gets?|got)\s+(?:\w+ly\s+)?"
    r"(\w+(?:ed|en)|done|made|sent|shown|seen|found|taken|given|known|built|held|read|set|put|run|leaked|exposed|bypassed|disclosed)\b",
    re.I,
)
DOUBLED_WORD_RE = re.compile(r"\b(\w+)\s+\1\b", re.I)
MULTI_BANG_RE = re.compile(r"[!?]{2,}")
TRAILING_WS_RE = re.compile(r"[ \t]+$")
DOUBLE_SPACE_RE = re.compile(r"(?<=\S)  +(?=\S)")

# Impact-field tell: speculation instead of a demonstrated outcome. Triagers close
# "theoretically possible" findings as Informative — the Impact must read "I did X".
IMPACT_SPECULATION_RE = re.compile(
    r"\b(an attacker (could|would|can|might|may)|could (allow|be used|lead|result|enable)"
    r"|may be able to|might be able to|it (is|may be) possible to|theoretically|in theory"
    r"|potentially (allow|lead|result|expose))\b", re.I)
# Evidence hosted off-platform: H1 only trusts ATTACHED media; third-party links rot / aren't trusted.
THIRD_PARTY_HOST_RE = re.compile(
    r"https?://(?:www\.)?(youtube\.com|youtu\.be|streamable\.com|imgur\.com|i\.imgur\.com"
    r"|drive\.google\.com|dropbox\.com|we\.tl|wetransfer\.com|pastebin\.com|gist\.github\.com"
    r"|prnt\.sc|gyazo\.com|ibb\.co|postimg\.cc|vimeo\.com|loom\.com)/", re.I)
# Which CVSS version the vector declares (surfaced so it can be matched to the program's).
CVSS_VERSION_RE = re.compile(r"CVSS:(3\.0|3\.1|4\.0)/", re.I)

# Words allowed to repeat (doubled-word check false positives).
DOUBLE_OK = {"that", "had", "is", "do", "no", "blah", "ha", "wo"}


@dataclass
class Issue:
    line: int
    rule: str
    status: str
    detail: str
    suggestion: str = ""


@dataclass
class Result:
    issues: list[Issue] = field(default_factory=list)
    em_dash_count: int = 0
    fixed: bool = False
    cvss_version: str = ""

    def add(self, line: int, rule: str, status: str, detail: str, suggestion: str = "") -> None:
        self.issues.append(Issue(line, rule, status, detail, suggestion))

    @property
    def fails(self) -> list[Issue]:
        return [i for i in self.issues if i.status == FAIL]

    @property
    def warns(self) -> list[Issue]:
        return [i for i in self.issues if i.status == WARN]


def _context(line: str, idx: int, width: int = 36) -> str:
    start = max(0, idx - width // 2)
    snippet = line[start:start + width].strip()
    return f"…{snippet}…" if start > 0 else snippet


def lint(text: str, *, em_dashes_remaining: int) -> Result:
    res = Result(em_dash_count=em_dashes_remaining)
    lines = text.splitlines()
    cvss_m = CVSS_VERSION_RE.search(text)
    if cvss_m:
        res.cvss_version = cvss_m.group(1)

    # Em dashes still present (run after any --fix; if --fix ran this is 0).
    if em_dashes_remaining:
        for n, line in enumerate(lines, 1):
            for m in EMDASH_CHAR_RE.finditer(line):
                res.add(n, "em-dash", FAIL, _context(line, m.start()),
                        "remove it (run --fix): use a comma, colon, or rewrite")
            for m in ASCII_DDASH_RE.finditer(line):
                res.add(n, "em-dash", FAIL, _context(line, m.start()),
                        "ASCII '--' used as a dash; replace with a comma")

    lower_lines = [l.lower() for l in lines]
    in_fence = False
    for n, (line, low) in enumerate(zip(lines, lower_lines), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue  # never lint code/PoC blocks for prose

        for w in AI_SLOP:
            if w in low:
                res.add(n, "ai-slop", WARN, f"'{w.strip()}'",
                        "chatbot tell; cut it or use plain words")
        for w in HEDGES:
            if w in low:
                res.add(n, "hedge", WARN, f"'{w.strip()}'",
                        "hedging weakens the claim; state what you proved or drop it")
        for w in CONDESCENDING:
            if w in low:
                res.add(n, "condescending", WARN, f"'{w.strip()}'",
                        "if it were obvious the triager wouldn't need the report; remove")
        for w in INTENSIFIERS:
            if re.search(rf"\b{re.escape(w.strip())}\b", low):
                res.add(n, "filler", WARN, f"'{w.strip()}'", "filler intensifier; delete")
        for m in DOUBLED_WORD_RE.finditer(line):
            if m.group(1).lower() not in DOUBLE_OK:
                res.add(n, "doubled-word", WARN, f"'{m.group(0)}'", "repeated word")
        if MULTI_BANG_RE.search(line):
            res.add(n, "punctuation", WARN, "'!!'/'??'", "one mark is enough; stay measured")
        if TRAILING_WS_RE.search(line):
            res.add(n, "whitespace", WARN, "trailing whitespace", "strip it")
        if DOUBLE_SPACE_RE.search(line):
            res.add(n, "whitespace", WARN, "double space", "single space")

    # Sentence-level: run-ons and passive voice over the de-fenced prose.
    prose = strip_fences(text)
    for sent in split_sentences(prose):
        words = sent.split()
        if len(words) > 40:
            res.add(0, "run-on", WARN, f"{len(words)}-word sentence: '{sent[:50].strip()}…'",
                    "split it; triagers skim")
    passive_hits = len(PASSIVE_RE.findall(prose))
    if passive_hits >= 4:
        res.add(0, "passive-voice", WARN, f"{passive_hits} passive constructions",
                "prefer active voice: 'the server returns', not 'is returned by the server'")

    # Impact field: must read as a demonstrated outcome, not speculation.
    impact_body, impact_start = section_body(lines, "impact")
    for off, line in enumerate(impact_body):
        for m in IMPACT_SPECULATION_RE.finditer(line):
            res.add(impact_start + off, "impact-speculation", WARN, f"'{m.group(0)}'",
                    "Impact must state what you DID ('I retrieved/accessed/changed X'), not what an attacker could")

    # Third-party-hosted evidence: H1 trusts attached media only.
    for n, line in enumerate(lines, 1):
        m = THIRD_PARTY_HOST_RE.search(line)
        if m:
            res.add(n, "external-evidence", WARN, m.group(0),
                    "attach the video/screenshot to the report; off-platform links rot and aren't trusted")

    # Walls of un-trimmed output: keep only the load-bearing lines, mark the rest [snip].
    for start, length in oversized_fences(text):
        if "[snip]" not in text:
            res.add(start, "wall-of-output", WARN, f"{length}-line code/output block",
                    "trim to the load-bearing lines and mark the cut with [snip]")

    # Title check: first markdown heading or first non-empty line.
    title = first_title(lines)
    if title:
        if VAGUE_TITLE_RE.search(title):
            res.add(title_line(lines), "vague-title", FAIL, f"'{title.strip()}'",
                    "title must name TYPE + LOCATION + IMPACT (H1 'clear and concise title')")
        elif not re.search(r"\b(in|on|via|allows|lets|enables|exposes|leaks)\b", title, re.I):
            res.add(title_line(lines), "weak-title", WARN, f"'{title.strip()}'",
                    "good titles read '<type> in <endpoint> allows <impact>'")
    return res


def section_body(lines: list[str], name: str) -> tuple[list[str], int]:
    """Return (body_lines, 1-based_start_line) for the markdown section whose heading
    text matches `name` (e.g. 'impact'), up to the next heading. Empty if not found."""
    name = name.lower()
    out, start, capturing = [], 0, False
    for n, line in enumerate(lines, 1):
        h = re.match(r"^#+\s+(.*)", line)
        if h:
            if capturing:
                break
            if h.group(1).strip().lower().startswith(name):
                capturing, start = True, n + 1
            continue
        if capturing:
            out.append(line)
    return out, start


def oversized_fences(text: str, limit: int = 50) -> list[tuple[int, int]]:
    """Line ranges of fenced code blocks longer than `limit` lines: (start_line, length)."""
    spans, in_fence, fence_start, count = [], False, 0, 0
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            if in_fence:
                if count > limit:
                    spans.append((fence_start, count))
                in_fence = False
            else:
                in_fence, fence_start, count = True, n, 0
            continue
        if in_fence:
            count += 1
    return spans


def strip_fences(text: str) -> str:
    out, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def split_sentences(text: str) -> list[str]:
    # collapse whitespace, then split on sentence enders; skip markdown list/heading noise
    flat = re.sub(r"\s+", " ", re.sub(r"`[^`]*`", "", text))
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat) if s.strip()]


# Heading labels from the 05 template — when a heading is just the section name, the real
# title is the line under it, not the heading word.
SECTION_LABELS = {"title", "summary", "severity", "affected asset", "steps to reproduce",
                  "proof of concept", "impact", "remediation", "references"}


def first_title(lines: list[str]) -> str:
    for n, line in enumerate(lines):
        m = re.match(r"^#+\s+(.*)", line)
        if m:
            head = m.group(1).strip()
            if head.lower() in SECTION_LABELS:
                # template style: real title is the next non-empty line
                for nxt in lines[n + 1:]:
                    if nxt.strip():
                        return nxt.strip()
                return head
            return head
        if line.strip().lower().startswith(("title:", "**title")):
            return re.sub(r"(?i)^\**title:?\**\s*", "", line.strip())
    for line in lines:
        if line.strip():
            return line.strip()
    return ""


def title_line(lines: list[str]) -> int:
    for n, line in enumerate(lines, 1):
        if re.match(r"^#+\s+", line) or line.strip().lower().startswith("title"):
            return n
    return 1


def render(res: Result, path: str) -> str:
    out = [f"## report_lint: {path}"]
    if res.fixed:
        out.append(f"FIXED {res.em_dash_count} em/en dash(es) → plain punctuation.")
    if res.em_dash_count and not res.fixed:
        out.append(f"FAIL  {res.em_dash_count} em/en dash(es) present — run with --fix.")
    elif not res.em_dash_count:
        out.append("PASS  no em dashes.")
    if res.cvss_version:
        out.append(f"INFO  CVSS {res.cvss_version} vector — confirm this matches the program's configured version.")
    for i in sorted(res.issues, key=lambda x: (x.status != FAIL, x.line)):
        loc = f"L{i.line}" if i.line else "doc"
        sug = f"  → {i.suggestion}" if i.suggestion else ""
        out.append(f"  [{i.status}] {loc} {i.rule}: {i.detail}{sug}")
    f, w = len(res.fails), len(res.warns)
    out.append(f"\n{f} FAIL · {w} WARN" + ("" if (f or res.em_dash_count and not res.fixed) else " · clean"))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Em-dash + grammar/style linter for H1 report drafts.")
    ap.add_argument("path", help="report markdown file, or - for stdin")
    ap.add_argument("--fix", action="store_true", help="rewrite em dashes to plain punctuation")
    ap.add_argument("-o", "--output", help="write fixed copy here (default: in place; stdout for -)")
    ap.add_argument("--strict", action="store_true", help="style WARNs also fail")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if args.path == "-":
        text = sys.stdin.read()
        src = None
    else:
        src = Path(args.path)
        if not src.is_file():
            print(f"error: not a file: {args.path}", file=sys.stderr)
            return 2
        text = src.read_text(encoding="utf-8", errors="replace")

    fixed = False
    remaining = len(EMDASH_CHAR_RE.findall(text)) + len(ASCII_DDASH_RE.findall(text))
    if args.fix and remaining:
        text, _ = fix_em_dashes(text)
        remaining = len(EMDASH_CHAR_RE.findall(text)) + len(ASCII_DDASH_RE.findall(text))
        fixed = True
        dest = Path(args.output) if args.output else src
        if dest is None:  # stdin + --fix with no -o: emit to stdout
            sys.stdout.write(text)
        else:
            dest.write_text(text, encoding="utf-8")

    res = lint(text, em_dashes_remaining=remaining)
    res.fixed = fixed

    if args.json:
        print(json.dumps({
            "path": args.path,
            "em_dashes_remaining": remaining,
            "cvss_version": res.cvss_version,
            "fixed": fixed,
            "issues": [vars(i) for i in res.issues],
            "fail": len(res.fails),
            "warn": len(res.warns),
        }, indent=2))
    else:
        if not (args.fix and src is None and not args.output):
            print(render(res, args.path))

    hard_fail = bool(res.fails) or (remaining and not fixed)
    if args.strict and res.warns:
        hard_fail = True
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
