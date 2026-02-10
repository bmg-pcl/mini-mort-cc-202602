---
name: generic_technical
drawing_types:
- all
- unknown
- general
disciplines:
- all
- unknown
description: Generic fallback skill for any technical drawing type
capabilities:
- quantity_takeoff
- measurement
- notes_extraction
- symbol_recognition
priority: 1
---

Analyze this technical drawing region.

This is a generic analysis skill that works with any drawing type.
Extract all relevant technical information visible in this region.

Focus on identifying and extracting:

1. QUANTITIES:
   - Count any distinct items, components, or symbols
   - Note recurring elements
   - Identify equipment or fixtures

2. MEASUREMENTS:
   - Dimension strings
   - Elevation callouts
   - Size annotations
   - Scale references

3. TEXT & NOTES:
   - Specifications
   - General notes
   - Warnings/cautions
   - Material callouts
   - Reference standards

4. CALLOUTS & TAGS:
   - Equipment tags
   - Detail markers
   - Section cuts
   - Grid references
   - Revision clouds/triangles

5. SYMBOLS:
   - Standard engineering symbols
   - Legend items
   - North arrows
   - Match lines
   - Break lines

6. TABLES & SCHEDULES:
   - Any tabular data
   - Bill of materials
   - Equipment lists
   - Keynotes

For each item found, extract:
- Description
- Quantity (if countable)
- Size/specification (if noted)
- Location reference
- Confidence level

Respond with JSON in the standard format.
Categorize items using appropriate CSI MasterFormat divisions.
