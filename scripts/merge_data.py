#!/usr/bin/env python3
"""Merge build records into the data branch checkout.

data/builds/<image>/<line>.json      newest-first history (no component lists)
data/components/<image>/<line>.json  component list of the latest build, for diffing
"""
import glob, json, os, sys

MAX_HISTORY = 200


def load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def diff(old, new):
    if old is None:
        return None
    return {
        "added": sorted(f"{k} {v}" for k, v in new.items() if k not in old),
        "removed": sorted(f"{k} {v}" for k, v in old.items() if k not in new),
        "updated": sorted(f"{k} {old[k]} -> {new[k]}" for k in new if k in old and old[k] != new[k]),
    }


def main(records_dir, data_dir):
    for path in sorted(glob.glob(f"{records_dir}/**/*.json", recursive=True)):
        rec = json.load(open(path))
        img, line = rec["image"], rec["line"]
        bpath = f"{data_dir}/builds/{img}/{line}.json"
        cpath = f"{data_dir}/components/{img}/{line}.json"
        comps = rec.pop("components")
        rec["changes"] = diff(load(cpath, None), comps)
        builds = load(bpath, [])
        builds.insert(0, rec)
        for p, obj in ((bpath, builds[:MAX_HISTORY]), (cpath, comps)):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            json.dump(obj, open(p, "w"), indent=1)
        print(f"merged {img}:{line} {rec['tag']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
