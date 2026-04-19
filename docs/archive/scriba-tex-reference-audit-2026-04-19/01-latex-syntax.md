# §1–2 LaTeX Syntax Audit

Audited against:
- `scriba/tex/renderer.py`
- `scriba/tex/parser/environments.py`
- `scriba/tex/parser/math.py`
- `scriba/tex/parser/text_commands.py`
- `scriba/core/text_utils.py`
- `scriba/tex/parser/lists.py`
- `scriba/tex/parser/tables.py`
- `scriba/tex/parser/dashes_quotes.py`
- `scriba/tex/parser/code_blocks.py`
- `scriba/tex/parser/images.py`
- `scriba/tex/validate.py`

---

## Findings

### [HIGH] Triple-dollar `$$$...$$$` display math is supported but undocumented (line 53)

**What doc says:** Only `$...$` (inline) and `$$...$$` (display) are supported. `\[...\]` and `\(...\)` are explicitly NOT supported.

**What code does:** `math.py:75–79` matches `$$$...$$$` first as a display-math alias (Polygon-style). This is real, rendered behavior — it goes through the same KaTeX display path as `$$...$$`.

**Recommendation:** Add `$$$...$$$` row to §2.3 table as display-mode alias. Low risk of breakage but an AI agent generating `$$$...$$$` would currently get correct output without knowing it's valid.

---

### [HIGH] Starred section variants: claim "not supported" is partially misleading (line 36)

**What doc says:** "No starred variants (`\section*{}`)."

**What code does:** `environments.py:68–70` uses simple regexes `\\section\{...\}`, `\\subsection\{...\}`, `\\subsubsection\{...\}`. A `\section*{Title}` will NOT match these regexes — the `*` causes the pattern to fail silently and the literal `\section*{Title}` leaks as text into the output.

**Recommendation:** The claim is correct but the consequence is important: starred variants are not just "unsupported" — they pass through as raw literal text (not silently ignored). Doc should say "do not use starred variants; they appear verbatim in output."

---

### [CRITICAL] `equation`, `align`, `align*` environments accepted by validator but behavior undocumented (line 54, 108)

**What doc says:** §2.3 says math environments "must be inside `$` or `$$` delimiters." §2.9 says nothing about `equation`/`align`.

**What code does:** `validate.py:14–39` lists `equation`, `align`, `align*`, `array`, `matrix`, `pmatrix`, `bmatrix`, `vmatrix`, `Vmatrix`, `cases` in `KNOWN_ENVIRONMENTS` — these pass validation without error. However, `renderer.py`'s pipeline has no dedicated handler for them. `strip_validation_environments` (`environments.py:77–113`) only strips: `verbatim`, `quote`, `quotation`, `figure`, `table`, `description`, `minipage`. The math environments are NOT in that strip list and NOT handled as block math.

**Net effect:** `\begin{equation}...\end{equation}` passes the validator, is not stripped, and is not rendered as math — the `\begin{equation}` and `\end{equation}` tags leak as literal escaped text into the HTML output. An AI agent following the doc will use `$$...$$` correctly; an agent probing the validator will think these environments are safe to use and get broken output.

**Recommendation:** Either (a) add these environments to `_VALIDATION_ONLY_ENVS` so their delimiters are stripped (content then needs to be wrapped in `$$` by the author), or (b) add a dedicated rendering pass. Until fixed, §2.3 must explicitly warn: "`equation`, `align`, `align*` pass validation but their `\begin`/`\end` tags appear verbatim — do not use them as top-level environments."

---

### [HIGH] Undocumented legacy aliases `\bf`, `\it`, `\tt` are supported (line 38–46)

**What doc says:** §2.2 lists `\textbf`, `\textit`/`\emph`, `\underline`, `\texttt`, `\sout`, `\textsc`. No mention of legacy aliases.

**What code does:** `core/text_utils.py:31–33` adds `\bf`, `\it`, `\tt` as aliases producing the same HTML as `\textbf`, `\textit`, `\texttt`.

**Recommendation:** Add a note to §2.2: "Legacy Polygon-style aliases `\bf`, `\it`, `\tt` are also accepted."

---

### [MED] Size commands (`\large`, `\small`, `\tiny`, etc.) are implemented but absent from §2 (line 38–46)

