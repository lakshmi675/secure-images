#!/usr/bin/env python3
"""Build the static site: dist/index.html (self-contained) + dist/catalog.json."""
import argparse, datetime, glob, json, os, yaml

ap = argparse.ArgumentParser()
ap.add_argument("--data", default="data")
ap.add_argument("--out", default="dist")
ap.add_argument("--registry", default=os.environ.get("REGISTRY_PREFIX", "ghcr.io/OWNER"))
ap.add_argument("--title", default="Sealed Images")
a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__))

keys = ["name", "title", "category", "summary", "description", "license", "homepage", "runtime", "quickstart", "notes"]
images = []
for path in sorted(glob.glob("images/*/image.yaml")):
    m = yaml.safe_load(open(path))
    lines, cfg = [], m["lines"]
    if isinstance(cfg, dict):
        d = f'{a.data}/builds/{m["name"]}'
        ids = sorted((f[:-5] for f in os.listdir(d) if f.endswith(".json")),
                     key=lambda x: tuple(map(int, x.split(".")))) if os.path.isdir(d) else []
        cfg = [{"id": i, "jdk": m["lines"].get("jdk", {}).get(i, m["lines"]["default_jdk"])} for i in ids]
    for l in cfg:
        p = f'{a.data}/builds/{m["name"]}/{l["id"]}.json'
        builds = json.load(open(p)) if os.path.exists(p) else []
        lines.append({"id": l["id"], "runtime": f'JDK {l["jdk"]}', "builds": builds[:30]})
    images.append({k: m.get(k) for k in keys} | {"lines": lines})

catalog = {
    "title": a.title, "registry": a.registry, "images": images,
    "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "demo": os.path.exists(f"{a.data}/DEMO"),
}
os.makedirs(a.out, exist_ok=True)
json.dump(catalog, open(f"{a.out}/catalog.json", "w"), indent=1)
html = open(f"{here}/template.html").read()
open(f"{a.out}/index.html", "w").write(html.replace("/*DATA*/", json.dumps(catalog).replace("</", "<\\/")))
print(f"site written to {a.out}/ ({len(images)} images)")
