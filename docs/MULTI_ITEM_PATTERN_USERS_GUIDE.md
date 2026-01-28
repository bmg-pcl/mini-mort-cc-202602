# Multi-Item Pattern Matching User's Guide

## MiniMort Pattern Query System

---

## Quick Start

### Your First Pattern Query

1. **Load a PDF** using the file upload button
2. **Click the "Pattern Matches" tab** in the right panel
3. **Type a query** in the console:

```
LIST A ABOVE B WITH A="Total:" AND B~/\d+/
```

4. **Press Enter** to execute
5. **View results** in the table below the console

This query finds all places where "Total:" appears directly above a number.

---

## Understanding the Query Language

### Basic Structure

Every pattern query follows this structure:

```
[COMMAND] ELEMENT [SPATIAL_OP ELEMENT]... [WITH CONDITIONS]
```

**Components:**
- **COMMAND**: `LIST` (show results) or `SELECT` (highlight on page)
- **ELEMENT**: A letter (A-Z) representing a page element
- **SPATIAL_OP**: How elements relate spatially (ABOVE, BELOW, etc.)
- **CONDITIONS**: Text matching rules for each element

### Element Bindings

Use single letters to name the elements you're looking for:

```
A ABOVE B           -- Two elements: A is above B
A LEFT OF B LEFT OF C   -- Three elements in a row
```

Each letter becomes a variable you can reference in the WITH clause.

---

## Spatial Operators

### Cardinal Directions

| Operator | Meaning | Diagram |
|----------|---------|---------|
| `ABOVE` | A is above B (with horizontal overlap) | `[A]`<br>`[B]` |
| `BELOW` | A is below B (with horizontal overlap) | `[B]`<br>`[A]` |
| `LEFT OF` | A is to the left of B (with vertical overlap) | `[A][B]` |
| `RIGHT OF` | A is to the right of B (with vertical overlap) | `[B][A]` |

**Horizontal/Vertical Overlap Requirement:**
Cardinal operators require the elements to share some horizontal (for ABOVE/BELOW) or vertical (for LEFT OF/RIGHT OF) space:

```
     [A]              [A]
       [B]    YES        [B]    NO (no overlap)
```

### Diagonal Directions

| Operator | Meaning |
|----------|---------|
| `TOP LEFT OF` | A is above and to the left of B |
| `TOP RIGHT OF` | A is above and to the right of B |
| `BOTTOM LEFT OF` | A is below and to the left of B |
| `BOTTOM RIGHT OF` | A is below and to the right of B |

Diagonal operators do NOT require overlap:

```
[A]
    [B]     -- A is TOP LEFT OF B
```

### Chaining Operators

Combine multiple spatial relationships:

```
A ABOVE B LEFT OF C
```

This finds patterns where:
- A is above B
- B is to the left of C

All three elements must be on the same page.

---

## Text Matching

### Literal Matching (=)

Match exact text:

```
WITH A="Invoice Number"
```

This matches elements with exactly "Invoice Number" as their text.

### Regex Matching (~)

Match text patterns using regular expressions:

```
WITH A~/INV-\d+/
```

Common regex patterns:

| Pattern | Matches |
|---------|---------|
| `\d+` | One or more digits |
| `\d{4}` | Exactly 4 digits |
| `\$[\d,]+\.\d{2}` | Currency like $1,234.56 |
| `\d{2}/\d{2}/\d{4}` | Date like 01/15/2024 |
| `[A-Z]{2,}` | Two or more uppercase letters |
| `\w+@\w+\.\w+` | Email addresses |
| `.*` | Any text |

### Regex Flags

Add flags after the closing `/`:

```
WITH A~/invoice/i    -- Case-insensitive
```

| Flag | Meaning |
|------|---------|
| `i` | Case-insensitive |
| `g` | Global (match all) |
| `m` | Multiline |

### Label Matching (MATCHES)

Match elements by their auto-detected labels:

```
WITH A MATCHES InvoiceNumber
```

This uses the label patterns you've loaded via the Tags/Labels file.

### Combining Conditions

Use `AND` to combine multiple conditions:

```
WITH A="Total:" AND B~/\d+\.\d{2}/ AND C MATCHES Currency
```

---

## Commands

### LIST

Display matching elements in the console:

```
LIST A ABOVE B WITH A="Name:" AND B~/\w+/
```

Output:
```
Found 5 matches:
 # │ File │ Page │ A (text) │ B (text)
───┼──────┼──────┼──────────┼──────────
 1 │ 0    │ 1    │ Name:    │ John Smith
 2 │ 0    │ 1    │ Name:    │ Jane Doe
 3 │ 0    │ 2    │ Name:    │ Bob Wilson
...
```

### SELECT

Find matches AND highlight them on the page:

