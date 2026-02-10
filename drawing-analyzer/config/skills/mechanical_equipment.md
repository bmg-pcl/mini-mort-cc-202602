---
name: mechanical_equipment
drawing_types:
- plan
- layout
- equipment_layout
- mechanical_plan
disciplines:
- mechanical
- HVAC
description: Analyzes mechanical equipment layouts and HVAC plans
capabilities:
- quantity_takeoff
- measurement
- notes_extraction
- symbol_recognition
priority: 15
---

Analyze this mechanical/HVAC drawing region.

Focus on identifying and extracting:

1. AIR HANDLING EQUIPMENT:
   - AHUs (Air Handling Units) - model, CFM, tonnage
   - RTUs (Rooftop Units) - model, CFM, tonnage
   - FCUs (Fan Coil Units) - model, CFM
   - VAV boxes - CFM min/max
   - Unit heaters
   - Exhaust fans - CFM

2. DUCTWORK:
   - Supply ducts - sizes (WxH or diameter)
   - Return ducts - sizes
   - Exhaust ducts - sizes
   - Flex duct runs
   - Duct insulation requirements

3. DIFFUSERS & GRILLES:
   - Supply diffusers - type, size, CFM
   - Return grilles - type, size
   - Linear diffusers - length
   - Slot diffusers

4. HYDRONIC SYSTEMS:
   - Pumps - GPM, HP
   - Chillers - tonnage
   - Boilers - MBH
   - Cooling towers
   - Expansion tanks

5. PIPING:
   - Chilled water - sizes
   - Hot water - sizes
   - Condensate - sizes
   - Refrigerant lines

6. CONTROLS:
   - Thermostats
   - Sensors (temperature, humidity, CO2)
   - Dampers (manual, motorized)
   - Control valves

For each equipment item, extract:
- Tag/ID number
- Model/size/capacity
- Location
- Associated schedule reference

Respond with JSON in the standard format.
Use CSI Division 23 (HVAC) codes where applicable.
