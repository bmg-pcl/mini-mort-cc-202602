---
name: miscellaneous_metals
drawing_types:
- detail
- section
- plan
- stair_detail
disciplines:
- structural
- architectural
description: Analyzes miscellaneous metal elements like stairs, railings, and ladders
capabilities:
- quantity_takeoff
- measurement
- notes_extraction
- symbol_recognition
priority: 15
---

Analyze this drawing for miscellaneous metal components, which are often separate from the primary structural frame.

Focus on identifying and extracting:

1. STAIRS:
   - Stringers: Channels (C-shape) or Plate size
   - Treads: Grating, checkered plate, or pan-filled concrete
   - Risers: Height and type (open/closed)
   - Landing framing and plates

2. RAILINGS & HANDRAILS:
   - Post sizes (Pipe, HSS, or Bar)
   - Top rail and mid-rail sizes
   - Infill: Pickets, wire mesh, glass, or cables
   - Mounting: Side-mounted (sleeve/bracket) or top-mounted (base plate)
   - Material: Steel, Stainless Steel, or Aluminum

3. LADDERS:
   - Side rails (Bar or Angle)
   - Rungs (Round bar/Square bar, diameter)
   - Safety cages: Vertical bars and hoops
   - Stand-off brackets

4. GRATINGS & PLATES:
   - Floor grating: Bearing bar size and spacing, cross bar spacing
   - Checkered (diamond) plate: Thickness
   - Trench covers and frames

5. EMBEDS & MISC:
   - Curb angles / Nosings
   - Lintels (Angles or Channels over openings)
   - Bollards (Pipe size, concrete filled)
   - Wall brackets and supports

6. FINISHES:
   - Hot-dip galvanized
   - Powder coated
   - Primed only
   - Polished (for stainless/aluminum)

For each component, extract:
- Type of element
- Material and Member Size
- Dimensions (Length, Height, Width)
- Quantity
- Finish specification

Respond with JSON in the standard format.
Reference CSI Division 05 (Metals), specifically 05 50 00 (Metal Fabrications) and 05 51 00 (Metal Stairs).
