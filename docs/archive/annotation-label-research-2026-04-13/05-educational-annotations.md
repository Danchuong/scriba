# 05 — Educational Annotation Patterns

## 7 Design Patterns from Educational Tools

### Pattern 1: Coordinated Highlight via Shared Keys (Red Blob Games)

`data-key` attributes shared between prose text and diagram elements.
Hover either one → both highlight. Association maintained through interaction,
not spatial proximity.

- Bidirectional: hover text highlights arrow AND hover arrow highlights text
- Labels fully visible at all times
- ~10 lines of JavaScript

### Pattern 2: Status Panel + Pseudocode Sync (VisuAlgo)

Three synchronized panels:
1. Visualization canvas (color-coded nodes/edges)
2. Pseudocode panel (current line highlighted)
3. Status panel (natural language description)

Arrow-label association sidestepped: no labels on arrows. Color encodes state,
status panel provides text explanation. Users correlate through temporal sync.

### Pattern 3: Sequential Reveal with Auto-Pause (CS Education Research)

- Animations auto-pause after logically related steps
- Only 1-2 annotations visible at a time
- Previous annotations fade to dimmed context
- "Three, maximum five" visible annotations at full emphasis

Research finding: "discrete segment presentation" is critical for learning.

### Pattern 4: Leader Lines with Spatial Encoding (Annotation Research 2025)

Practitioner interviews (arxiv 2604.07691):
- Direct labeling first (adjacent to data element)
- Leader lines second (when adjacency causes overlap)
- Keyed legend last resort
- Color matching must pair with non-color redundancy (proximity, connector)
- Annotation budget: 3-5 visible at full emphasis

### Pattern 5: Edge Label Placement Strategies

Three complementary techniques:
1. Label rotation along edge path (geometric alignment)
2. Region positioning (above/below/left/right/over)
3. Association positioning (source/center/target along edge)

### Pattern 6: Split-Screen Code-Visual Sync (Algorithm Visualizer)

Distribute annotations across spatial zones rather than overlaying on canvas:
- Code panel on one side
- Visualization on the other
- Variables/state in sub-panels

### Pattern 7: LabeledArrow with Positional Control (Manim)

- Label placed directly on arrow at configurable position (0.0-1.0)
- VGroup containers group arrow+label for synchronized transforms
- Sequential `Play()` reveals one pair at a time
- Previous pairs remain visible but visually subordinate

## Critical Don'ts

- Never bury essential context behind hover-only interaction
- Never rely on color alone for association (accessibility)
- Never allow leader lines to cross each other or cross arrows
- Never exceed 5 simultaneously visible annotations without spatial separation

## Synthesis for Scriba

### Static Mode
1. Sequential reveal (1-2 arrows per step, fade previous)
2. Label rotation along edge
3. Color matching with redundant encoding (color + position on curve)
4. Budget: 3-5 annotations at full opacity per frame

### Interactive Mode
1. Shared-key coordinated highlighting (hover highlights arrow+label pair)
2. Narration panel provides full text context
3. All labels visible, hover strengthens association
4. Toggle annotation layer visibility

## Sources

- Red Blob Games: Highlighting diagrams and text together
- VisuAlgo (visualgo.net)
- Algorithm Animations for Teaching and Learning (ERIC)
- Designing Annotations in Visualization (arxiv 2604.07691)
- Manim LabeledArrow documentation
- Khan Academy Algorithms course
- USF Data Structure Visualization
