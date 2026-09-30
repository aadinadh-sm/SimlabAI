# SIMLAB AI: Whiteboard Sketch Recognition Engine

## Recognition Pipeline
```
Pointer Event Stream
       ↓
Stroke Polyline Collection
       ↓
Geometric Bounding & Aspect Ratio Analysis
       ↓
Primitive Detection (Zig-zags, parallel lines, triangles, loops)
       ↓
Symbol Classification (Resistor, Capacitor, Diode, Source, Ground, Logic Gates)
       ↓
Endpoint Proximity Graph Construction (Wire snapping & node clustering)
       ↓
Circuit IR Generation
       ↓
Deterministic Experiment Matcher
```

## Supported Symbol Primitives
1. **Resistors**: Detected via repeated acute angle inflection points (zig-zag pattern).
2. **Capacitors**: Detected via two parallel orthogonal lines with gap distance $\le 25\text{ px}$.
3. **Diodes**: Detected via closed triangle with perpendicular cathode bar line.
4. **Logic Gates**: Detected via curved arcs (OR/XOR) vs flat inputs with semicircles (AND/NAND).
5. **Voltage Sources**: Detected via circles or long/short battery plates.
