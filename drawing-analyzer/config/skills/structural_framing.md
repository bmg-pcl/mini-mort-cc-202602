---
name: structural_framing
drawing_types:
- framing_plan
- plan
- structural_plan
disciplines:
- structural
description: Analyzes structural framing plans for steel and concrete
capabilities:
- quantity_takeoff
- measurement
- notes_extraction
- symbol_recognition
priority: 20
---

Analyze this structural framing plan region.

Focus on identifying and extracting:

1. STEEL BEAMS:
   - Wide flange beams (W shapes) - size (e.g., W12x26)
   - HSS tubes - size (e.g., HSS6x6x1/4)
   - Channels (C shapes)
   - Angles (L shapes)
   - Mark numbers and piece marks

2. STEEL COLUMNS:
   - Wide flange columns
   - HSS columns
   - Pipe columns
   - Column grid references (e.g., A1, B2)
   - Base plate sizes

3. CONCRETE ELEMENTS:
   - Beams - width x depth
   - Girders - width x depth
   - Columns - dimensions
   - Reinforcement notes (rebar sizes)

4. JOISTS & DECKING:
   - Open web steel joists (K, LH, DLH series)
   - Joist spacing
   - Metal deck type and gauge
   - Composite deck specifications

5. BRACING:
   - Horizontal bracing
   - Vertical bracing
   - Kickers and drag struts

6. CONNECTIONS:
   - Moment connections
   - Shear connections
   - Base plates
   - Connection detail references

For each element, extract:
- Member mark/ID
- Size/designation
- Quantity (if shown)
- Length (if dimensioned)
- Grid location
- Elevation reference

Respond with JSON in the standard format.
Use CSI Division 05 (Metals) or 03 (Concrete) codes where applicable.
