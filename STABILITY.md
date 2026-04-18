# Stability Policy

This document enumerates the contracts Scriba promises to consumers. Anything
listed in **Locked Contracts** is part of the stable surface: breaking it is a
MAJOR version bump under SemVer. Anything listed under **Not yet locked** is
free to change.

If you catch Scriba violating any of the locked contracts below, that is a
bug — please open an issue tagged `stability`.

## Semantic Versioning

Scriba follows [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html):

- **MAJOR** (`X.0.0`) — breaking changes to any locked contract.
- **MINOR** (`0.X.0`) — backward-compatible additions.
- **PATCH** (`0.0.X`) — backward-compatible bug fixes.

While Scriba is still in `0.x`, minor bumps **may** include breaking changes.
Every such change is explicitly called out in [`CHANGELOG.md`](CHANGELOG.md)
under a `BREAKING` heading. `1.0.0` will freeze the locked surface listed
below — from that point on, breaks require a MAJOR bump.

## Locked Contracts

### Public API surface

Every symbol listed in `scriba/__init__.py.__all__` is part of the public
API. The same symbols (minus the sanitize whitelist re-exports and the
version constants) are also listed in `scriba/core/__init__.py.__all__` so
consumers may import them from either level.

- **Adding** a symbol to `__all__` is a backward-compatible MINOR bump.
- **Removing** a symbol from `__all__` is a BREAKING MAJOR bump.
- Symbols not in `__all__` (including anything under `scriba._*` or
  `scriba.*.parser`, `scriba.*.engine`, etc.) are internal and may change
  without notice.

The full public set is pinned by `tests/unit/test_public_api.py`; that
test is the source of truth for the exported snapshot.

### `Document` shape

The `Document` dataclass fields are locked. As of v0.1.1 the fields are:

- `html: str`
- `required_css: frozenset[str]`
- `required_js: frozenset[str]`
- `versions: Mapping[str, int]`
- `block_data: Mapping[str, Any]` (added in 0.1.1)
- `required_assets: Mapping[str, Path]` (added in 0.1.1)

Rules:

- **Adding** a field with a default value is backward compatible.
- **Removing** or **renaming** a field is BREAKING.
- **Changing** a field's type is BREAKING.

The field set is pinned by `tests/unit/test_stability.py`.

### Asset namespace format

`Document.required_css`, `Document.required_js`, and the keys of
`Document.required_assets` all use the form:

```text
"<renderer>/<basename>"
```

Examples:

- `"tex/scriba-tex-content.css"`
- `"tex/scriba-tex-pygments-light.css"`
- `"animation/scriba-animation.css"`

Rules:

- `<renderer>` is the owning plugin's `Renderer.name` attribute (e.g.
  `"tex"`, `"diagram"`, `"animation"`). This is the same string used as
  the key in `Document.versions`.
- `<basename>` is a plain filename with no directory components.
- The separator is a literal `/` and never changes.
- Renaming a renderer, changing the separator, or renaming a basename is
  a BREAKING change.
- Adding a new asset (new key) is backward compatible.

The namespace was introduced in **v0.1.1** (when the old basename-only
format became ambiguous across plugins) and is locked from that release
onward. See `docs/spec/architecture.md` §Asset namespace format for the
full definition.

### Error code catalogue

Scriba error codes follow the `E1xxx` numbering scheme:

- `E1001`–`E1599` are reserved for the current error taxonomy.
- Codes are append-only within each range. Removing a code is BREAKING.
- Changing an error's **message text** is **not** breaking — messages are
  free to improve. Changing an error's **class** (e.g. moving a failure
  from `ValidationError` to `RendererError`) is BREAKING.
- Reserving a new code in the catalogue without raising it anywhere is
  backward compatible.
- `E1103` is kept as a deprecated alias for backward compatibility and
  may be removed no earlier than the next MAJOR release.

See `docs/spec/error-codes.md` for the live catalogue.

### Exception hierarchy

The following exception classes are locked:

- `ScribaError` (base)
- `RendererError`
- `WorkerError`
- `ScribaRuntimeError` (added in v0.1.1)
- `ValidationError`

All subclass `ScribaError`. Removing any of these, or re-parenting them,
is BREAKING. Adding new subclasses is backward compatible.

### `ALLOWED_TAGS` / `ALLOWED_ATTRS`

The sanitize whitelist exported as `scriba.ALLOWED_TAGS` and
`scriba.ALLOWED_ATTRS`:

- **Adding** a tag or an attribute is backward compatible.
- **Removing** a tag or an attribute is BREAKING (consumer sanitizers
  pinned to the old set would start stripping previously-allowed output).