```
SELECT A ABOVE B WITH A="Total" AND B~/\d+/
```

This:
1. Shows results in the console
2. Highlights matching element groups on the canvas
3. Marks matched elements as selected in the Text Extraction table

### GOTO

Navigate to a specific match from the results:

```
GOTO 3
```

Jumps to match #3, switching files/pages as needed and centering the view.

---

## Working with Vectors (Shapes)

### What Are Vectors?

Vectors are shapes you draw on the page:
- **Rectangles**: Drawn by dragging
- **Polygons**: Drawn by Shift+clicking multiple points
- **Circles**: Regular polygons (6+ sides) are auto-detected as circles
- **Lines**: Draw a two-point polygon

### Using Vectors in Queries

#### IN Operator

Find elements inside a shape:

```
A IN CIRCLE WITH A="Logo"
A IN RECTANGLE WITH A~/\d+/
A IN POLYGON WITH A MATCHES Address
```

This uses the most recent vector of that type on the current page.

#### Above/Below Line

Find elements relative to a line:

```
A ABOVE LINE WITH A="Header"
B BELOW LINE WITH B~/footer/i
```

### Naming Vectors

Give your vectors names for easier reference:

```
NAME CIRCLE AS logo_region
NAME RECTANGLE AS header_box
NAME LINE AS divider
```

Then use the name in queries:

```
A IN logo_region WITH A MATCHES CompanyName
B IN header_box WITH B="Invoice"
```

### Show Vectors

List all vectors on the current page:

```
SHOW VECTORS
```

Output:
```
Vectors on File 0, Page 1:
 # │ Type      │ Name          │ Details
───┼───────────┼───────────────┼─────────────────
 1 │ circle    │ logo_region   │ center(120,80) r=45
 2 │ rectangle │ header_box    │ (50,20)-(500,120)
 3 │ line      │ divider       │ (50,300)-(500,300)
 4 │ polygon   │ (unnamed)     │ 6 vertices
```

---

## Console Reference

### All Commands

| Command | Description |
|---------|-------------|
| `LIST <pattern>` | Find matches and display in console |
| `SELECT <pattern>` | Find matches and highlight on page |
| `GOTO <n>` | Navigate to match number n |
| `NAME <type> AS <name>` | Name a vector (CIRCLE, RECTANGLE, LINE, POLYGON) |
| `SHOW VECTORS` | List vectors on current page |
| `SHOW TABLES` | List all database tables |
| `SET TOLERANCE <n>` | Set spatial matching tolerance (pixels) |
| `SET PAGE <n>` | Set page context for queries |
| `SET FILE <n>` | Set file context for queries |
| `EXPLAIN <pattern>` | Show the SQL generated from a pattern |
| `SQL <query>` | Execute raw SQL directly |
| `CLEAR` | Clear console output |
| `HELP` | Show help information |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Execute query |
| `Shift+Enter` | New line (for multi-line queries) |
| `Up/Down` | Navigate command history |
| `Ctrl+L` | Clear console |
| `Escape` | Cancel / clear selection |
| `Tab` | Auto-complete |

---

## Examples

### Example 1: Invoice Header Fields

Find invoice numbers and dates:

```
LIST A LEFT OF B WITH A="Invoice #:" AND B~/INV-\d+/
LIST A LEFT OF B WITH A="Date:" AND B~/\d{2}\/\d{2}\/\d{4}/
```

### Example 2: Table Cell Extraction

Find label-value pairs in a form:

```
SELECT A LEFT OF B WITH A~/^[A-Za-z ]+:$/ AND B~/\S+/
```

This matches patterns like:
- "Name: John Smith"
- "Email: john@example.com"
- "Phone: 555-1234"

### Example 3: Financial Totals

Find amounts with their labels:

```
LIST A ABOVE B WITH A MATCHES CurrencyLabel AND B~/\$[\d,]+\.\d{2}/
```

### Example 4: Header in Region

First draw a rectangle around the header area, then:

```
NAME RECTANGLE AS header
SELECT A IN header WITH A MATCHES CompanyName
```

### Example 5: Elements Above a Line

Draw a horizontal line, then find everything above it:

```
NAME LINE AS fold_line
LIST A ABOVE LINE WITH A~/\S+/
```

### Example 6: Multi-Element Alignment

Find three horizontally aligned elements (like table rows):

```
LIST A LEFT OF B LEFT OF C WITH A~/\d+/ AND B~/\w+/ AND C~/\$\d+/
```

### Example 7: Diagonal Relationships

Find a value below and to the right of its label (common in forms):

```
SELECT LABEL BOTTOM LEFT OF VALUE WITH LABEL="Signature" AND VALUE~/\S+/
```

### Example 8: Debugging with EXPLAIN

See what SQL gets generated:

```
EXPLAIN A ABOVE B WITH A="Test"
```

