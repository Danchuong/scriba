# KaTeX Bundling Strategy for Scriba

> Status: research, not a decision. Feeds open question **Q32** in
> [`../07-open-questions.md`](../../planning/open-questions.md).

## Problem

`scriba.tex.TexRenderer` spawns a Node.js subprocess that `require()`s
the `katex` npm package (pinned to 0.16.11 inside `katex_worker.js`).
Today, Scriba assumes `katex` is already present on the host — either
installed globally (`npm install -g katex@0.16.11`) or resolvable via
the `NODE_PATH` that Scriba auto-derives from `npm root -g`.

This works on the ojcloud container because the image pre-installs
KaTeX. It does **not** work on a fresh `pip install scriba`, where the
user has never heard of npm and expects a Python package to Just Work.

A new runtime probe (`_probe_runtime` in `scriba/tex/renderer.py`) now
fails fast with an actionable error telling the user to run
`npm install -g katex@0.16.11`, but that is still a friction point
compared to a single `pip install`. This document evaluates three
paths forward.

## Options

### Option 1 — Status quo: require global `npm install -g katex@0.16.11`

The current model. Document the prerequisite in the README. The runtime
probe ensures fresh users get a clear error instead of a cryptic
`MODULE_NOT_FOUND` deep inside a Node subprocess.

| Dimension           | Assessment                                        |
|---------------------|---------------------------------------------------|
| Wheel size impact   | 0 bytes — nothing new shipped.                    |
| First-run UX        | Poor. User must install Node + npm + run a second install command before anything works. |
| Offline story       | Best. Once installed, no network ever needed.     |
| Release eng cost    | ~0. No new build step.                            |
| Supply-chain story  | User owns their npm global tree; we pin version in our docs and the probe. |
| Version guarantees  | Weak. User could install a different katex version and we'd only catch it at runtime if it broke output. |

**Verdict.** Cheap to maintain, painful to onboard.

### Option 2 — Bundle KaTeX inside the wheel via `package_data`

Vendor the minimum set of files `katex_worker.js` needs into
`scriba/tex/vendor/katex/`, ship them as `package_data`, and update
`katex_worker.js` to `require` from a relative path
(`./vendor/katex/katex.min.js` or similar) instead of the bare
`katex` module name.