Exact membership is pinned by `tests/sanitize/test_whitelist.py`; the
membership snapshot in that file is the source of truth. See
`docs/spec/architecture.md` §Sanitization policy for the rationale.

### CSS class names

Every class emitted by Scriba uses the `scriba-*` prefix. The prefix
itself is locked.

- Class **renames** are BREAKING (consumer stylesheets targeting the old
  name would silently stop working).
- Adding new classes is backward compatible.

See `docs/spec/animation-css.md` for the animation-plugin class taxonomy.

### SVG scene ID format

Animation scenes emit a root `<svg>` element with a deterministic `id`
of the form:

```text
scriba-<sha256[:10]>
```

Where the hash is `hashlib.sha256(<scene source>.encode()).hexdigest()`
truncated to 10 hex characters. The prefix, hash algorithm, and
truncation length are all locked. Changing any of them is BREAKING
because consumer stylesheets and JavaScript that target specific scene
IDs would break.

### `SCRIBA_VERSION` constant

`scriba.SCRIBA_VERSION` is a positive integer. It is bumped whenever the
`Document` shape changes in a way that should invalidate consumer
caches. Consumers may use it as part of their cache key.

- The type is locked as `int`.
- Backward: the value only increases.
- Adding fields with defaults to `Document` does **not** require a bump
  (old cached output remains valid); renaming or semantically changing
  an existing field does.

### `Renderer` protocol

Every renderer implementation must expose these attributes:

- `name: str` — stable plugin identifier (also the namespace prefix for
  the asset keys above).
- `version: int` — plugin version, bumped when HTML output shape
  changes.
- `priority: int` — overlap tie-breaker. The **locked default is 100**,
  enforced by the Pipeline when a renderer omits the attribute. Lower
  values win on overlap (added in v0.1.1).

Plus the methods `detect()`, `render_block()`, and `assets()`. See
`docs/spec/architecture.md` §Renderer protocol for the full signatures.

### Deprecation: `SubprocessWorker`

`SubprocessWorker` is a deprecated alias for
`PersistentSubprocessWorker`. It is lazy-loaded via PEP 562
`__getattr__` so that `import scriba` and `from scriba.core import
Pipeline` never emit a `DeprecationWarning` for consumers who do not
touch the legacy name. Reaching for the alias
(`from scriba import SubprocessWorker` or
`from scriba.core.workers import SubprocessWorker`) emits a
`DeprecationWarning` exactly once per call site. The alias is scheduled
for removal in **1.0.0**; consumers should migrate to
`PersistentSubprocessWorker`.

## Extension API (Locked)

### `register_primitive` / `get_primitive_registry`

Third-party primitive plugins use these two entry points from
`scriba.animation.primitives`:

- **`register_primitive(*type_names)`** — class decorator that adds a
  `PrimitiveBase` subclass to the built-in dispatch table under one or
  more type-name strings. The decorator signature is locked.
- **`get_primitive_registry()`** — returns a ``dict[str, type]`` snapshot
  of all registered primitives. The return type is locked.

Rules:

- These symbols remain in `scriba.animation.primitives.__all__` and are
  therefore part of the importable public surface.
- The **decorator signature** (`*type_names: str`) will not change before
  `1.0.0`.
- The **return type** of `get_primitive_registry` (`dict[str, type]`) will
  not change before `1.0.0`.
- The *internal* dispatch table (`_PRIMITIVE_REGISTRY`) is not locked and
  may be restructured without notice.


## Not yet locked (evolving)

These surfaces are explicitly **not** locked and may change without a
MAJOR bump during `0.x`:

- Animation `scene-ir.md` internal data model — intermediate
  representation used between the parser and the emitter.
- Starlark worker API — see `docs/spec/starlark-worker.md`. Planned to
  lock at `1.0.0`.
- Primitive internal state representation — the Python classes under
  `scriba.animation.primitives.*`. Only their emitted HTML/CSS/SVG
  output is locked; the Python shape is free to change.
- Anything under a module named `_*` or inside `scriba.*.parser`,
  `scriba.*.engine`, `scriba.*.emitter` that is not re-exported from the
  package root.

## Deprecation policy

When we deprecate a feature:

1. It emits `DeprecationWarning` on first use (or on every call, if the
   warning cost is negligible). Internal scriba-to-scriba use is
   silenced so end users do not see spurious warnings.
2. It remains functional for at least **one full minor release** after
   the deprecation lands.
3. Removal is explicitly documented in `CHANGELOG.md` under `BREAKING`.

## Reporting a contract violation

If you catch Scriba violating any of the contracts above, please open
an issue tagged `stability` with:

- The Scriba version you observed.
- A minimal reproduction (Python snippet or failing test).
- The exact field, symbol, or value you expected.

Contract violations are bugs and will be fixed in a PATCH release.
