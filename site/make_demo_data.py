#!/usr/bin/env python3
"""Write DEMO build history so the site can be previewed locally:
   python site/make_demo_data.py data-demo && python site/generate.py --data data-demo --out dist
Numbers are illustrative only; the site shows a 'demo data' banner when data/DEMO exists."""
import datetime as dt, hashlib, json, os, sys

out = sys.argv[1] if len(sys.argv) > 1 else "data-demo"
now = dt.datetime.now(dt.timezone.utc)
LINES = {"9.0": ("9.0.110", "9.0.108", "17"), "10.1": ("10.1.46", "10.1.44", "21"), "11.0": ("11.0.12", "11.0.10", "21")}


def rec(line, ver, hours_ago, reasons, changes, vulns, fixable):
    stamp = (now - dt.timedelta(hours=hours_ago)).strftime("%Y%m%d%H%M")
    return {
        "image": "tomcat", "line": line, "version": ver, "tag": f"{ver}-{stamp}",
        "digest": "sha256:" + hashlib.sha256(f"{ver}{stamp}".encode()).hexdigest(),
        "built_at": (now - dt.timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reasons": reasons, "size_mb": 121.4, "packages": 87,
        "vulns": {"critical": 0, "high": vulns[0], "medium": vulns[1], "low": vulns[2], "fixable": fixable},
        "baseline": {"ref": f"tomcat:{ver}-jdk{LINES[line][2]}-temurin", "size_mb": 312.0,
                     "vulns": {"critical": 1, "high": 9, "medium": 41, "low": 63, "fixable": 34}},
        "changes": changes,
    }


for line, (new, old, _) in LINES.items():
    builds = [
        rec(line, new, 3, [f"new upstream release {old} -> {new}", "BASE_IMAGE updated"],
            {"added": [], "removed": [], "updated": [f"tomcat-embed-core {old} -> {new}", "libssl3 3.0.16-1 -> 3.0.17-1"]}, (0, 1, 4), 0),
        rec(line, old, 27, ["JDK_IMAGE updated"], {"added": [], "removed": [], "updated": ["openjdk 21.0.7 -> 21.0.8"]}, (0, 1, 4), 0),
        rec(line, old, 51, ["new fixable vulns: CVE-2026-0001"], {"added": [], "removed": [], "updated": ["zlib1g 1:1.2.13 -> 1:1.2.14"]}, (0, 2, 4), 1),
        rec(line, old, 75, ["first build"], None, (0, 2, 5), 0),
    ]
    os.makedirs(f"{out}/builds/tomcat", exist_ok=True)
    json.dump(builds, open(f"{out}/builds/tomcat/{line}.json", "w"), indent=1)
open(f"{out}/DEMO", "w").write("demo\n")
