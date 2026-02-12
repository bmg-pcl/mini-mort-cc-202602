---
name: plumbing_riser
drawing_types:
- riser
- isometric
- riser_diagram
- plumbing_riser
disciplines:
- plumbing
description: Analyzes plumbing riser diagrams
capabilities:
- quantity_takeoff
- measurement
- notes_extraction
- symbol_recognition
priority: 18
---

Analyze this plumbing riser diagram region.

Focus on identifying and extracting:

1. WATER SUPPLY:
   - Cold water piping - sizes
   - Hot water piping - sizes
   - Hot water return - sizes
   - Water meter size
   - Backflow preventers
   - PRV (pressure reducing valves)
   - Expansion tanks

2. SANITARY WASTE:
   - Waste pipe sizes
   - Soil stack sizes
   - Vent sizes
   - Building drain size
   - Cleanout locations
   - P-traps
   - Floor drains

3. VENT SYSTEM:
   - Vent stack sizes
   - Individual vents
   - Wet vents
   - Air admittance valves
   - Vent through roof (VTR)

4. STORM DRAINAGE:
   - Roof drain sizes
   - Leader sizes
   - Storm main sizes
   - Overflow drains
   - Area drains
   - Trench drains

5. FIXTURES:
   - Water closets
   - Lavatories
   - Sinks (kitchen, utility, mop)
   - Showers/tubs
   - Drinking fountains
   - Water heaters
   - Fixture unit counts

6. VALVES & SPECIALTIES:
   - Shut-off valves
   - Check valves
   - Mixing valves
   - Trap primers
   - Interceptors (grease, oil)
   - Ejector pumps
   - Sump pumps

7. GAS PIPING (if shown):
   - Gas pipe sizes
   - Gas meter
   - Shut-off valves
   - Flex connectors
   - BTU loads

For each element, extract:
- Type/description
- Size
- Quantity
- Floor/elevation
- Associated fixture groups

Respond with JSON in the standard format.
Use CSI Division 22 (Plumbing) codes where applicable.
