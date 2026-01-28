# Multi-Item Pattern Matching Specification

## Version 1.0

## Executive Summary

This specification defines a new multi-item spatial pattern matching system for MiniMort. The feature enables users to find groups of page elements that match complex spatial and textual relationships, such as "find all instances where text 'Total:' appears above a number matching `\d+\.\d{2}`".

The architecture leverages WebAssembly DuckDB for high-performance SQL queries, with custom spatial functions and a domain-specific language (DSL) that compiles to SQL.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Model](#2-data-model)
3. [DSL Grammar](#3-dsl-grammar)
4. [Spatial Operators](#4-spatial-operators)
5. [Vector Element Support](#5-vector-element-support)
6. [Query Console (REPL)](#6-query-console-repl)
7. [UI Integration](#7-ui-integration)
8. [Implementation Phases](#8-implementation-phases)

---

## 1. Architecture Overview

### 1.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        MiniMort UI                               │
├─────────────────┬───────────────────────┬───────────────────────┤
│  Text Extraction│   Pattern Matches     │    Query Console      │
│     Tab         │       Tab             │      (REPL)           │
└────────┬────────┴───────────┬───────────┴───────────┬───────────┘
         │                    │                       │
         │                    ▼                       │
         │         ┌─────────────────────┐            │
         │         │   DSL Compiler      │◄───────────┘
         │         │  (Pattern → SQL)    │
         │         └─────────┬───────────┘
         │                   │
         ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DuckDB WASM Engine                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │   elements   │  │   vectors    │  │   Custom Functions     │ │
│  │    Table     │  │    Table     │  │   • spatial_above()    │ │
│  │              │  │              │  │   • spatial_left_of()  │ │
│  │ - id         │  │ - id         │  │   • spatial_right_of() │ │
│  │ - file_id    │  │ - file_id    │  │   • spatial_below()    │ │
│  │ - page       │  │ - page       │  │   • in_circle()        │ │
│  │ - type       │  │ - type       │  │   • in_polygon()       │ │
│  │ - x1,y1,x2,y2│  │ - shape_type │  │   • above_line()       │ │
│  │ - text       │  │ - center_x/y │  │   • below_line()       │ │
│  │ - labels[]   │  │ - radius     │  │   • text_match()       │ │
│  └──────────────┘  │ - vertices[] │  │   • regex_match()      │ │
│                    └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Query Engine | DuckDB WASM | In-browser SQL, vectorized execution, UDF support |
| DSL Parser | Hand-written recursive descent | Simple grammar, no build step |
| UI | Vanilla JS (existing) | Consistency with codebase |
| State Sync | Event-driven | Elements table syncs on PDF load |

### 1.3 Data Flow

1. **PDF Load** → Extract elements → Populate DuckDB `elements` table
2. **Selection Draw** → Create vector → Insert into `vectors` table
3. **Query Submit** → DSL parse → SQL generation → DuckDB execute → Results
4. **LIST Command** → Display results in console
5. **SELECT Command** → Highlight elements on canvas + select in table

---

## 2. Data Model

### 2.1 Elements Table

```sql
CREATE TABLE elements (
    id              INTEGER PRIMARY KEY,
    file_id         INTEGER NOT NULL,
    file_md5        VARCHAR(32) NOT NULL,
    page            INTEGER NOT NULL,
    type            VARCHAR(16) NOT NULL,  -- 'text', 'annotation'
    x1              DOUBLE NOT NULL,
    y1              DOUBLE NOT NULL,
    x2              DOUBLE NOT NULL,
    y2              DOUBLE NOT NULL,
    cx              DOUBLE GENERATED ALWAYS AS ((x1 + x2) / 2),  -- center x
    cy              DOUBLE GENERATED ALWAYS AS ((y1 + y2) / 2),  -- center y
    width           DOUBLE GENERATED ALWAYS AS (x2 - x1),
    height          DOUBLE GENERATED ALWAYS AS (y2 - y1),
    text            TEXT,
    labels          TEXT[]  -- Array of matched label names
);

CREATE INDEX idx_elements_page ON elements(file_id, page);
CREATE INDEX idx_elements_text ON elements(text);
CREATE INDEX idx_elements_spatial ON elements(file_id, page, x1, y1, x2, y2);
```

### 2.2 Vectors Table

```sql
CREATE TABLE vectors (
    id              INTEGER PRIMARY KEY,
    file_id         INTEGER NOT NULL,
    page            INTEGER NOT NULL,
    name            VARCHAR(64),           -- User-assigned name (optional)
    shape_type      VARCHAR(16) NOT NULL,  -- 'rectangle', 'polygon', 'circle', 'line'
    -- For rectangles and bounding boxes
    x1              DOUBLE,
    y1              DOUBLE,
    x2              DOUBLE,
    y2              DOUBLE,
    -- For circles (n-gons resolved to circles)
    center_x        DOUBLE,
    center_y        DOUBLE,
    radius          DOUBLE,
    -- For lines
    line_x1         DOUBLE,
    line_y1         DOUBLE,
    line_x2         DOUBLE,
    line_y2         DOUBLE,
    -- For polygons (stored as JSON array)
    vertices        JSON,  -- [{x: number, y: number}, ...]
    -- Metadata
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vectors_page ON vectors(file_id, page);
```

### 2.3 N-gon to Circle Resolution

Polygons with 6+ vertices that are approximately circular are automatically resolved to circles:

```javascript
function resolveNgonToCircle(polygon) {
    const n = polygon.vertices.length;
    if (n < 6) return null;  // Not enough vertices for circle approximation

    // Calculate centroid
    const cx = vertices.reduce((s, v) => s + v.x, 0) / n;
    const cy = vertices.reduce((s, v) => s + v.y, 0) / n;

    // Calculate average radius and variance
    const radii = vertices.map(v => Math.sqrt((v.x-cx)**2 + (v.y-cy)**2));
    const avgRadius = radii.reduce((s, r) => s + r, 0) / n;
    const variance = radii.reduce((s, r) => s + (r - avgRadius)**2, 0) / n;
    const cv = Math.sqrt(variance) / avgRadius;  // Coefficient of variation

    // If CV < 10%, treat as circle
    if (cv < 0.10) {
        return { center_x: cx, center_y: cy, radius: avgRadius };
    }
    return null;  // Keep as polygon
}
```

---

## 3. DSL Grammar

### 3.1 EBNF Grammar

```ebnf
query           ::= list_query | select_query | pattern_query

list_query      ::= 'LIST' pattern_expr
select_query    ::= 'SELECT' pattern_expr
pattern_query   ::= pattern_expr

pattern_expr    ::= element_binding (spatial_clause)* (with_clause)?

element_binding ::= IDENTIFIER

spatial_clause  ::= spatial_op element_binding
                  | spatial_op vector_ref

spatial_op      ::= 'ABOVE' | 'BELOW' | 'LEFT' 'OF' | 'RIGHT' 'OF'
                  | 'TOP' 'LEFT' 'OF' | 'TOP' 'RIGHT' 'OF'
                  | 'BOTTOM' 'LEFT' 'OF' | 'BOTTOM' 'RIGHT' 'OF'
                  | 'IN'

vector_ref      ::= 'CIRCLE' | 'LINE' | 'RECTANGLE' | 'POLYGON'
                  | IDENTIFIER  -- named vector

with_clause     ::= 'WITH' condition ('AND' condition)*

condition       ::= IDENTIFIER '=' string_match
                  | IDENTIFIER '~' regex_pattern
                  | IDENTIFIER 'MATCHES' label_name

string_match    ::= '"' STRING '"'
regex_pattern   ::= '/' REGEX '/' flags?
label_name      ::= IDENTIFIER

IDENTIFIER      ::= [A-Z][A-Z0-9_]*
STRING          ::= (any character except unescaped ")*
REGEX           ::= (any character except unescaped /)*
flags           ::= [gimsuvy]*
```

### 3.2 Query Examples

**Simple two-element pattern:**
```
A ABOVE B WITH A="Total:" AND B~/\$[\d,]+\.\d{2}/
```

**Three-element alignment:**
```
A LEFT OF B LEFT OF C WITH A="Name" AND B=":" AND C~/\w+/
```

**Diagonal relationships:**
```
HEADER TOP LEFT OF VALUE WITH HEADER="Invoice #" AND VALUE~/INV-\d+/
```

**With vector constraints:**
```
A ABOVE LINE AND IN CIRCLE WITH A MATCHES InvoiceNumber
```

**Named vector reference:**
```
A IN header_region WITH A="Contract"
```

**LIST command (console output):**
```
LIST A ABOVE B WITH A="Total" AND B~/\d+/
```

**SELECT command (visual selection):**
```
SELECT A ABOVE B WITH A="Date:" AND B~/\d{2}\/\d{2}\/\d{4}/
```

### 3.3 DSL to SQL Compilation

**Input DSL:**
```
A ABOVE B WITH A="Total:" AND B~/\d+\.\d{2}/
```

**Generated SQL:**
```sql
SELECT
    a.id AS a_id, a.text AS a_text, a.x1 AS a_x1, a.y1 AS a_y1, a.x2 AS a_x2, a.y2 AS a_y2,
    b.id AS b_id, b.text AS b_text, b.x1 AS b_x1, b.y1 AS b_y1, b.x2 AS b_x2, b.y2 AS b_y2
FROM elements a
JOIN elements b ON a.file_id = b.file_id AND a.page = b.page
WHERE spatial_above(a.x1, a.y1, a.x2, a.y2, b.x1, b.y1, b.x2, b.y2)
  AND text_match(a.text, 'Total:')
  AND regex_match(b.text, '\d+\.\d{2}', '')
ORDER BY a.file_id, a.page, a.y1, a.x1;
```

---

## 4. Spatial Operators

### 4.1 Operator Definitions

All spatial operators use element bounding boxes (x1, y1, x2, y2) where:
- (x1, y1) = top-left corner
- (x2, y2) = bottom-right corner
- Coordinates increase right and down (canvas convention)

#### 4.1.1 ABOVE

Element A is **ABOVE** element B if A's bottom edge is above B's top edge with horizontal overlap.

```sql
CREATE FUNCTION spatial_above(
    a_x1 DOUBLE, a_y1 DOUBLE, a_x2 DOUBLE, a_y2 DOUBLE,
    b_x1 DOUBLE, b_y1 DOUBLE, b_x2 DOUBLE, b_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    -- A's bottom (a_y2) must be above B's top (b_y1)
    -- Must have horizontal overlap
    SELECT a_y2 <= b_y1
       AND a_x2 > b_x1
       AND a_x1 < b_x2
$$;
```

#### 4.1.2 BELOW

Element A is **BELOW** element B if A's top edge is below B's bottom edge with horizontal overlap.

```sql
CREATE FUNCTION spatial_below(
    a_x1 DOUBLE, a_y1 DOUBLE, a_x2 DOUBLE, a_y2 DOUBLE,
    b_x1 DOUBLE, b_y1 DOUBLE, b_x2 DOUBLE, b_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    SELECT a_y1 >= b_y2
       AND a_x2 > b_x1
       AND a_x1 < b_x2
$$;
```

#### 4.1.3 LEFT OF

Element A is **LEFT OF** element B if A's right edge is to the left of B's left edge with vertical overlap.

```sql
CREATE FUNCTION spatial_left_of(
    a_x1 DOUBLE, a_y1 DOUBLE, a_x2 DOUBLE, a_y2 DOUBLE,
    b_x1 DOUBLE, b_y1 DOUBLE, b_x2 DOUBLE, b_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    SELECT a_x2 <= b_x1
       AND a_y2 > b_y1
       AND a_y1 < b_y2
$$;
```

#### 4.1.4 RIGHT OF

Element A is **RIGHT OF** element B if A's left edge is to the right of B's right edge with vertical overlap.

```sql
CREATE FUNCTION spatial_right_of(
    a_x1 DOUBLE, a_y1 DOUBLE, a_x2 DOUBLE, a_y2 DOUBLE,
    b_x1 DOUBLE, b_y1 DOUBLE, b_x2 DOUBLE, b_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    SELECT a_x1 >= b_x2
       AND a_y2 > b_y1
       AND a_y1 < b_y2
$$;
```

#### 4.1.5 Diagonal Operators

**TOP LEFT OF**: A is above and to the left of B (no overlap requirement).

```sql
CREATE FUNCTION spatial_top_left_of(
    a_x1 DOUBLE, a_y1 DOUBLE, a_x2 DOUBLE, a_y2 DOUBLE,
    b_x1 DOUBLE, b_y1 DOUBLE, b_x2 DOUBLE, b_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    SELECT a_y2 <= b_y1 AND a_x2 <= b_x1
$$;
```

**TOP RIGHT OF**: A is above and to the right of B.

```sql
CREATE FUNCTION spatial_top_right_of(
    a_x1 DOUBLE, a_y1 DOUBLE, a_x2 DOUBLE, a_y2 DOUBLE,
    b_x1 DOUBLE, b_y1 DOUBLE, b_x2 DOUBLE, b_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    SELECT a_y2 <= b_y1 AND a_x1 >= b_x2
$$;
```

**BOTTOM LEFT OF**: A is below and to the left of B.

```sql
CREATE FUNCTION spatial_bottom_left_of(
    a_x1 DOUBLE, a_y1 DOUBLE, a_x2 DOUBLE, a_y2 DOUBLE,
    b_x1 DOUBLE, b_y1 DOUBLE, b_x2 DOUBLE, b_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    SELECT a_y1 >= b_y2 AND a_x2 <= b_x1
$$;
```

**BOTTOM RIGHT OF**: A is below and to the right of B.

```sql
CREATE FUNCTION spatial_bottom_right_of(
    a_x1 DOUBLE, a_y1 DOUBLE, a_x2 DOUBLE, a_y2 DOUBLE,
    b_x1 DOUBLE, b_y1 DOUBLE, b_x2 DOUBLE, b_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    SELECT a_y1 >= b_y2 AND a_x1 >= b_x2
$$;
```

### 4.2 Spatial Relationship Diagram

```
                    ABOVE
                      ▲
                      │
         TOP LEFT   ╲ │ ╱   TOP RIGHT
                  ╲   │   ╱
                    ╲ │ ╱
    LEFT OF ◄─────── [B] ────────► RIGHT OF
                    ╱ │ ╲
                  ╱   │   ╲
      BOTTOM LEFT  ╱  │  ╲  BOTTOM RIGHT
                      │
                      ▼
                    BELOW
```

### 4.3 Tolerance Parameters

Operators support optional tolerance parameters for fuzzy matching:

```sql
-- With 5-pixel tolerance
spatial_above(a.*, b.*, tolerance := 5)
```

Default tolerance: 0 (exact). Configurable via REPL command:

```
SET TOLERANCE 5
```

---

## 5. Vector Element Support

### 5.1 Circle Containment

Test if an element's center point is inside a circle.

```sql
CREATE FUNCTION in_circle(
    elem_cx DOUBLE, elem_cy DOUBLE,  -- Element center
    circle_cx DOUBLE, circle_cy DOUBLE, circle_r DOUBLE
) RETURNS BOOLEAN AS $$
    SELECT SQRT(POWER(elem_cx - circle_cx, 2) +
                POWER(elem_cy - circle_cy, 2)) <= circle_r
$$;
```

### 5.2 Line Relationships

Test if an element is above or below a line defined by two points.

```sql
CREATE FUNCTION above_line(
    elem_cx DOUBLE, elem_cy DOUBLE,
    line_x1 DOUBLE, line_y1 DOUBLE,
    line_x2 DOUBLE, line_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    -- Cross product: positive = above line (assuming y increases downward)
    SELECT (line_x2 - line_x1) * (elem_cy - line_y1) -
           (line_y2 - line_y1) * (elem_cx - line_x1) < 0
$$;

CREATE FUNCTION below_line(
    elem_cx DOUBLE, elem_cy DOUBLE,
    line_x1 DOUBLE, line_y1 DOUBLE,
    line_x2 DOUBLE, line_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    SELECT (line_x2 - line_x1) * (elem_cy - line_y1) -
           (line_y2 - line_y1) * (elem_cx - line_x1) > 0
$$;
```

### 5.3 Polygon Containment (Ray Casting)

```sql
CREATE FUNCTION in_polygon(
    elem_cx DOUBLE, elem_cy DOUBLE,
    vertices JSON  -- [{x: number, y: number}, ...]
) RETURNS BOOLEAN AS $$
    -- Implements ray casting algorithm
    -- Returns true if point is inside polygon
$$;
```

### 5.4 Rectangle Containment

```sql
CREATE FUNCTION in_rectangle(
    elem_x1 DOUBLE, elem_y1 DOUBLE, elem_x2 DOUBLE, elem_y2 DOUBLE,
    rect_x1 DOUBLE, rect_y1 DOUBLE, rect_x2 DOUBLE, rect_y2 DOUBLE
) RETURNS BOOLEAN AS $$
    SELECT elem_x1 >= rect_x1 AND elem_y1 >= rect_y1
       AND elem_x2 <= rect_x2 AND elem_y2 <= rect_y2
$$;
```

### 5.5 DSL Syntax for Vector References

**By type (uses most recent vector of that type on current page):**
```
A IN CIRCLE WITH A="Total"
A ABOVE LINE WITH A~/\d+/
A IN RECTANGLE WITH A MATCHES InvoiceNumber
```

**By name (user-named vectors):**
```
A IN header_box WITH A="Invoice"
B BELOW signature_line WITH B~/Signed:/
```

**Naming vectors in REPL:**
```
NAME CIRCLE AS logo_area
NAME LINE AS page_divider
NAME POLYGON AS stamp_region
```

---

## 6. Query Console (REPL)

### 6.1 Console UI

```
┌─────────────────────────────────────────────────────────────────┐
│ Pattern Query Console                              [Clear] [?]  │
├─────────────────────────────────────────────────────────────────┤
│ > LIST A ABOVE B WITH A="Total:" AND B~/\d+\.\d{2}/             │
│                                                                 │
│ Found 3 matches:                                                │
│ ┌───┬──────┬──────┬───────────────┬───────────────────────────┐ │
│ │ # │ File │ Page │ A (text)      │ B (text)                  │ │
│ ├───┼──────┼──────┼───────────────┼───────────────────────────┤ │
│ │ 1 │ 0    │ 1    │ Total:        │ $1,234.56                 │ │
│ │ 2 │ 0    │ 2    │ Total:        │ $567.89                   │ │
│ │ 3 │ 1    │ 1    │ Total:        │ $2,000.00                 │ │
│ └───┴──────┴──────┴───────────────┴───────────────────────────┘ │
│                                                                 │
│ > _                                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 REPL Commands

| Command | Description | Example |
|---------|-------------|---------|
| `LIST <pattern>` | Execute pattern query and display results | `LIST A ABOVE B WITH A="Total"` |
| `SELECT <pattern>` | Execute query and select matches in viewer | `SELECT A BELOW B WITH B="Date:"` |
| `SHOW VECTORS` | List all vectors on current page | `SHOW VECTORS` |
| `SHOW TABLES` | List DuckDB tables | `SHOW TABLES` |
| `NAME <type> AS <name>` | Name the most recent vector | `NAME CIRCLE AS logo` |
| `SET TOLERANCE <n>` | Set spatial tolerance in pixels | `SET TOLERANCE 5` |
| `SET PAGE <n>` | Set current page context | `SET PAGE 2` |
| `SET FILE <n>` | Set current file context | `SET FILE 0` |
| `EXPLAIN <pattern>` | Show generated SQL | `EXPLAIN A ABOVE B` |
| `CLEAR` | Clear console output | `CLEAR` |
| `HELP` | Show command reference | `HELP` |
| `SQL <query>` | Execute raw DuckDB SQL | `SQL SELECT COUNT(*) FROM elements` |

### 6.3 Console Features

- **Syntax highlighting**: Keywords, strings, regex patterns color-coded
- **Auto-complete**: Suggests identifiers, operators, vector names
- **History**: Up/Down arrows navigate command history
- **Multi-line**: Shift+Enter for multi-line queries
- **Error display**: Parse and execution errors with position markers
- **Result export**: Click to copy results as CSV

### 6.4 Result Navigation

Results from `LIST` and `SELECT` commands include row numbers. Users can:

```
GOTO 2  -- Navigate to match #2 (adjusts file/page and centers view)
```

---

## 7. UI Integration

### 7.1 Tab Layout

The right panel gains a tab interface:

```
┌─────────────────────────────────────────────────────────────────┐
│  [Text Extraction]  [Pattern Matches]                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│          (Tab content area)                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Text Extraction Tab (Existing)

Unchanged from current implementation:
- CSV export buttons
- Tag/label file loading
- Element table with columns: Selected, File, Page, Text, Labels, Coordinates

### 7.3 Pattern Matches Tab (New)

```
┌─────────────────────────────────────────────────────────────────┐
│  [Text Extraction]  [Pattern Matches]                           │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Pattern Query Console                          [Clear] [?]  │ │
│ │─────────────────────────────────────────────────────────────│ │
│ │ > _                                                         │ │
│ │                                                             │ │
│ │                                                             │ │
│ │                                                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Match Results                          [Export CSV] [Copy]  │ │
│ │─────────────────────────────────────────────────────────────│ │
│ │ # │ File │ Page │ Elements...                               │ │
│ │───┼──────┼──────┼───────────────────────────────────────────│ │
│ │   │      │      │                                           │ │
│ │   │  (Results appear here after query)                      │ │
│ │   │      │      │                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Vectors: [●] Circle  [■] Rectangle  [▲] Polygon  [/] Line      │
│          [Show All] [Clear Vectors]                             │
└─────────────────────────────────────────────────────────────────┘
```

### 7.4 Visual Feedback

When `SELECT` command executes:

1. **Console**: Shows result count and table
2. **Canvas (#hi)**: Highlights matched element groups with distinct colors
3. **Canvas (#sel)**: Shows vectors used in query
4. **Table (Text Extraction tab)**: Sets `keep=true` for matched elements

Match group colors cycle through:
- Group 1: `rgba(255, 100, 100, 0.3)` (red)
- Group 2: `rgba(100, 255, 100, 0.3)` (green)
- Group 3: `rgba(100, 100, 255, 0.3)` (blue)
- Group 4+: Cycles through palette

### 7.5 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+P` | Focus Pattern Matches tab and console |
| `Ctrl+Enter` | Execute query in console |
| `Escape` | Clear selection, close console focus |
| `Ctrl+L` | Clear console |
| `Ctrl+Shift+E` | Export pattern results as CSV |

---

## 8. Implementation Phases

### Phase 1: Core Infrastructure (Foundation)

**Deliverables:**
- DuckDB WASM integration
- Elements table schema and sync
- Basic custom functions (spatial_above, spatial_below, etc.)
- Console UI skeleton

**Tasks:**
1. Add DuckDB WASM to dependencies
2. Initialize DuckDB instance on app load
3. Create `elements` table DDL
4. Implement `syncElements()` function (called on PDF load)
5. Register custom spatial functions
6. Add console HTML/CSS to right panel
7. Basic REPL command parsing (SQL passthrough)

### Phase 2: DSL Parser and Compiler

**Deliverables:**
- Complete DSL parser
- SQL code generator
- EXPLAIN command
- Error reporting with positions

**Tasks:**
1. Implement tokenizer for DSL grammar
2. Build recursive descent parser
3. AST node types for patterns, conditions, operators
4. SQL code generator from AST
5. LIST/SELECT command differentiation
6. Parse error messages with caret position
7. EXPLAIN command to show generated SQL

### Phase 3: Vector Support

**Deliverables:**
- Vectors table schema
- N-gon to circle resolution
- IN CIRCLE/LINE/RECTANGLE/POLYGON operators
- Vector naming and references

**Tasks:**
1. Create `vectors` table DDL
2. Hook into existing polygon/rectangle drawing code
3. Implement n-gon detection and circle resolution
4. Register `in_circle`, `in_polygon`, `above_line`, `below_line` UDFs
5. Extend DSL parser for vector references
6. Implement NAME command
7. SHOW VECTORS command

### Phase 4: UI Polish and Integration

**Deliverables:**
- Tabbed interface
- Visual selection feedback
- Result navigation
- Export functionality

**Tasks:**
1. Implement tab switching UI
2. SELECT command canvas integration
3. GOTO command for result navigation
4. Result table with export
5. Syntax highlighting for console
6. Auto-complete suggestions
7. Command history (localStorage)

### Phase 5: Advanced Features

**Deliverables:**
- Tolerance configuration
- Performance optimization
- Saved patterns
- Pattern templates

**Tasks:**
1. SET TOLERANCE command
2. Query result caching
3. Saved pattern management (localStorage)
4. Pre-built pattern templates
5. Performance profiling and optimization
6. Documentation and examples

---

## Appendix A: DuckDB WASM Integration

### A.1 Loading DuckDB

```html
<script type="module">
import * as duckdb from 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.28.0/+esm';

const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();

async function initDuckDB() {
    const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);
    const worker_url = URL.createObjectURL(
        new Blob([`importScripts("${bundle.mainWorker}");`],
                 {type: 'text/javascript'})
    );
    const worker = new Worker(worker_url);
    const logger = new duckdb.ConsoleLogger();
    const db = new duckdb.AsyncDuckDB(logger, worker);
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
    URL.revokeObjectURL(worker_url);
    return db;
}
</script>
```

### A.2 Registering Custom Functions

```javascript
async function registerSpatialFunctions(conn) {
    // spatial_above
    await conn.createScalarFunction(
        'spatial_above',
        (a_x1, a_y1, a_x2, a_y2, b_x1, b_y1, b_x2, b_y2) => {
            return a_y2 <= b_y1 && a_x2 > b_x1 && a_x1 < b_x2;
        },
        'BOOLEAN',
        ['DOUBLE', 'DOUBLE', 'DOUBLE', 'DOUBLE',
         'DOUBLE', 'DOUBLE', 'DOUBLE', 'DOUBLE']
    );

    // ... register other functions
}
```

---

## Appendix B: Error Messages

| Error Code | Message | Resolution |
|------------|---------|------------|
| `E001` | Unknown identifier: X | Define X in WITH clause |
| `E002` | Invalid spatial operator | Use: ABOVE, BELOW, LEFT OF, RIGHT OF, etc. |
| `E003` | Regex syntax error | Check regex pattern syntax |
| `E004` | Vector not found: NAME | Draw vector or use valid name |
| `E005` | No elements loaded | Load a PDF file first |
| `E006` | Ambiguous vector reference | Multiple vectors of type; use NAME |

---

## Appendix C: Performance Considerations

1. **Indexing**: Spatial indices on (file_id, page, x1, y1) enable efficient range queries
2. **Join optimization**: DuckDB automatically optimizes multi-way joins
3. **Result limits**: Default LIMIT 1000 on queries (configurable via SET)
4. **Lazy loading**: Vectors table populated on-demand per page
5. **Caching**: Recent query results cached for GOTO navigation

---

*End of Specification*
