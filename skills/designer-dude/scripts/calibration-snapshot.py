#!/usr/bin/env python3
"""Freeze and verify versioned calibration artifacts.

Unlike a live-site note, a snapshot can be replayed after the reference site
redesigns. The manifest binds every artifact to bytes, capture environment,
source URL and review date.
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
import urllib.parse

ALLOWED = {".json", ".png", ".yml", ".yaml", ".html", ".md"}
MAX_AGE_DAYS = 90
REQUIRED_ENVIRONMENT = {
    "os", "architecture", "playwrightVersion", "designerDudeVersion",
    "browserVersions", "fontFingerprintSha256",
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def environment_errors(env):
    errors = []
    missing = sorted(key for key in REQUIRED_ENVIRONMENT if not env.get(key))
    if missing:
        errors.append("environment missing: " + ", ".join(missing))
    browsers = env.get("browserVersions") if isinstance(env.get("browserVersions"), dict) else {}
    for engine in ("chromium", "firefox", "webkit"):
        value = str(browsers.get(engine) or "").strip().lower()
        if not value or value in {"unknown", "unavailable", "false"}:
            errors.append(f"environment.browserVersions.{engine} is missing or unavailable")
    fingerprint = str(env.get("fontFingerprintSha256") or "").lower()
    if len(fingerprint) != 64 or any(ch not in "0123456789abcdef" for ch in fingerprint):
        errors.append("environment.fontFingerprintSha256 is invalid")
    return errors


def artifact_class_errors(files):
    suffixes = {pathlib.PurePosixPath(str(item.get("path") or "")).suffix.lower()
                for item in files if isinstance(item, dict)}
    errors = []
    for label, choices in (("probe JSON", {".json"}), ("screenshot", {".png"}),
                           ("ARIA tree", {".yml", ".yaml"}), ("review report", {".md"})):
        if not suffixes & choices:
            errors.append(f"snapshot has no {label} artifact")
    return errors


def freeze(args):
    root = pathlib.Path(args.root).resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    files = []
    out_resolved = pathlib.Path(args.out).resolve()
    for path in sorted(x for x in root.rglob("*") if x.is_file() and x.suffix.lower() in ALLOWED):
        if path.resolve() == out_resolved:
            continue
        try:
            path.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError(f"artifact resolves outside snapshot root: {path.relative_to(root)}") from exc
        files.append({"path": path.relative_to(root).as_posix(), "sha256": digest(path),
                      "bytes": path.stat().st_size})
    if not files:
        raise ValueError("snapshot root contains no supported artifacts")
    if not args.environment:
        raise ValueError("--environment is required for a replayable snapshot")
    env = json.loads(pathlib.Path(args.environment).read_text())
    if not isinstance(env, dict):
        raise ValueError("environment JSON must be an object")
    env_errors = environment_errors(env)
    if env_errors:
        raise ValueError("; ".join(env_errors))
    class_errors = artifact_class_errors(files)
    if class_errors:
        raise ValueError("; ".join(class_errors))
    doc = {"schema": "designer-dude-calibration-snapshot/v1", "label": args.label,
           "capturedAt": utcnow().isoformat(), "sourceUrls": sorted(set(args.source_url or [])),
           "environment": env, "artifacts": files}
    if not doc["sourceUrls"]:
        raise ValueError("at least one --source-url is required")
    if any(urllib.parse.urlparse(url).scheme not in {"http", "https"} or
           not urllib.parse.urlparse(url).netloc for url in doc["sourceUrls"]):
        raise ValueError("every --source-url must be an absolute HTTP(S) URL")
    if not str(args.label or "").strip():
        raise ValueError("--label is required")
    target = pathlib.Path(args.out); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"calibration snapshot: {len(files)} artifacts -> {target}")
    return 0


def verify(args):
    manifest_path = pathlib.Path(args.manifest).resolve()
    try:
        doc = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read manifest: {exc}") from exc
    errors = []
    if not 0 <= args.max_age_days <= MAX_AGE_DAYS:
        errors.append(f"max_age_days must be between 0 and {MAX_AGE_DAYS} for perfection evidence")
    if doc.get("schema") != "designer-dude-calibration-snapshot/v1":
        errors.append("unsupported schema")
    if not str(doc.get("label") or "").strip(): errors.append("label is missing")
    try:
        captured = datetime.datetime.fromisoformat(str(doc.get("capturedAt") or "").replace("Z", "+00:00"))
        if captured.tzinfo is None: captured = captured.replace(tzinfo=datetime.timezone.utc)
        age = (utcnow() - captured.astimezone(datetime.timezone.utc)).days
        if age < -1: errors.append("capturedAt is in the future")
        if age > args.max_age_days: errors.append(f"snapshot is stale ({age} days; max {args.max_age_days})")
    except ValueError:
        age = None; errors.append("capturedAt is invalid")
    if not doc.get("sourceUrls"): errors.append("sourceUrls is empty")
    elif any(urllib.parse.urlparse(str(url)).scheme not in {"http", "https"} or
             not urllib.parse.urlparse(str(url)).netloc for url in doc.get("sourceUrls", [])):
        errors.append("sourceUrls contains a non-HTTP(S) URL")
    env = doc.get("environment") if isinstance(doc.get("environment"), dict) else {}
    errors.extend(environment_errors(env))
    root = pathlib.Path(args.root).resolve() if args.root else manifest_path.parent
    seen = set()
    for item in doc.get("artifacts", []) if isinstance(doc.get("artifacts"), list) else []:
        rel = str(item.get("path") or "")
        if not rel or rel in seen or pathlib.PurePosixPath(rel).is_absolute() or ".." in pathlib.PurePosixPath(rel).parts:
            errors.append(f"unsafe, blank or duplicate artifact path: {rel!r}"); continue
        seen.add(rel); path = root / pathlib.PurePosixPath(rel)
        try:
            path.resolve().relative_to(root)
        except ValueError:
            errors.append(f"artifact resolves outside snapshot root: {rel}"); continue
        if not path.is_file(): errors.append(f"missing artifact: {rel}"); continue
        if digest(path) != item.get("sha256"): errors.append(f"sha256 mismatch: {rel}")
        if path.stat().st_size != item.get("bytes"): errors.append(f"byte-size mismatch: {rel}")
    if not seen: errors.append("artifact list is empty")
    errors.extend(artifact_class_errors(doc.get("artifacts") or []))
    bundle_root = pathlib.Path(args.bundle_root).resolve()
    try:
        manifest_path.relative_to(bundle_root)
        root.relative_to(bundle_root)
        bundle_contained = True
    except ValueError:
        bundle_contained = False
        errors.append("manifest and snapshot root must be contained by bundle_root")
    bundle_artifacts = ([{"path": manifest_path.relative_to(bundle_root).as_posix(),
                          "sha256": digest(manifest_path), "kind": "calibration-manifest"}]
                        if bundle_contained else [])
    for item in doc.get("artifacts", []) if isinstance(doc.get("artifacts"), list) else []:
        rel = str(item.get("path") or "")
        path = root / pathlib.PurePosixPath(rel)
        try:
            bundle_path = path.resolve().relative_to(bundle_root).as_posix()
        except ValueError:
            continue
        bundle_artifacts.append({"path": bundle_path,
                                 "sha256": str(item.get("sha256") or "").lower(),
                                 "kind": "calibration-artifact"})
    result = {"schema": "designer-dude-calibration-verification/v1",
              "verifiedAt": utcnow().isoformat(), "manifest": str(manifest_path),
              "manifestSha256": digest(manifest_path),
              "artifacts": bundle_artifacts,
              "thresholds": {"maxAgeDays": args.max_age_days},
              "status": "pass" if not errors else "fail", "ageDays": age,
              "artifactCount": len(seen), "errors": errors}
    payload = json.dumps(result, indent=2) + "\n"
    if args.out: pathlib.Path(args.out).write_text(payload)
    print(payload, end="")
    return 0 if not errors else 1


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory(prefix="dd-calibration-") as tmp:
        root = pathlib.Path(tmp); (root / "probe.json").write_text('{"ok":true}\n')
        (root / "screen.png").write_bytes(b"png-fixture")
        (root / "tree.aria.yml").write_text("- button 'Save'\n")
        (root / "report.md").write_text("# Review\n")
        environment = root / "environment-source.txt"
        environment.write_text(json.dumps({"os": "fixture-os", "architecture": "x86_64",
            "playwrightVersion": "1.62.0", "designerDudeVersion": "fixture",
            "browserVersions": {"chromium": "1", "firefox": "1", "webkit": "1"},
            "fontFingerprintSha256": "a" * 64}))
        manifest = root / "snapshot.json"
        class F: pass
        f = F(); f.root = str(root); f.out = str(manifest); f.label = "fixture"
        f.source_url = ["https://example.test/frozen"]; f.environment = str(environment)
        if freeze(f): return 1
        class V: pass
        v = V(); v.manifest = str(manifest); v.root = str(root); v.bundle_root = str(root)
        v.max_age_days = 1; v.out = None
        if verify(v): return 1
        v.max_age_days = MAX_AGE_DAYS + 1
        if verify(v) == 0:
            print("calibration-snapshot selftest FAILED: weakened age policy accepted"); return 1
        v.max_age_days = 1
        stale = json.loads(manifest.read_text()); stale["capturedAt"] = "2000-01-01T00:00:00Z"
        manifest.write_text(json.dumps(stale))
        if verify(v) == 0:
            print("calibration-snapshot selftest FAILED: stale snapshot accepted"); return 1
        freeze(f)
        unsafe = json.loads(manifest.read_text()); unsafe["artifacts"][0]["path"] = "../probe.json"
        manifest.write_text(json.dumps(unsafe))
        if verify(v) == 0:
            print("calibration-snapshot selftest FAILED: path traversal accepted"); return 1
        freeze(f)
        (root / "probe.json").write_text('{"ok":false}\n')
        if verify(v) == 0:
            print("calibration-snapshot selftest FAILED: tamper accepted"); return 1
    print("calibration-snapshot selftest ok - current snapshot passes and byte tampering fails")
    return 0


def main():
    if "--selftest" in sys.argv: return selftest()
    ap = argparse.ArgumentParser(description=__doc__); sub = ap.add_subparsers(dest="mode", required=True)
    fr = sub.add_parser("freeze"); fr.add_argument("--root", required=True); fr.add_argument("--out", required=True)
    fr.add_argument("--label", required=True); fr.add_argument("--source-url", action="append")
    fr.add_argument("--environment", help="JSON object describing browser/font/OS/tool versions")
    ve = sub.add_parser("verify"); ve.add_argument("--manifest", required=True); ve.add_argument("--root")
    ve.add_argument("--bundle-root", required=True,
                    help="outer evidence directory used for portable artifact paths")
    ve.add_argument("--max-age-days", type=int, default=MAX_AGE_DAYS); ve.add_argument("--out")
    args = ap.parse_args()
    try: return freeze(args) if args.mode == "freeze" else verify(args)
    except ValueError as exc: print(f"error: {exc}", file=sys.stderr); return 2


if __name__ == "__main__": sys.exit(main())
