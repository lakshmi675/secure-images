# Sealed Images

A catalog of hardened container images that rebuild themselves daily, plus the site that publishes them.
Tomcat (9.0, 10.1, 11.0) is the first image. Adding software means adding a directory under `images/`.

## Pieces
| Piece | Where |
|---|---|
| Image definition (versions, pins, upstream source, docs) | `images/<name>/image.yaml` |
| Build recipe | `images/<name>/Dockerfile`, `rootfs/`, `tests/`, `smoke-test.sh` |
| Change detection | `scripts/detect.py` |
| Daily build, test, scan, sign | `.github/workflows/daily-build.yml` |
| Build history (data branch) | `scripts/record_build.py`, `scripts/merge_data.py` |
| Site | `site/template.html`, `site/generate.py`, `.github/workflows/site.yml` |

## Daily flow
1. `detect` checks each line for: a new upstream release, a changed pinned digest (base image, JDK), or new
   *fixable* vulnerabilities in the published image. No change means no build.
2. `build` runs per changed line: verify source, build, harden, assemble, smoke test, scan, push with an
   immutable timestamp tag, sign (cosign keyless), attach SBOM and vulnerability attestations, then move the
   floating tags (`10.1.46`, `10.1`).
3. Each build writes a record (CVE counts, size, component list). `site.yml` merges records into the `data`
   branch, diffs components against the previous build to produce the changelog, regenerates the site and
   deploys it to GitHub Pages.

State lives in OCI labels on the images and in the `data` branch. There is no database or server.

## Setup
1. Run `images/tomcat/fetch-keys.sh`, check the key fingerprints against tomcat.apache.org, commit `keys/`.
2. Repo settings: Actions can write packages; Pages source = GitHub Actions; make the GHCR packages public.
3. Run **daily-build** manually with `force=true`. The site goes live when it finishes.
4. Preview the site without running the pipeline:
   `python site/make_demo_data.py data-demo && python site/generate.py --data data-demo --out dist`

## Adding a new image
Copy `images/tomcat/` to `images/<name>/`, then edit `image.yaml` (upstream source, pins, build args, lines),
the `Dockerfile`, and `smoke-test.sh`. `detect.py` supports `maven` and `github` upstream types; add a resolver
in `latest_upstream()` for others. The workflow and site pick the image up automatically.

## Known limits
- Only the Tomcat layer is built from source. The base (distroless/Debian) and JRE (Temurin) are binaries.
- The site is one self-contained page with hash routes. Fine for dozens of images; generate one HTML page per image
  if you need search-engine indexing.
- Not yet built: security advisory feed, Helm charts, `-dev` variants, custom image builder, tag retention.
- "Hardened" means the configuration at build time, not a guarantee of zero vulnerabilities. Keep that disclaimer on the site.
- Trademarks: show upstream names only to identify the software, and say so on the site (Minimus does the same).