**What doc says:** §2.2 only covers the six text-style commands. No mention of size commands.

**What code does:** `text_commands.py:24–34` defines nine size commands: `\scriptsize`, `\normalsize`, `\LARGE`, `\Large`, `\large`, `\Huge`, `\huge`, `\small`, `\tiny`. Both brace form `\large{text}` and switch form `\large text` are supported (`text_commands.py:37–73`).

**Recommendation:** Add a §2.2a (or extend §2.2) documenting size commands.

---

### [MED] Smart-quote syntax undocumented (line 96–104)

**What doc says:** §2.8 lists `---`, `--`, `\\`, `~` as typography features. No mention of smart quotes.

**What code does:** `dashes_quotes.py:23–24` transforms ``` ``...'' ``` → curly double quotes and `` `...' `` → curly single quotes.

**Recommendation:** Add to §2.8: "`` ``text'' `` → curly double quotes; `` `text' `` → curly single quotes."

---

### [MED] `\footnote` listed as unsupported, but several environments are validator-only (line 108)

**What doc says:** §2.9 lists `\footnote` as NOT supported.

**What code does:** `validate.py:14–39` accepts `verbatim`, `quote`, `quotation`, `figure`, `table`, `description`, `minipage` in `KNOWN_ENVIRONMENTS`. Their delimiters are stripped by `strip_validation_environments` but their content passes through. This means `\begin{quote}...\end{quote}` renders the content without the block-quote wrapper — it is not an error, not a rendered block quote, just inline text.

**Recommendation:** §2.9 should explicitly note which environments are "validator-accepted but content-passthrough" so authors know not to rely on them for structural rendering.

---

### [LOW] `\includegraphics` options: only `width`, `height`, `scale` parsed (line 92–94)

**What doc says:** §2.7 shows `[width=8cm]` as the only example option.

**What code does:** `images.py:47–75` supports `scale`, `width`, and `height` with units `cm`, `mm`, `in`, `pt`, `px`. Other options (e.g., `keepaspectratio`, `angle`) are silently ignored.

**Recommendation:** Expand §2.7 to document all recognized option keys and supported units.

---

### [LOW] `\cline` described but not `\hline` (line 87)

**What doc says:** §2.6 mentions `\multicolumn`, `\multirow`, and `\cline{n-m}` but not `\hline`.

**What code does:** `tables.py:138–142` explicitly handles `\hline` for top/bottom borders. It is a first-class feature.

**Recommendation:** Add `\hline` to the §2.6 table features list.

---

## Coverage Gaps

Commands/features supported by code but missing from §1–2 of the doc:

- `$$$...$$$` triple-dollar display math alias (`math.py:75`)
- `\bf`, `\it`, `\tt` legacy aliases (`core/text_utils.py:31–33`)
- Nine size commands: `\tiny` `\small` `\normalsize` `\large` `\Large` `\LARGE` `\huge` `\Huge` `\scriptsize` (`text_commands.py:24–34`)
- Smart-quote syntax: ` ``...'' ` and `` `...' `` (`dashes_quotes.py:23–24`)
- `\hline` in tables (`tables.py:138–142`)
- `scale=`, `height=` options for `\includegraphics` (`images.py:47–75`)
- Validator-accepted passthrough environments: `verbatim`, `quote`, `quotation`, `figure`, `table`, `description`, `minipage` (`validate.py:14–39`, `environments.py:77–87`)

---

## Verdict

**Overall accuracy: 6/10**

The file-structure claim (§1) is correct — no `\documentclass`, no `\usepackage`, body-only content. The core documented commands (`\section` family, `\textbf`/`\textit`/`\emph`/`\texttt`/`\underline`/`\sout`/`\textsc`, `$...$`/`$$...$$`, `itemize`/`enumerate`, `lstlisting`, `tabular`, `href`/`url`/`includegraphics`, `center`, `epigraph`, dash/tilde/linebreak escapes) all match their implementations.

The two critical gaps are: (1) the `equation`/`align`/`align*` validator-pass-but-render-broken hazard (§2.3/§2.9), which will cause an AI agent that probes the validator to generate silently broken output; and (2) the undocumented size commands and legacy aliases, which represent significant usable functionality not exposed to agents. The smart-quote omission and `\hline` gap are lower stakes but add up to a noticeably incomplete picture.