Only the server-side rendering API is used, and Scriba emits HTML
(with KaTeX's own CSS loaded separately from `scriba/tex/static/`).
Fonts live on the client side; the wheel does **not** need to ship
`fonts/` at all.

| File                              | Approx size |
|-----------------------------------|-------------|
| `katex.min.js` (KaTeX 0.16.11)    | ~280 KB     |
| License file                      | ~1 KB       |
| **Total added to wheel**          | **~280 KB** |

| Dimension           | Assessment                                        |
|---------------------|---------------------------------------------------|
| Wheel size impact   | +~280 KB. Current wheel is small; this is still a modest wheel by ML-package standards. |
| First-run UX        | Excellent. `pip install scriba` + `brew install node` is all the user needs. Zero npm commands. |
| Offline story       | Excellent. Everything is in the wheel.            |
| Release eng cost    | Moderate. Need a one-time vendoring script (`scripts/vendor-katex.sh`) that downloads `katex.min.js` + LICENSE for the pinned version, runs a SHA-256 check, and drops the files into `scriba/tex/vendor/katex/`. CI should verify the vendored tree matches the expected hash. |
| Supply-chain story  | Strong. We pin the exact file and its hash at release time. Dependabot/Renovate can watch upstream KaTeX releases. |
| Version guarantees  | Strong. The user cannot accidentally run a wrong version. |

**Caveats.**
- `katex_worker.js` needs a small patch to resolve the vendored file
  via an absolute path computed from `__dirname`. This is a one-line
  change.
- The vendored file is `LICENSE`d under MIT — compatible with Scriba.
  We must keep the KaTeX LICENSE file alongside the bundled asset.
- `katex.min.js` is large enough that we should add it to the wheel
  but **not** to the sdist unless we also ship the vendoring script;
  otherwise, the sdist is a build-time fetch.

**Verdict.** Best UX for OSS users. Wheel size is a non-issue at ~280 KB.

### Option 3 — Lazy install at first use (`scriba install-runtime`)

Ship a small CLI command (`python -m scriba install-runtime` or
`scriba install-runtime`) that runs `npm install katex@0.16.11` into a
user cache directory (`~/.cache/scriba/node_modules/` on Linux,
platform-appropriate elsewhere) and updates `NODE_PATH` at runtime to
point at that cache. Alternatively, auto-run the install on first use
when the runtime probe detects a missing `katex`.

| Dimension           | Assessment                                        |
|---------------------|---------------------------------------------------|
| Wheel size impact   | 0 bytes.                                          |
| First-run UX        | Good, but requires network on first run. Auto-install is magical but brittle; explicit `scriba install-runtime` is discoverable but adds a second command. |
| Offline story       | Poor on first run. Fine afterwards.               |
| Release eng cost    | High. We now maintain a mini package manager: cache dir layout, concurrency (two processes racing on install), cache invalidation when the pinned version bumps, error handling for network failures, handling users behind corporate proxies. |
| Supply-chain story  | Weaker than option 2. We trust whatever npm resolves at install time; a registry compromise on the exact day of install would ship a bad payload. Mitigation: verify a SHA-256 of the tarball against a hash we ship in the wheel — which is most of the work of option 2 anyway. |
| Version guarantees  | Medium. We pin the version string but don't pin the tarball bytes unless we add hash verification. |

**Verdict.** Worst of both worlds: we still depend on npm *and* we
write more code than option 2. The only advantage over option 2 is the
280 KB saved in the wheel, which is negligible.

## Comparison summary

| Dimension         | 1. Status quo | 2. Bundle   | 3. Lazy install |
|-------------------|---------------|-------------|-----------------|
| Wheel size delta  | 0             | +~280 KB    | 0               |
| First-run UX      | Poor          | Excellent   | Good            |
| Offline first run | N/A           | Yes         | No              |
| npm required      | Yes           | No          | Yes             |
| Release eng cost  | ~0            | Low         | High            |
| Version pinning   | Weak          | Strong      | Medium          |
| Supply chain      | User-owned    | Pinned hash | Trust-on-install |

## Recommendation

**Adopt Option 2 — bundle `katex.min.js` inside the wheel via
`package_data`.**

Reasoning:

1. **280 KB is free.** A Python package that ships a Node subprocess
   and a syntax-highlighting theme set is already in the mid-size
   bracket. Adding 280 KB to guarantee zero-install math rendering is
   an obvious trade.
2. **OSS UX matters.** A user who runs `pip install scriba` and hits a
   `run npm install -g katex@0.16.11` error is likely to close the tab.
   Every step between install and first success costs users.
3. **Supply chain hygiene.** Pinning the file hash in the wheel is
   strictly safer than pinning a version string resolved by npm at
   first run.
4. **Release engineering cost is one shell script.** A vendoring
   script that downloads `katex.min.js` for the pinned version, checks
   a SHA-256, and writes into `scriba/tex/vendor/katex/` is ~30 lines.
   CI runs it in a nightly job to flag upstream releases.
5. **Option 3 doesn't justify its complexity.** The only thing it buys
   over option 2 is saved wheel size, and wheel size is not the
   bottleneck.

### Implementation sketch (out of scope for this document)

1. Add `scripts/vendor-katex.sh` that fetches
   `https://registry.npmjs.org/katex/-/katex-0.16.11.tgz`, verifies a
   known SHA-256, extracts `dist/katex.min.js` + `LICENSE`, writes to
   `scriba/tex/vendor/katex/`.
2. Add `scriba/tex/vendor/katex/` to `package_data` in `pyproject.toml`
   and ensure it is included in the wheel.
3. Patch `katex_worker.js` to resolve the vendored file:
   ```js
   const path = require('path');
   const katex = require(path.join(__dirname, 'vendor', 'katex', 'katex.min.js'));
   ```
4. Remove the `NODE_PATH` auto-discovery dance and the
   `_probe_runtime` `katex` check — only the `node` binary check
   remains.
5. Keep `_probe_runtime` for the `node` binary check; that prerequisite
   cannot be bundled.
6. Bump wheel version and release notes: "KaTeX now bundled; no more
   `npm install -g katex` required."

### Non-goals

- Bundling Node.js itself. That would push wheel size from ~280 KB to
  ~60 MB and require per-platform wheels. Node is a real prerequisite
  and `brew install node` / `apt install nodejs` is acceptable friction.
- Bundling Pygments themes as JavaScript. Already handled via Python.

## Revisit triggers

- Upstream KaTeX ships a major version with breaking changes.
- A user reports the bundled size is a problem on constrained targets
  (AWS Lambda layers near the 250 MB limit, for instance).
- The vendoring script breaks in CI on a KaTeX release.
