#!/usr/bin/env python3
"""Turn one build's scan + SBOM output into a JSON record for the site."""
import argparse, json, datetime

SEV = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def counts(path):
    if not path:
        return None
    try:
        data = json.load(open(path))
    except (OSError, ValueError):
        return None
    seen, fixable = {}, set()
    for r in data.get("Results") or []:
        for v in r.get("Vulnerabilities") or []:
            seen[v["VulnerabilityID"]] = v.get("Severity", "UNKNOWN")
            if v.get("FixedVersion"):
                fixable.add(v["VulnerabilityID"])
    out = {s.lower(): sum(1 for x in seen.values() if x == s) for s in SEV}
    out["fixable"] = len(fixable)
    return out


def components(path):
    comps = {}
    for p in json.load(open(path)).get("packages", []):
        if p.get("primaryPackagePurpose") == "CONTAINER" or not p.get("versionInfo"):
            continue
        comps.setdefault(p["name"], set()).add(p["versionInfo"])
    return {k: ",".join(sorted(v)) for k, v in sorted(comps.items())}


ap = argparse.ArgumentParser()
for a in ["image", "line", "version", "tag", "digest", "reasons", "sbom", "trivy", "out"]:
    ap.add_argument(f"--{a}", required=True)
for a in ["baseline-trivy", "baseline-ref"]:
    ap.add_argument(f"--{a}", default="")
ap.add_argument("--size-bytes", type=int, default=0)
ap.add_argument("--baseline-size-bytes", type=int, default=0)
a = ap.parse_args()

comps = components(a.sbom)
base = counts(a.baseline_trivy)
rec = {
    "image": a.image, "line": a.line, "version": a.version, "tag": a.tag, "digest": a.digest,
    "built_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "reasons": [r for r in a.reasons.split("; ") if r],
    "size_mb": round(a.size_bytes / 1e6, 1), "packages": len(comps),
    "vulns": counts(a.trivy),
    "baseline": {"ref": a.baseline_ref, "size_mb": round(a.baseline_size_bytes / 1e6, 1), "vulns": base} if base else None,
    "components": comps,
}
json.dump(rec, open(a.out, "w"), indent=1)
