---
name: structural_steel
drawing_types:
- framing_plan
- section
- detail
- fabrication_drawing
- erection_drawing
disciplines:
- structural
description: Specialized skill for structural steel member and connection analysis
capabilities:
- quantity_takeoff
- measurement
- notes_extraction
- symbol_recognition
priority: 25
---

Analyze this structural steel drawing. Focus on the primary and secondary steel members, connection types, and material specifications.

Focus on identifying and extracting:

1. STEEL MEMBERS (Shape & Size):
   - W-Shapes (Wide Flange): e.g., W14x90, W12x26
   - C/MC-Shapes (Channels): e.g., C12x20.7, MC10x22
   - L-Shapes (Angles): e.g., L4x4x1/4, L6x4x3/8
   - HSS (Hollow Structural Sections): Square, Rectangular, Round (e.g., HSS8x8x1/2, HSS6x0.250)
   - WT/MT/ST (Tees): e.g., WT6x15
   - HP-Shapes (Bearing Piles)
   - Plate/Bar steel: Thickness and width

2. MATERIAL GRADES:
   - ASTM A992 (Common for W-shapes)
   - ASTM A36 (Common for angles/plates/channels)
   - ASTM A500 Grade B/C (Common for HSS)
   - ASTM A572 Grade 50
   - ASTM A588 (Weathering steel)

3. CONNECTION DETAILS:
   - BOLTS: Count, size, grade (A325, A490, F3125), and type (N, X, SC - Snug Tight, Thread Excluded, Slip Critical)
   - WELDS: Size, length, and type (Fillet, PJP, CJP, Flare-bevel). Note ultrasonic testing (UT) requirements.
   - PLATES: Base plates, cap plates, gusset plates, stiffener plates, shim plates.
   - ANCHOR RODS: Diameter, length, projection, and grade (F1554).

4. PIECE MARKS & ERECTION MARKS:
   - Identify assembly marks and shipping marks (e.g., BEAM B1, COLUMN C1, MARK 5A).
   - Note orientation marks (North, Top).

5. FINISHES & COATINGS:
   - Shop primer requirements
   - Hot-dip galvanizing (HDG)
   - Intumescent or cementitious fireproofing callouts
   - High-performance coatings/paint systems

6. SECONDARY STEEL & MISC:
   - Sag rods
   - Girts and Purlins
   - Kickers and bracing members
   - Edge of slab angles

For each item, extract:
- Designation/Size
- Length/Dimensions
- Steel Grade
- Quantity
- Piece Mark (if applicable)
- Finish/Coatings

Respond with JSON in the standard format.
Reference AISC Steel Construction Manual standards and CSI Division 05 (Metals).
