# Wave 8 — Architecture: External `scriba.js` + Strict CSP

**Origin:** Wave 7 findings W7-M12, W7-M13
**Effort:** Medium (~1-2 days)
**Risk:** Medium — touches every emitted HTML page, breaks any consumer relying on inline JS
**Goal:** Make every Scriba-generated page servable under a strict CSP without `'unsafe-inline'` for scripts.

---

## Problem Statement

Current emitter inlines everything into the rendered HTML:

- ~60 KB inline `<script>` block per page (≈11.7 KB runtime + ≈48.5 KB serialised frame data)
- Inline `onclick=` handlers on player controls
- A few inline event listeners attached after DOM ready

This blocks any deployment under a real production CSP:

- `script-src 'self'` rejects every inline block
- `script-src 'self' 'unsafe-inline'` defeats the purpose of CSP
- Even with `'nonce-...'`, every inline payload would need stamping per request — impractical for static output

Symptom in the wild: enterprise wikis, Notion-style hosts, and corporate intranets that enforce CSP silently drop Scriba widgets.

---

## Target State

1. **`scriba.js`** — single static asset shipped with the library.
   - Pure runtime (player controls, frame stepping, prefers-reduced-motion handling, MutationObserver, WAAPI).
   - Zero per-render variability — fully cacheable, hashable, SRI-friendly.
   - Loaded via `<script src="scriba.js" defer>` (or with `nonce` if host inserts one).

2. **Frame data as `<script type="application/json">`** — non-executing data island.
   - Browsers will not run `type="application/json"` blocks, so CSP need not whitelist them.
   - Runtime reads it via `document.getElementById(...).textContent` + `JSON.parse`.
   - Per-page payload, but inert.

3. **Event handlers via `addEventListener`** — no `onclick=` attributes left in markup.
   - Use `data-scriba-action="play|pause|step|restart"` attributes.
   - Single delegated listener in `scriba.js` dispatches by `data-*` value.

4. **CSP recommendation in docs**:
   - `script-src 'self'` (or `'self' 'nonce-X'` for hosts that nonce everything).
   - `style-src 'self' 'unsafe-inline'` (Scriba still inlines per-render CSS — separate refactor, not in this wave).
   - `object-src 'none'`, `base-uri 'self'`.

---

## Migration Strategy

### Phase 1 — Asset extraction
- Move `_RUNTIME_JS` (or whatever the inline runtime currently is) into a real `scriba.js` source file inside the package.
- Add a build step (or runtime read at startup) that loads it as bytes.
- Compute its SHA-384 once; expose for SRI.

### Phase 2 — Emit changes
- `emitter.py` stops embedding the runtime block.
- Emits a `<script src="{base_url}/scriba.js" integrity="sha384-..." crossorigin="anonymous" defer></script>` instead.
- Per-render JSON island for frames.
- Replace every `onclick=` with `data-scriba-action=`.

### Phase 3 — Deployment surface
- `render.py` gains `--asset-base-url` and `--inline-runtime` flags.
  - `--asset-base-url https://cdn.example.com/scriba/0.8.3` for hosted setups.
  - `--inline-runtime` keeps current behaviour for local-file viewing (no HTTP context).
- Default behaviour: copy `scriba.js` next to the output HTML and reference relatively.

### Phase 4 — Docs + examples
- Add a "CSP-strict deployment" guide.
- Update tutorial fixtures showing both inline-runtime and external-runtime modes.
- Provide ready-to-paste CSP header example.

---

## Backwards Compatibility

| Audience | Impact | Mitigation |
|---|---|---|
| Local-file users (`file://`) | Would break — `file://` cross-origin script loads fail | `--inline-runtime` default for `file://` outputs, or auto-detect |
| Static-site embeds | Need to upload `scriba.js` once per deploy | Document; provide `scriba export-runtime --to <dir>` helper |
| Existing rendered HTML in the wild | No change — old files still self-contained | New behaviour opt-in via flag, default flips in v0.9 |

Default flip is the breaking moment. Plan: ship as opt-in in v0.8.3, flip default in v0.9.0, drop inline-runtime in v1.0.

---

## Risks

- **CDN dependency** for hosted users — mitigated by SRI and self-host fallback docs.
- **Caching of `scriba.js`** across versions — file is content-hashed in URL (e.g. `scriba-0.8.3.js` or `scriba.<hash>.js`).
- **Frame data still per-page** — JSON island is the only per-render JS-adjacent payload, but it's inert under CSP.
- **CSS still inline** — separate effort, called out as Wave 9 candidate.

---

## Success Criteria

- A single `scriba.js` artifact, content-hash-named, with published SRI hash.
- Default-rendered HTML loads cleanly under `Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self';`.
- No `onclick=` attribute remains anywhere in emitter output.
- Existing widgets continue to work under `--inline-runtime` until v1.0.
- Docs include a CSP deployment recipe.
