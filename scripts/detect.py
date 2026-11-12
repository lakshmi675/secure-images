#!/usr/bin/env python3
"""Daily change detection for every image in images/*/image.yaml.

Emits a build matrix with only the (image, line) pairs whose inputs changed.
Triggers: new upstream release, any pinned input digest changed, new FIXABLE
vulnerabilities in the published image, nothing published yet, or FORCE.
State = OCI labels on the published image (io.secure-images.*), so no database.
"""
import glob, json, os, re, subprocess, sys, urllib.request
import xml.etree.ElementTree as ET
import yaml

NS = "io.secure-images"
STABLE = re.compile(r"^\d+\.\d+\.\d+$")


def sh(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def vkey(v):
    return tuple(map(int, v.split(".")))


def http(url):
    req = urllib.request.Request(url, headers={"User-Agent": "secure-images"})
    return urllib.request.urlopen(req, timeout=30).read()


def upstream_versions(up):
    if up["type"] == "maven":
        url = f'https://repo1.maven.org/maven2/{up["group"].replace(".", "/")}/{up["artifact"]}/maven-metadata.xml'
        versions = [v.text for v in ET.fromstring(http(url)).iter("version")]
    elif up["type"] == "github":
        rel = json.loads(http(f'https://api.github.com/repos/{up["repo"]}/releases?per_page=100'))
        pre = up.get("tag_prefix", "v")
        versions = [r["tag_name"][len(pre):] for r in rel
                    if not r["draft"] and not r["prerelease"] and r["tag_name"].startswith(pre)]
    else:
        sys.exit(f'unknown upstream type {up["type"]}')
    return versions


def latest_upstream(up, line):
    cands = [v for v in upstream_versions(up) if STABLE.match(v) and v.startswith(line + ".")]
    if not cands:
        sys.exit(f"no stable release for line {line}")
    return max(cands, key=vkey)


def lines_for(meta, versions=None):
    """Fixed list, or discover stable major.minor lines from upstream."""
    cfg = meta["lines"]
    if isinstance(cfg, list):
        return cfg
    versions = versions or upstream_versions(meta["upstream"])
    mm = lambda x: tuple(map(int, x.split(".")))
    found = {".".join(v.split(".")[:2]) for v in versions if STABLE.match(v)}
    return [{"id": l, "jdk": cfg.get("jdk", {}).get(l, cfg["default_jdk"])}
            for l in sorted(found, key=mm) if mm(l) >= mm(cfg["min"]) and l not in cfg.get("exclude", [])]


def pin(ref):
    return f'{ref.rsplit(":", 1)[0]}@{sh("crane", "digest", ref)}'


def parse_pins(s):
    return dict(p.split("=", 1) for p in (s or "").split(";") if "=" in p)


def published_labels(ref):
    try:
        return (json.loads(sh("crane", "config", ref)).get("config") or {}).get("Labels") or {}
    except subprocess.CalledProcessError:
        return None


def fixable_ids(ref):
    out = sh("trivy", "image", "--quiet", "--scanners", "vuln", "--ignore-unfixed", "--format", "json", ref)
    return {v["VulnerabilityID"] for r in (json.loads(out).get("Results") or []) for v in (r.get("Vulnerabilities") or [])}


def main():
    prefix = os.environ["REGISTRY_PREFIX"]
    force = os.environ.get("FORCE", "false").lower() == "true"
    only_img, only_line = (os.environ.get("ONLY", "").split(":") + [""])[:2]
    include, report = [], []
    for path in sorted(glob.glob("images/*/image.yaml")):
        meta = yaml.safe_load(open(path))
        name = meta["name"]
        if only_img and only_img != name:
            continue
        for line in lines_for(meta):
            lid = line["id"]
            if only_line and only_line != lid:
                continue
            version = latest_upstream(meta["upstream"], lid)
            ctx = dict(line, version=version, major=lid.split(".")[0], line=lid)
            pins = {k: pin(v.format(**ctx)) for k, v in meta["pins"].items()}
            pin_digests = {k: v.split("@")[1] for k, v in pins.items()}
            ref = f"{prefix}/{name}:{lid}"
            labels = published_labels(ref)
            reasons = []
            if force:
                reasons.append("forced")
            if labels is None:
                reasons.append("first build")
            else:
                if labels.get(f"{NS}.version") != version:
                    reasons.append(f'new upstream release {labels.get(f"{NS}.version")} -> {version}')
                old = parse_pins(labels.get(f"{NS}.pins"))
                for k, d in pin_digests.items():
                    if old.get(k) != d:
                        reasons.append(f"{k} updated")
                prev = set(labels.get(f"{NS}.fixable-vulns", "").split())
                new = fixable_ids(ref) - prev
                if new:
                    reasons.append("new fixable vulns: " + ", ".join(sorted(new)[:10]))
            report.append(f"| {name} | {lid} | {version} | {'; '.join(reasons) or 'no change, skipped'} |")
            if reasons:
                args = {**{k: " ".join(v.format(**ctx).split()) for k, v in meta.get("build_args", {}).items()}, **pins}
                include.append({
                    "image": name, "context": os.path.dirname(path), "id": lid, "version": version,
                    "build_args": "\n".join(f"{k}={v}" for k, v in args.items()),
                    "pins": ";".join(f"{k}={v}" for k, v in pin_digests.items()),
                    "platforms": meta["platforms"],
                    "baseline": meta.get("baseline", "").format(**ctx),
                    "reasons": "; ".join(reasons),
                })
    summary = "### Change detection\n| image | line | latest | decision |\n|---|---|---|---|\n" + "\n".join(report)
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(summary + "\n")
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/stdout"), "a") as out:
        out.write(f"matrix={json.dumps(include, separators=(',', ':'))}\n")
        out.write(f"any={'true' if include else 'false'}\n")


if __name__ == "__main__":
    main()
