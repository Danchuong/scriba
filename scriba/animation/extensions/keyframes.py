"""CSS @keyframes preset system — named animation slots scoped per scene.

Authors reference preset names (``rotate``, ``pulse``, …) on SVG elements.
The emitter calls :func:`generate_keyframe_styles` to inline only the
``@keyframes`` rules actually used, prefixed with the scene id to prevent
cross-animation leakage.
"""

from __future__ import annotations

import html

KEYFRAME_PRESETS: dict[str, str] = {
    "rotate": """
@keyframes {name} {{
  from {{ transform: rotate(0deg); }}
  to {{ transform: rotate(360deg); }}
}}""",
    "pulse": """
@keyframes {name} {{
  0%, 100% {{ transform: scale(1); }}
  50% {{ transform: scale(1.15); }}
}}""",
    "orbit": """
@keyframes {name} {{
  from {{ transform: rotate(0deg) translateX(10px) rotate(0deg); }}
  to {{ transform: rotate(360deg) translateX(10px) rotate(-360deg); }}
}}""",
    "fade-loop": """
@keyframes {name} {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.3; }}
}}""",
    "trail": """
@keyframes {name} {{
  from {{ stroke-dashoffset: 100; }}
  to {{ stroke-dashoffset: 0; }}
}}""",
}


def _sanitize_scene_id(scene_id: str) -> str:
    """Strip characters unsafe for CSS identifiers."""
    return html.escape(scene_id, quote=True)


def generate_keyframe_styles(
    scene_id: str,
    requested_presets: set[str],
) -> str:
    """Generate scoped ``@keyframes`` CSS for the requested presets.

    Each keyframe name is prefixed with *scene_id* so that animations from
    different scenes on the same page never collide.

    Parameters
    ----------
    scene_id:
        Unique identifier for the enclosing scene.
    requested_presets:
        Set of preset names to emit (e.g. ``{"rotate", "pulse"}``).

    Returns
    -------
    str
        A ``<style>`` block containing the ``@keyframes`` rules, or an
        empty string when no valid presets are requested.
    """
    if not requested_presets:
        return ""

    rules: list[str] = []
    for preset_name in sorted(requested_presets):
        template = KEYFRAME_PRESETS.get(preset_name)
        if template is None:
            continue
        scoped_name = f"{scene_id}-{preset_name}"
        rules.append(template.format(name=scoped_name))

    if not rules:
        return ""

    return f'<style>{"".join(rules)}\n</style>'


def get_animation_class(scene_id: str, preset_name: str) -> str:
    """Return the CSS class that applies the keyframe animation.

    The class uses a CSS custom property ``--scriba-anim-name`` so that
    the utility rule can reference the scene-scoped ``@keyframes`` name.
    """
    return f"scriba-anim-{preset_name}"


# Utility CSS classes — intended for inclusion in scriba-animation.css or
# emitted inline alongside ``generate_keyframe_styles`` output.
UTILITY_CSS = """\
/* Keyframe animation utility classes — set --scriba-anim-name per element */
.scriba-anim-rotate { animation: var(--scriba-anim-name) 2s linear infinite; }
.scriba-anim-pulse { animation: var(--scriba-anim-name) 1s ease-in-out infinite; }
.scriba-anim-orbit { animation: var(--scriba-anim-name) 3s linear infinite; }
.scriba-anim-fade-loop { animation: var(--scriba-anim-name) 2s ease-in-out infinite; }
.scriba-anim-trail { animation: var(--scriba-anim-name) 1.5s linear infinite; }

/* Respect user motion preferences */
@media (prefers-reduced-motion: reduce) {
  .scriba-anim-rotate,
  .scriba-anim-pulse,
  .scriba-anim-orbit,
  .scriba-anim-fade-loop,
  .scriba-anim-trail {
    animation: none !important;
  }
}
"""