Output:
```sql
SELECT
    a.id AS a_id, a.text AS a_text, ...
FROM elements a
JOIN elements b ON a.file_id = b.file_id AND a.page = b.page
WHERE spatial_above(a.x1, a.y1, a.x2, a.y2, b.x1, b.y1, b.x2, b.y2)
  AND text_match(a.text, 'Test')
ORDER BY a.file_id, a.page, a.y1, a.x1;
```

### Example 9: Raw SQL Queries

For complex analysis, drop to raw SQL:

```
SQL SELECT text, COUNT(*) as cnt FROM elements GROUP BY text ORDER BY cnt DESC LIMIT 10
```

---

## Tips and Best Practices

### 1. Start Simple

Begin with basic patterns and add complexity:

```
-- Start here
LIST A WITH A="Total"

-- Then add relationships
LIST A ABOVE B WITH A="Total"

-- Then add conditions
LIST A ABOVE B WITH A="Total" AND B~/\d+/
```

### 2. Use EXPLAIN

When queries don't return expected results, use EXPLAIN to see the generated SQL:

```
EXPLAIN A ABOVE B WITH A="Total"
```

### 3. Check Your Regex

Test regex patterns incrementally:

```
LIST A WITH A~/\d+/           -- Find any numbers
LIST A WITH A~/\$\d+/         -- Find dollar amounts
LIST A WITH A~/\$[\d,]+\.\d{2}/  -- Find formatted currency
```

### 4. Adjust Tolerance

If spatial matches are too strict, add tolerance:

```
SET TOLERANCE 5
LIST A ABOVE B WITH A="Total" AND B~/\d+/
```

This allows 5 pixels of flexibility in spatial relationships.

### 5. Name Your Vectors

Instead of relying on "most recent," give vectors meaningful names:

```
NAME RECTANGLE AS line_items_table
NAME CIRCLE AS company_logo
NAME LINE AS signature_line
```

### 6. Export Results

Click the "Export CSV" button above the results table to save matches for further analysis.

### 7. Combine with Labels

Load your label patterns first, then use MATCHES for cleaner queries:

```
-- Instead of:
LIST A WITH A~/^INV-\d+$/

-- Use:
LIST A WITH A MATCHES InvoiceNumber
```

---

## Troubleshooting

### "No matches found"

1. **Check spelling**: Queries are case-sensitive by default
2. **Add regex flag**: Use `/pattern/i` for case-insensitive
3. **Verify spatial relationship**: Use SELECT to visualize what's being compared
4. **Check page context**: Use `SET PAGE` to target specific page
5. **Reduce tolerance**: `SET TOLERANCE 0` for exact matching

### "Unknown identifier: X"

Every element letter must appear either:
- Before a spatial operator: `A ABOVE B`
- In the WITH clause: `WITH A="text"`

### "Regex syntax error"

Check your regex pattern:
- Escape special characters: `\$`, `\.`, `\(`, `\)`
- Use proper quantifiers: `+`, `*`, `{n}`, `{n,m}`
- Close all groups: `()`, `[]`

### "Vector not found"

1. Draw the vector type you're referencing (CIRCLE, LINE, etc.)
2. Make sure you're on the correct page
3. Use SHOW VECTORS to see available vectors
4. Use a named vector instead of type reference

### Slow queries

For large PDFs:
1. Add more specific conditions
2. Limit to specific pages: `SET PAGE 1`
3. Use indexed fields (text, file_id, page)

---

## Appendix: Regex Quick Reference

| Pattern | Description | Example Matches |
|---------|-------------|-----------------|
| `.` | Any character | a, 1, @ |
| `\d` | Digit | 0-9 |
| `\w` | Word character | a-z, A-Z, 0-9, _ |
| `\s` | Whitespace | space, tab, newline |
| `[abc]` | Character class | a, b, or c |
| `[^abc]` | Negated class | anything except a, b, c |
| `+` | One or more | `\d+` matches 123 |
| `*` | Zero or more | `\d*` matches "" or 123 |
| `?` | Zero or one | `\d?` matches "" or 1 |
| `{n}` | Exactly n | `\d{4}` matches 2024 |
| `{n,m}` | Between n and m | `\d{2,4}` matches 12, 123, 1234 |
| `^` | Start of string | `^INV` matches "INV-001" |
| `$` | End of string | `USD$` matches "100 USD" |
| `\|` | Alternation | `cat\|dog` matches "cat" or "dog" |
| `()` | Group | `(USD\|EUR)` groups alternatives |
| `\.` | Literal dot | `\.pdf` matches ".pdf" |
| `\$` | Literal dollar | `\$100` matches "$100" |

---

*For technical details and implementation information, see the [Multi-Item Pattern Matching Specification](./MULTI_ITEM_PATTERN_SPEC.md).*
