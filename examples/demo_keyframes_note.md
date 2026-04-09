# @keyframes Extension -- Wiring Status

## Current State

The `@keyframes` extension (`scriba/animation/extensions/keyframes.py`) provides:

- **`KEYFRAME_PRESETS`** -- five named CSS animation templates: `rotate`, `pulse`, `orbit`, `fade-loop`, `trail`
- **`generate_keyframe_styles(scene_id, requested_presets)`** -- generates a `<style>` block with scene-scoped `@keyframes` rules
- **`get_animation_class(scene_id, preset_name)`** -- returns the utility CSS class name
- **`UTILITY_CSS`** -- matching `.scriba-anim-*` utility classes

## What Is Missing

The keyframes extension is **not wired into the rendering pipeline**:

1. `renderer.py` imports `generate_keyframe_styles` but never calls it.
2. The animation `.tex` grammar (`parser/grammar.py`, `parser/lexer.py`) has no command to attach a keyframe animation to a shape or element. There is no `\animate`, `\keyframe`, or similar command.
3. The emitter (`emitter.py`) does not inject the keyframe `<style>` block or add animation classes to SVG elements.

## What Is Needed to Wire It

1. **Add a new `.tex` command** to the lexer and grammar, e.g.:
   ```
   \animate{shape.selector}{preset=rotate, duration=2s}
   ```
2. **Store animation metadata** in `FrameCommand` or a new AST node so the scene state machine can track which elements have animations.
3. **Emit the CSS** in `renderer.py`'s `render_block()` by calling `generate_keyframe_styles()` with the set of presets used, and including the output in `RenderArtifact.html`.
4. **Apply CSS classes** in the emitter when rendering SVG elements that have an active animation, adding `class="scriba-anim-{preset}"` and `style="--scriba-anim-name: {scene_id}-{preset}"`.
5. **Include `UTILITY_CSS`** either in `scriba-animation.css` or emitted inline alongside the keyframes block.

## Verification (Unit Test Level)

The extension functions work correctly in isolation. See `tests/unit/test_keyframes.py` for existing coverage of `generate_keyframe_styles`.
