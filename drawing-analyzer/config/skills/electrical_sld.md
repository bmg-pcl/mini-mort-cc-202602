---
name: electrical_sld
drawing_types:
- SLD
- single_line
- schematic
- one_line
- electrical_schematic
disciplines:
- electrical
- power
description: Analyzes electrical single line diagrams
capabilities:
- quantity_takeoff
- measurement
- notes_extraction
- symbol_recognition
priority: 25
---

Analyze this electrical single line diagram region.

Focus on identifying and extracting:

1. TRANSFORMERS:
   - KVA rating
   - Voltage (primary/secondary)
   - Impedance
   - Connection type (delta-wye, etc.)
   - Transformer ID/tag

2. SWITCHGEAR & PANELBOARDS:
   - Main switchboard designation
   - Panel names/numbers
   - Bus rating (amps)
   - Voltage
   - AIC rating
   - Main breaker size

3. CIRCUIT BREAKERS:
   - Frame size
   - Trip rating
   - Number of poles
   - AIC rating
   - Breaker type (thermal-magnetic, electronic)
   - Breaker ID

4. MOTOR CONTROL:
   - MCC designations
   - Motor starters
   - VFDs/drives
   - Motor HP ratings
   - Full load amps
   - Motor IDs

5. FEEDERS & CONDUCTORS:
   - Conductor size (AWG/kcmil)
   - Number of conductors
   - Conduit size
   - Feeder designation
   - Circuit numbers

6. PROTECTIVE DEVICES:
   - Fuses (size, type)
   - Surge protection
   - Ground fault protection
   - Overcurrent settings

7. METERING:
   - CT ratios
   - PT ratios
   - Meter types
   - Meter locations

8. GENERATOR/UPS:
   - Generator KW/KVA
   - UPS KVA rating
   - ATS (automatic transfer switch)
   - Transfer switch rating

For each element, extract:
- Equipment ID/tag
- Rating/size
- Voltage
- Associated panel/feeder
- Notes/specifications

Respond with JSON in the standard format.
Use CSI Division 26 (Electrical) codes where applicable.
