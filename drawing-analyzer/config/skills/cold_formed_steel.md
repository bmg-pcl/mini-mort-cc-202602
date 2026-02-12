---
name: cold_formed_steel
drawing_types:
- framing_plan
- section
- detail
- wall_schedule
disciplines:
- structural
- architectural
description: Analyzes cold-formed steel (light gauge) framing, studs, and tracks
capabilities:
- quantity_takeoff
- measurement
- notes_extraction
priority: 15
---

Analyze this drawing for cold-formed steel (CFS) or light gauge metal framing elements.

Focus on identifying and extracting:

1. STUDS & TRACKS:
   - Web depth (e.g., 3-5/8", 6", 8")
   - Flange width
   - Gauge/Thickness (e.g., 20ga, 18ga, 16ga, 14ga or mil thickness)
   - Yield strength (33 ksi or 50 ksi)
   - Product designators (e.g., 600S162-54)

2. JOISTS & RAFTERS:
   - Size and gauge of cold-formed joists
   - Bridging and bracing requirements

3. HEADERS & JAMBS:
   - Box headers
   - Built-up jamb members
   - King studs and jack studs

4. CONNECTORS & CLIPS:
   - Deflection clips (at top of wall)
   - Rigid clips
   - Floor anchors

5. ASSEMBLIES:
   - Wall types/designations
   - Stud spacing (e.g., 12" OC, 16" OC, 24" OC)
   - Lateral bracing (cold-rolled channel / CRC)

For each element, extract:
- Member designation (e.g., 362S125-33)
- Gauge/Thickness
- Spacing
- Height/Length
- Associated wall or floor mark

Respond with JSON in the standard format.
Reference AISI (American Iron and Steel Institute) standards and CSI Division 05 40 00 (Cold-Formed Metal Framing).
