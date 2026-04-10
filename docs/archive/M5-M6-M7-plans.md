# Implementation Plans: M5, M6, M7

## M5: Stringly-typed state system

**Recommendation: Won't-fix**

The parser already validates states at parse time (E1109 in `grammar.py` line 357), and `VALID_STATES` in `base.py` is a `frozenset` checked at runtime. The actual gap is IDE support for `.tex` authors, which is a tooling problem (LSP/editor plugin), not a language problem. Introducing a `StrEnum` in Python would add import overhead and a migration burden across every primitive that references state strings, but would not improve the `.tex` authoring experience at all since the DSL surface remains string-based.

Custom states via CSS custom properties (Option C) would require a theme/palette system, SVG style injection changes across all primitives, and spec updates -- significant scope for a speculative need. The fixed 8-state palette (`idle`, `current`, `done`, `dim`, `error`, `good`, `highlight`, `path`) covers standard algorithm visualization well.

**What would change the decision:** If a concrete use case requires >8 distinguishable visual states in a single animation, revisit with Option C scoped to `STATE_COLORS` extensibility via `\palette` command.

## M6: No diff/delta semantics

**Recommendation: Defer**

With `\foreach` (added for C1), the verbosity that motivated M6 is substantially reduced. An author can now write:

```tex
\foreach{i}{0..${prev}}{ \recolor{a.cell[${i}]}{state=dim} }
```

This is one line instead of N repeated `\recolor` commands. The remaining pain point -- "previous `current` auto-becomes `done`" -- is a convenience, not a blocker.

If pursued later, **Option C (implicit state transitions)** is the cleanest design: define a transition table (e.g., `current -> done -> dim`) applied automatically at each `\step` boundary. This would touch `scene.py` (`apply_frame` method, after clearing ephemerals) and require a new `\transitions` command in the grammar. Complexity: medium (~2 days). But it adds implicit behavior that makes animations harder to reason about, which conflicts with the DSL's explicit-is-better philosophy.

**What would change the decision:** User feedback showing that even with `\foreach`, step definitions remain >50% boilerplate recoloring. At that point, Option D (`\step[autodim=true]`) is the safest entry point -- explicit opt-in per step, no implicit global behavior.

## M7: SIGALRM Unix-only

**Recommendation: Defer**

The current code (`starlark_worker.py` lines 308-328) uses `signal.SIGALRM` on Unix with a `hasattr` guard, falling back to step-counter-only protection on Windows. The step counter (`sys.settrace` with 10^8 limit) is the primary protection; `SIGALRM` is a secondary wall-clock backstop.

Scriba is a build-time tool targeting developers on Unix/macOS. CI environments (GitHub Actions, GitLab CI) run Linux. Windows usage is theoretical.

If pursued, **Option B** is correct: keep `signal.alarm` on Unix, add `threading.Timer` on non-Unix. The timer thread would call `_thread.interrupt_main()` after `_WALL_CLOCK_SECONDS`. Changes limited to `starlark_worker.py` `_evaluate()` function (~15 lines). Complexity: low (~2 hours), but adds threading complexity to a subprocess that is otherwise single-threaded.

**What would change the decision:** A concrete Windows user or a CI environment running on Windows containers. Until then, the step counter is sufficient protection.
