---
name: fire_protection
drawing_types:
- plan
- fire_protection_plan
- sprinkler_plan
- suppression_plan
disciplines:
- fire_protection
- sprinkler
- life_safety
description: Analyzes fire protection and sprinkler plans
capabilities:
- quantity_takeoff
- measurement
- notes_extraction
- symbol_recognition
priority: 18
---

Analyze this fire protection/sprinkler plan region.

Focus on identifying and extracting:

1. SPRINKLER HEADS:
   - Type (pendant, upright, sidewall, concealed)
   - K-factor
   - Temperature rating (color coded)
   - Coverage area
   - Head count per area
   - Special heads (ESFR, extended coverage)

2. PIPING:
   - Main sizes
   - Branch line sizes
   - Riser size
   - Cross main size
   - Feed main size
   - Pipe material (black steel, CPVC, etc.)

3. SYSTEM COMPONENTS:
   - Riser location and size
   - Fire department connection (FDC)
   - OS&Y valves
   - Check valves
   - Inspector's test connection
   - Drain valves
   - Alarm valves
   - Flow switches
   - Tamper switches

4. HANGERS & SUPPORTS:
   - Hanger types
   - Hanger spacing
   - Seismic bracing locations
   - Trapeze assemblies

5. HYDRAULIC DATA:
   - Design area
   - Design density (gpm/sf)
   - Remote area location
   - Required flow/pressure
   - Available pressure

6. SPECIAL SYSTEMS:
   - Pre-action systems
   - Deluge systems
   - Dry pipe systems
   - Clean agent systems
   - Kitchen hood suppression
   - Standpipe locations

7. FIRE EXTINGUISHERS:
   - Type (ABC, K, CO2)
   - Size
   - Location
   - Cabinet type

For each element, extract:
- Type/description
- Size/rating
- Quantity
- Location/coverage area
- Associated notes

Respond with JSON in the standard format.
Use CSI Division 21 (Fire Suppression) codes where applicable.
