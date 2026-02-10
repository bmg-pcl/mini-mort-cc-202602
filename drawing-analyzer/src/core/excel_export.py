"""
Excel Export with Formatting

Exports analysis results to properly formatted Excel files using openpyxl.
"""
from io import BytesIO
from pathlib import Path
from typing import Any

from .schema import AnalysisResult, QuantityItem, Measurement, NoteExtraction


def export_to_excel(result: AnalysisResult, output_path: Path | None = None) -> bytes:
    """
    Export analysis results to a formatted Excel file.

    Args:
        result: The analysis result to export
        output_path: Optional path to save the file (if None, returns bytes)

    Returns:
        Excel file as bytes
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import (
            Font,
            PatternFill,
            Alignment,
            Border,
            Side,
            NamedStyle,
        )
        from openpyxl.utils import get_column_letter
        from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
        from openpyxl.chart import PieChart, Reference
    except ImportError:
        raise ImportError("openpyxl is required for Excel export. Install with: pip install openpyxl")

    wb = Workbook()

    # Define styles
    header_style = NamedStyle(name="header")
    header_style.font = Font(bold=True, color="FFFFFF")
    header_style.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_style.alignment = Alignment(horizontal="center", vertical="center")
    header_style.border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    confidence_high = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    confidence_medium = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    confidence_low = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    # ===== Summary Sheet =====
    ws_summary = wb.active
    ws_summary.title = "Summary"

    # Title
    ws_summary["A1"] = "Drawing Analysis Report"
    ws_summary["A1"].font = Font(size=16, bold=True)
    ws_summary.merge_cells("A1:D1")

    # Source info
    ws_summary["A3"] = "Source File:"
    ws_summary["B3"] = result.source_file
    ws_summary["A4"] = "Analysis Date:"
    ws_summary["B4"] = result.analysis_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    # Classification
    ws_summary["A6"] = "Classification"
    ws_summary["A6"].font = Font(bold=True)
    ws_summary["A7"] = "Drawing Type:"
    ws_summary["B7"] = result.classification.drawing_type
    ws_summary["A8"] = "Discipline:"
    ws_summary["B8"] = result.classification.discipline
    ws_summary["A9"] = "Confidence:"
    ws_summary["B9"] = f"{result.classification.confidence:.1%}"

    # Statistics
    ws_summary["A11"] = "Statistics"
    ws_summary["A11"].font = Font(bold=True)
    ws_summary["A12"] = "Total Elements:"
    ws_summary["B12"] = result.total_elements
    ws_summary["A13"] = "Total Quantities:"
    ws_summary["B13"] = result.total_quantities
    ws_summary["A14"] = "Average Confidence:"
    ws_summary["B14"] = f"{result.average_confidence:.1%}"
    ws_summary["A15"] = "Items Needing Review:"
    ws_summary["B15"] = result.requires_review_count

    # Metadata
    if result.metadata.drawing_number:
        ws_summary["A17"] = "Drawing Metadata"
        ws_summary["A17"].font = Font(bold=True)
        ws_summary["A18"] = "Drawing Number:"
        ws_summary["B18"] = result.metadata.drawing_number
        if result.metadata.revision:
            ws_summary["A19"] = "Revision:"
            ws_summary["B19"] = result.metadata.revision
        if result.metadata.scale:
            ws_summary["A20"] = "Scale:"
            ws_summary["B20"] = result.metadata.scale

    # Adjust column widths
    ws_summary.column_dimensions["A"].width = 20
    ws_summary.column_dimensions["B"].width = 40

    # ===== Quantities Sheet =====
    ws_quantities = wb.create_sheet("Quantities")

    # Headers
    headers = [
        "ID", "Description", "Quantity", "Unit",
        "Category L1", "Category L2", "Category L3", "Category L4",
        "CSI Division", "UniFormat",
        "Source Drawing", "Source Page",
        "Confidence", "Status", "Notes"
    ]
    for col, header in enumerate(headers, 1):
        cell = ws_quantities.cell(row=1, column=col, value=header)
        cell.style = header_style

    # Data
    for row, q in enumerate(result.quantities, 2):
        ws_quantities.cell(row=row, column=1, value=q.id)
        ws_quantities.cell(row=row, column=2, value=q.description)
        ws_quantities.cell(row=row, column=3, value=q.quantity)
        ws_quantities.cell(row=row, column=4, value=q.unit.value)
        ws_quantities.cell(row=row, column=5, value=q.category.level1)
        ws_quantities.cell(row=row, column=6, value=q.category.level2 or "")
        ws_quantities.cell(row=row, column=7, value=q.category.level3 or "")
        ws_quantities.cell(row=row, column=8, value=q.category.level4 or "")
        ws_quantities.cell(row=row, column=9, value=q.category.csi_division or "")
        ws_quantities.cell(row=row, column=10, value=q.category.uniformat or "")
        ws_quantities.cell(row=row, column=11, value=q.source_drawing)
        ws_quantities.cell(row=row, column=12, value=q.source_page)

        # Confidence with conditional formatting
        conf_cell = ws_quantities.cell(row=row, column=13, value=q.confidence)
        conf_cell.number_format = "0%"
        if q.confidence >= 0.8:
            conf_cell.fill = confidence_high
        elif q.confidence >= 0.5:
            conf_cell.fill = confidence_medium
        else:
            conf_cell.fill = confidence_low

        ws_quantities.cell(row=row, column=14, value=q.verification_status.value)
        ws_quantities.cell(row=row, column=15, value="; ".join(q.notes))

    # Auto-fit columns
    for col in range(1, len(headers) + 1):
        ws_quantities.column_dimensions[get_column_letter(col)].width = 15
    ws_quantities.column_dimensions["B"].width = 40  # Description
    ws_quantities.column_dimensions["O"].width = 30  # Notes

    # Freeze header row
    ws_quantities.freeze_panes = "A2"

    # Add filter
    ws_quantities.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(result.quantities) + 1}"

    # ===== Measurements Sheet =====
    ws_measurements = wb.create_sheet("Measurements")

    headers = ["ID", "Value", "Unit", "Label", "Confidence", "Related Elements"]
    for col, header in enumerate(headers, 1):
        cell = ws_measurements.cell(row=1, column=col, value=header)
        cell.style = header_style

    for row, m in enumerate(result.measurements, 2):
        ws_measurements.cell(row=row, column=1, value=m.id)
        ws_measurements.cell(row=row, column=2, value=m.value)
        ws_measurements.cell(row=row, column=3, value=m.unit.value)
        ws_measurements.cell(row=row, column=4, value=m.label or "")

        conf_cell = ws_measurements.cell(row=row, column=5, value=m.confidence)
        conf_cell.number_format = "0%"
        if m.confidence >= 0.8:
            conf_cell.fill = confidence_high
        elif m.confidence >= 0.5:
            conf_cell.fill = confidence_medium
        else:
            conf_cell.fill = confidence_low

        ws_measurements.cell(row=row, column=6, value=", ".join(m.related_elements))

    ws_measurements.freeze_panes = "A2"

    # ===== Notes Sheet =====
    ws_notes = wb.create_sheet("Notes")

    headers = ["ID", "Type", "Content", "Tags"]
    for col, header in enumerate(headers, 1):
        cell = ws_notes.cell(row=1, column=col, value=header)
        cell.style = header_style

    for row, n in enumerate(result.notes, 2):
        ws_notes.cell(row=row, column=1, value=n.id)
        ws_notes.cell(row=row, column=2, value=n.note_type)
        ws_notes.cell(row=row, column=3, value=n.content)
        ws_notes.cell(row=row, column=4, value=", ".join(n.tags))

    ws_notes.column_dimensions["C"].width = 60
    ws_notes.freeze_panes = "A2"

    # ===== Callouts Sheet =====
    ws_callouts = wb.create_sheet("Callouts")

    headers = ["ID", "Callout ID", "Description", "Target Drawing", "Target Detail"]
    for col, header in enumerate(headers, 1):
        cell = ws_callouts.cell(row=1, column=col, value=header)
        cell.style = header_style

    for row, c in enumerate(result.callouts, 2):
        ws_callouts.cell(row=row, column=1, value=c.id)
        ws_callouts.cell(row=row, column=2, value=c.callout_id)
        ws_callouts.cell(row=row, column=3, value=c.description or "")
        ws_callouts.cell(row=row, column=4, value=c.target_drawing or "")
        ws_callouts.cell(row=row, column=5, value=c.target_detail or "")

    ws_callouts.freeze_panes = "A2"

    # ===== Category Summary Sheet =====
    if result.quantities:
        ws_category = wb.create_sheet("Category Summary")

        # Group quantities by category
        category_totals: dict[str, dict] = {}
        for q in result.quantities:
            cat = q.category.level1
            if cat not in category_totals:
                category_totals[cat] = {"count": 0, "items": []}
            category_totals[cat]["count"] += 1
            category_totals[cat]["items"].append(q)

        headers = ["Category", "Item Count", "Total Quantity", "Avg Confidence"]
        for col, header in enumerate(headers, 1):
            cell = ws_category.cell(row=1, column=col, value=header)
            cell.style = header_style

        for row, (cat, data) in enumerate(sorted(category_totals.items()), 2):
            ws_category.cell(row=row, column=1, value=cat)
            ws_category.cell(row=row, column=2, value=data["count"])
            ws_category.cell(row=row, column=3, value=sum(i.quantity for i in data["items"]))
            avg_conf = sum(i.confidence for i in data["items"]) / len(data["items"])
            conf_cell = ws_category.cell(row=row, column=4, value=avg_conf)
            conf_cell.number_format = "0%"

        ws_category.freeze_panes = "A2"

    # Save
    buffer = BytesIO()
    wb.save(buffer)
    excel_bytes = buffer.getvalue()

    if output_path:
        Path(output_path).write_bytes(excel_bytes)

    return excel_bytes


def export_comparison_to_excel(
    prev_result: AnalysisResult,
    curr_result: AnalysisResult,
    output_path: Path | None = None,
) -> bytes:
    """
    Export a comparison of two analysis results to Excel.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise ImportError("openpyxl is required for Excel export")

    wb = Workbook()
    ws = wb.active
    ws.title = "Comparison"

    # Styles
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    added_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    removed_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    changed_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")

    # Build lookup maps
    prev_map = {q.description: q for q in prev_result.quantities}
    curr_map = {q.description: q for q in curr_result.quantities}

    # Headers
    headers = ["Status", "Description", "Previous Qty", "Current Qty", "Difference", "Unit", "Category"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill

    row = 2

    # Added items
    for desc, curr in curr_map.items():
        if desc not in prev_map:
            ws.cell(row=row, column=1, value="ADDED").fill = added_fill
            ws.cell(row=row, column=2, value=desc)
            ws.cell(row=row, column=3, value="-")
            ws.cell(row=row, column=4, value=curr.quantity)
            ws.cell(row=row, column=5, value=f"+{curr.quantity}")
            ws.cell(row=row, column=6, value=curr.unit.value)
            ws.cell(row=row, column=7, value=curr.category.level1)
            for col in range(1, 8):
                ws.cell(row=row, column=col).fill = added_fill
            row += 1

    # Removed items
    for desc, prev in prev_map.items():
        if desc not in curr_map:
            ws.cell(row=row, column=1, value="REMOVED").fill = removed_fill
            ws.cell(row=row, column=2, value=desc)
            ws.cell(row=row, column=3, value=prev.quantity)
            ws.cell(row=row, column=4, value="-")
            ws.cell(row=row, column=5, value=f"-{prev.quantity}")
            ws.cell(row=row, column=6, value=prev.unit.value)
            ws.cell(row=row, column=7, value=prev.category.level1)
            for col in range(1, 8):
                ws.cell(row=row, column=col).fill = removed_fill
            row += 1

    # Changed items
    for desc, curr in curr_map.items():
        if desc in prev_map:
            prev = prev_map[desc]
            if prev.quantity != curr.quantity:
                diff = curr.quantity - prev.quantity
                ws.cell(row=row, column=1, value="CHANGED").fill = changed_fill
                ws.cell(row=row, column=2, value=desc)
                ws.cell(row=row, column=3, value=prev.quantity)
                ws.cell(row=row, column=4, value=curr.quantity)
                ws.cell(row=row, column=5, value=f"{'+' if diff > 0 else ''}{diff}")
                ws.cell(row=row, column=6, value=curr.unit.value)
                ws.cell(row=row, column=7, value=curr.category.level1)
                for col in range(1, 8):
                    ws.cell(row=row, column=col).fill = changed_fill
                row += 1

    # Adjust column widths
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 10
    ws.column_dimensions["G"].width = 15

    ws.freeze_panes = "A2"

    buffer = BytesIO()
    wb.save(buffer)
    excel_bytes = buffer.getvalue()

    if output_path:
        Path(output_path).write_bytes(excel_bytes)

    return excel_bytes
