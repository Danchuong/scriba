# Agent 4: Cross-References & Links Audit

**Score: 6.5/10**

## Critical Findings

### C1: 6 Broken Links to Removed fastforward Extension

| Source File | Line | Target | Status |
|---|---|---|---|
| planning/phase-c.md | 403 | ../extensions/fastforward.md | 404 |
| planning/implementation-phases.md | 322 | ../extensions/fastforward.md | 404 |
| planning/roadmap.md | 276 | ../extensions/fastforward.md | 404 |
| planning/roadmap.md | 376 | ../extensions/fastforward.md | 404 |
| guides/tex-plugin.md | 7 | ../TEX-RENDERER-BACKEND-ONLY.md | 404 |
| archive/verify-2026-04-09.md | 88 | path.md | Malformed |

### C2: CSS Class Name Mismatch in README

README.md line 49 says `scriba-filmstrip` but spec uses `scriba-frames`.

## High Findings

### H1: 8 Active Docs Reference Removed \fastforward

| File | Count |
|---|---|
| planning/phase-c.md | 1 |
| planning/implementation-phases.md | 2 |
| planning/roadmap.md | 2 |
| primitives/metricplot.md | 2 |
| README.md | 1 |

## Medium Findings

### M1: Non-standard Section Numbering

`spec/environments.md` line 756: Section `8.0` should be `8`.

## Archive Assessment: ✓ GOOD

- 14 audit/verification reports properly archived
- PHASE-D-PLAN.md preserved as historical artifact
- No spec files wrongly archived
- No duplication between active and archived docs

## Recommended Fixes

1. Replace `scriba-filmstrip` → `scriba-frames` in README.md:49
2. Remove/redirect 6 broken links to fastforward.md
3. Find/restore TEX-RENDERER-BACKEND-ONLY.md or fix tex-plugin.md:7
4. Remove fastforward references from planning docs
5. Fix section numbering in environments.md
