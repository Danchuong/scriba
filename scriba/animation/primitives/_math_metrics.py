"""Exact inline-math widths from KaTeX's own font metrics.

Label pills and their per-line ``<foreignObject>`` boxes embed KaTeX
output, but their widths were estimated by stripping ``$``/commands and
multiplying char count ×1.15×0.62em — p50 |err| 43% against the browser,
and pure-command fragments (``$\\to$``, ``$\\alpha$``) measured **0 px**
(investigations/folabel-measure.md §1).

This module measures the same way KaTeX lays out: a linear advance-sum
over the glyph tables baked from the vendored ``katex.min.js`` by
``scripts/build_katex_metrics.py``:

    px = Σ(advance_em × script_scale) × 1.21 × font_px

with three corrections the bench proved load-bearing (§2, §4):

- **italic correction** folded into every Math-Italic advance (KaTeX bakes
  it into the glyph box; capitals under-measure 10–19% without it);
- **script scaling**: sup/sub run at 0.7×, share one horizontal slot
  (base + max(sup, sub) + scriptspace);
- **TeX math spacing** between atom classes (bin 4mu, rel 5mu, op/punct
  3mu; unary +/− demoted to ord).

Bench vs Chromium rendering of the shipped page, N=67 fragments: p50
|err| 0.06%, p95 0.66%. Real label-math corpus is 100% linear (§3);
2-D material (``\\frac``, ``\\sqrt``…) and unknown commands take
``is_linear_math() == False`` and fall back to the old over-estimating
heuristic — safe: over-measure only pads.

Stdlib-only at runtime; the JSON table ships in the wheel next to KaTeX
itself. If the table is missing, everything degrades to the heuristic.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib.resources import files

from scriba.animation.primitives._text_render import estimate_text_width

__all__ = ["is_linear_math", "measure_inline_math"]

_KATEX_BASE_EM = 1.21  # .katex { font: normal 1.21em ... }
_SCRIPT_SCALE = 0.7  # scriptstyle multiplier for ^ / _
_MU = 1.0 / 18.0  # 1mu in em
_SCRIPTSPACE = 0.05  # em appended after a scripted atom

# Fragments containing any of these are 2-D (or row-structured) — the
# linear model cannot see their stacking, so they take the heuristic.
_NONLINEAR_RE = re.compile(
    r"\\(?:frac|dfrac|tfrac|cfrac|sqrt|binom|over(?![a-zA-Z])|atop|begin|"
    r"substack|overbrace|underbrace|overline|underline|stackrel|not(?![a-zA-Z]))"
    r"|\\\\"
)

_CMD_RE = re.compile(r"\\([a-zA-Z]+|.)")

# command -> (codepoint, font, atom class). "op" font = inline big operator
# looked up in Size1-Regular. Coverage = every command in the 620-file
# label-math census (folabel-measure.md §3) plus its immediate family.
_CMD: dict[str, tuple[int, str, str]] = {
    "to": (0x2192, "Main-Regular", "rel"),
    "rightarrow": (0x2192, "Main-Regular", "rel"),
    "gets": (0x2190, "Main-Regular", "rel"),
    "leftarrow": (0x2190, "Main-Regular", "rel"),
    "mapsto": (0x21A6, "Main-Regular", "rel"),
    "leftrightarrow": (0x2194, "Main-Regular", "rel"),
    "Rightarrow": (0x21D2, "Main-Regular", "rel"),
    "times": (0xD7, "Main-Regular", "bin"),
    "cdot": (0x22C5, "Main-Regular", "bin"),
    "div": (0xF7, "Main-Regular", "bin"),
    "pm": (0xB1, "Main-Regular", "bin"),
    "mp": (0x2213, "Main-Regular", "bin"),
    "oplus": (0x2295, "Main-Regular", "bin"),
    "cup": (0x222A, "Main-Regular", "bin"),
    "cap": (0x2229, "Main-Regular", "bin"),
    "setminus": (0x2216, "Main-Regular", "bin"),
    # U+2260 has no Main entry; KaTeX composes '=' + \not overlay (same advance)
    "ne": (0x3D, "Main-Regular", "rel"),
    "neq": (0x3D, "Main-Regular", "rel"),
    "le": (0x2264, "Main-Regular", "rel"),
    "leq": (0x2264, "Main-Regular", "rel"),
    "ge": (0x2265, "Main-Regular", "rel"),
    "geq": (0x2265, "Main-Regular", "rel"),
    "ll": (0x226A, "Main-Regular", "rel"),
    "gg": (0x226B, "Main-Regular", "rel"),
    "in": (0x2208, "Main-Regular", "rel"),
    "notin": (0x2209, "AMS-Regular", "rel"),
    "ni": (0x220B, "Main-Regular", "rel"),
    "approx": (0x2248, "Main-Regular", "rel"),
    "equiv": (0x2261, "Main-Regular", "rel"),
    "sim": (0x223C, "Main-Regular", "rel"),
    "subset": (0x2282, "Main-Regular", "rel"),
    "supset": (0x2283, "Main-Regular", "rel"),
    "subseteq": (0x2286, "Main-Regular", "rel"),
    "supseteq": (0x2287, "Main-Regular", "rel"),
    "mid": (0x2223, "Main-Regular", "rel"),
    "parallel": (0x2225, "Main-Regular", "rel"),
    "perp": (0x22A5, "Main-Regular", "rel"),
    "infty": (0x221E, "Main-Regular", "ord"),
    "partial": (0x2202, "Math-Italic", "ord"),
    "emptyset": (0x2205, "AMS-Regular", "ord"),
    "varnothing": (0x2205, "AMS-Regular", "ord"),
    "forall": (0x2200, "Main-Regular", "ord"),
    "exists": (0x2203, "Main-Regular", "ord"),
    "neg": (0xAC, "Main-Regular", "ord"),
    "lnot": (0xAC, "Main-Regular", "ord"),
    "land": (0x2227, "Main-Regular", "bin"),
    "lor": (0x2228, "Main-Regular", "bin"),
    "wedge": (0x2227, "Main-Regular", "bin"),
    "vee": (0x2228, "Main-Regular", "bin"),
    "star": (0x22C6, "Main-Regular", "bin"),
    "circ": (0x2218, "Main-Regular", "bin"),
    "bullet": (0x2219, "Main-Regular", "bin"),
    "nabla": (0x2207, "Main-Regular", "ord"),
    "ell": (0x2113, "Math-Italic", "ord"),
    "hbar": (0x210F, "Main-Regular", "ord"),
    "prime": (0x2032, "Main-Regular", "ord"),
    "angle": (0x2220, "Main-Regular", "ord"),
    "triangle": (0x25B3, "Main-Regular", "ord"),
    "lfloor": (0x230A, "Main-Regular", "open"),
    "rfloor": (0x230B, "Main-Regular", "close"),
    "lceil": (0x2308, "Main-Regular", "open"),
    "rceil": (0x2309, "Main-Regular", "close"),
    "langle": (0x27E8, "Main-Regular", "open"),
    "rangle": (0x27E9, "Main-Regular", "close"),
    "sum": (0x2211, "op", "op"),
    "prod": (0x220F, "op", "op"),
    "int": (0x222B, "op", "op"),
    "bigcup": (0x22C3, "op", "op"),
    "bigcap": (0x22C2, "op", "op"),
    "alpha": (0x3B1, "Math-Italic", "ord"),
    "beta": (0x3B2, "Math-Italic", "ord"),
    "gamma": (0x3B3, "Math-Italic", "ord"),
    "delta": (0x3B4, "Math-Italic", "ord"),
    "epsilon": (0x3F5, "Math-Italic", "ord"),
    "varepsilon": (0x3B5, "Math-Italic", "ord"),
    "zeta": (0x3B6, "Math-Italic", "ord"),
    "eta": (0x3B7, "Math-Italic", "ord"),
    "theta": (0x3B8, "Math-Italic", "ord"),
    "vartheta": (0x3D1, "Math-Italic", "ord"),
    "iota": (0x3B9, "Math-Italic", "ord"),
    "kappa": (0x3BA, "Math-Italic", "ord"),
    "lambda": (0x3BB, "Math-Italic", "ord"),
    "mu": (0x3BC, "Math-Italic", "ord"),
    "nu": (0x3BD, "Math-Italic", "ord"),
    "xi": (0x3BE, "Math-Italic", "ord"),
    "pi": (0x3C0, "Math-Italic", "ord"),
    "varpi": (0x3D6, "Math-Italic", "ord"),
    "rho": (0x3C1, "Math-Italic", "ord"),
    "sigma": (0x3C3, "Math-Italic", "ord"),
    "varsigma": (0x3C2, "Math-Italic", "ord"),
    "tau": (0x3C4, "Math-Italic", "ord"),
    "upsilon": (0x3C5, "Math-Italic", "ord"),
    "phi": (0x3D5, "Math-Italic", "ord"),
    "varphi": (0x3C6, "Math-Italic", "ord"),
    "chi": (0x3C7, "Math-Italic", "ord"),
    "psi": (0x3C8, "Math-Italic", "ord"),
    "omega": (0x3C9, "Math-Italic", "ord"),
    "Gamma": (0x393, "Main-Regular", "ord"),
    "Delta": (0x394, "Main-Regular", "ord"),
    "Theta": (0x398, "Main-Regular", "ord"),
    "Lambda": (0x39B, "Main-Regular", "ord"),
    "Xi": (0x39E, "Main-Regular", "ord"),
    "Pi": (0x3A0, "Main-Regular", "ord"),
    "Sigma": (0x3A3, "Main-Regular", "ord"),
    "Upsilon": (0x3A5, "Main-Regular", "ord"),
    "Phi": (0x3A6, "Main-Regular", "ord"),
    "Psi": (0x3A8, "Main-Regular", "ord"),
    "Omega": (0x3A9, "Main-Regular", "ord"),
}

_DOTS = {"ldots", "dots", "cdots", "dotsc", "dotsb"}
# \log-family: upright Main-Regular letter runs, atom class op
_OPNAMES = {
    "log", "ln", "lg", "exp", "min", "max", "gcd", "lcm", "sin", "cos",
    "tan", "cot", "sec", "csc", "arg", "det", "dim", "deg", "mod", "bmod",
    "hom", "ker", "inf", "sup", "lim",
}
# zero-glyph structural/formatting commands the linear model can ignore
_IGNORABLE = {"left", "right", "big", "Big", "bigl", "bigr", "Bigl", "Bigr",
              "mathrm", "mathbf", "mathit", "text", "textrm", "displaystyle",
              "textstyle", "limits", "nolimits"}
_SPACING = {",": 3 * _MU, " ": 4 * _MU, ";": 5 * _MU, ":": 4 * _MU,
            "quad": 1.0, "qquad": 2.0, "!": -3 * _MU}


@lru_cache(maxsize=1)
def _tables() -> dict[str, dict[int, tuple[float, float]]] | None:
    """Baked (width_em, italic_em) tables, or None -> heuristic fallback."""
    try:
        raw = (
            files("scriba.tex") / "vendor" / "katex" / "katex_advances.json"
        ).read_text("utf-8")
        data = json.loads(raw)
        return {
            font: {int(cp): (float(v[0]), float(v[1])) for cp, v in glyphs.items()}
            for font, glyphs in data["metrics"].items()
        }
    except (FileNotFoundError, KeyError, ValueError, OSError):
        return None


def _known_commands() -> set[str]:
    return set(_CMD) | _DOTS | _OPNAMES | _IGNORABLE | set(_SPACING)


def is_linear_math(frag: str) -> bool:
    """True when *frag* is a horizontal run the advance-sum models exactly.

    2-D structures and commands outside the map return False; callers fall
    back to the heuristic (over-estimates — safe, only pads).
    """
    if _NONLINEAR_RE.search(frag):
        return False
    known = _known_commands()
    for m in _CMD_RE.finditer(frag):
        if m.group(1) not in known:
            return False
    return True


def _adv(tables: dict, font: str, cp: int) -> float | None:
    e = tables.get(font, {}).get(cp)
    if e is None:
        return None
    width, italic = e
    # KaTeX bakes each Math-Italic glyph's italic correction into its box
    return width + italic if font == "Math-Italic" else width


def _char_atom(tables: dict, ch: str, scale: float) -> tuple[float, str]:
    o = ord(ch)
    if ch.isdigit():
        return ((_adv(tables, "Main-Regular", o) or 0.5) * scale, "ord")
    if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
        w = _adv(tables, "Math-Italic", o)
        if w is None:
            w = _adv(tables, "Main-Regular", o) or 0.5
        return (w * scale, "ord")
    if ch in "([{":
        return ((_adv(tables, "Main-Regular", o) or 0.39) * scale, "open")
    if ch in ")]}":
        return ((_adv(tables, "Main-Regular", o) or 0.39) * scale, "close")
    if ch in ",;":
        return ((_adv(tables, "Main-Regular", o) or 0.28) * scale, "punct")
    if ch == "+":
        return ((_adv(tables, "Main-Regular", o) or 0.78) * scale, "bin")
    if ch == "-":
        # KaTeX renders '-' as minus U+2212
        return ((_adv(tables, "Main-Regular", 0x2212) or 0.78) * scale, "bin")
    if ch in "=<>":
        return ((_adv(tables, "Main-Regular", o) or 0.78) * scale, "rel")
    if ch == "*":
        return ((_adv(tables, "Main-Regular", 0x2217) or 0.5) * scale, "bin")
    if ch == "!":
        return ((_adv(tables, "Main-Regular", o) or 0.28) * scale, "close")
    w = _adv(tables, "Main-Regular", o)
    return ((w if w is not None else 0.5) * scale, "ord")


def _parse(tables: dict, tex: str, scale: float) -> list[list[float | str]]:
    """Flat base-level atoms [emwidth, class(, script_slot_em)].

    Scripts fold into the preceding atom's slot: sup and sub share the
    horizontal column, so the slot is max(sup, sub)."""
    atoms: list[list] = []
    i, n = 0, len(tex)
    while i < n:
        c = tex[i]
        if c.isspace():
            i += 1
            continue
        if c == "{":
            depth, j = 1, i + 1
            while j < n and depth:
                if tex[j] == "{":
                    depth += 1
                elif tex[j] == "}":
                    depth -= 1
                j += 1
            atoms.extend([list(a) for a in _parse(tables, tex[i + 1 : j - 1], scale)])
            i = j
            continue
        if c in "^_":
            i += 1
            if i < n and tex[i] == "{":
                depth, j = 1, i + 1
                while j < n and depth:
                    if tex[j] == "{":
                        depth += 1
                    elif tex[j] == "}":
                        depth -= 1
                    j += 1
                sarg, i = tex[i + 1 : j - 1], j
            elif i < n and tex[i] == "\\":
                m = _CMD_RE.match(tex, i)
                sarg, i = tex[i : m.end()], m.end()
            else:
                sarg, i = (tex[i] if i < n else ""), i + 1
            sw = sum(a[0] for a in _parse(tables, sarg, scale * _SCRIPT_SCALE))
            if atoms:
                la = atoms[-1]
                if len(la) == 2:
                    la.append(sw)
                else:
                    la[2] = max(la[2], sw)
            continue
        if c == "\\":
            m = _CMD_RE.match(tex, i)
            name = m.group(1)
            i = m.end()
            if name in _SPACING:
                atoms.append([_SPACING[name] * scale, "space"])
                continue
            if name in _DOTS:
                w = 3 * (_adv(tables, "Main-Regular", 0x2E) or 0.28)
                atoms.append([w * scale, "ord"])
                continue
            if name in _OPNAMES:
                w = sum((_adv(tables, "Main-Regular", ord(ch)) or 0.5) for ch in name)
                atoms.append([w * scale, "op"])
                continue
            if name in _CMD:
                cp, font, cls = _CMD[name]
                if font == "op":
                    w = None
                    for fnt in ("Size1-Regular", "Main-Regular", "AMS-Regular"):
                        w = _adv(tables, fnt, cp)
                        if w:
                            break
                    w = w or 1.0
                else:
                    w = (
                        _adv(tables, font, cp)
                        or _adv(tables, "Main-Regular", cp)
                        or _adv(tables, "AMS-Regular", cp)
                        or 0.6
                    )
                atoms.append([w * scale, cls])
                continue
            # _IGNORABLE and anything else: zero width (guard already sent
            # unknown-command fragments to the heuristic)
            continue
        w, cls = _char_atom(tables, c, scale)
        atoms.append([w, cls])
        i += 1
    return atoms


def _mathspace(a: str, b: str) -> float:
    if a == "open" or b == "close":
        return 0.0
    if a == "op" or b == "op":
        return 3 * _MU
    if a == "bin" or b == "bin":
        return 4 * _MU
    if a == "rel" or b == "rel":
        return 5 * _MU
    if a == "punct":
        return 3 * _MU
    return 0.0


def _em_width(tables: dict, frag: str) -> float:
    atoms = _parse(tables, frag, 1.0)
    # unary +/-: a bin with no left operand demotes to ord (TeX rule)
    prev_cls: str | None = None
    for a in atoms:
        cls = a[1]
        if cls == "bin" and prev_cls in (None, "open", "bin", "rel", "punct", "op"):
            a[1] = "ord"
        if cls != "space":
            prev_cls = a[1]
    total = 0.0
    prev = None
    for a in atoms:
        w, cls = a[0], a[1]
        if len(a) == 3:
            w = w + a[2] + _SCRIPTSPACE
        if prev is not None and cls != "space" and prev != "space":
            total += _mathspace(prev, cls)
        total += w
        prev = cls
    return total


def _heuristic_px(frag: str, font_px: int) -> float:
    # the pre-engine estimate, floored so pure-command fragments (\to,
    # \alpha) can never measure zero again
    from scriba.animation.primitives._svg_helpers import _label_width_text

    est = estimate_text_width(_label_width_text(f"${frag}$"), font_px)
    return max(float(est), _KATEX_BASE_EM * font_px * 0.6)


@lru_cache(maxsize=4096)
def measure_inline_math(frag: str, font_px: int) -> float:
    """Rendered px width of inline ``$frag$`` (delimiters not included).

    Tier-B advance-sum (p50 0.06% / p95 0.66% vs Chromium) when the
    fragment is linear and the tables are vendored; heuristic otherwise.
    """
    tables = _tables()
    if tables is None or not is_linear_math(frag):
        return _heuristic_px(frag, font_px)
    return _em_width(tables, frag) * _KATEX_BASE_EM * font_px
