"""
Export service for generating Release Evidence Packs.

Produces:
  - PDF summary (ReportLab)
  - CSV of all test cases
  - Signed approval log
  - ZIP bundle of all artefacts
"""
import csv
import io
import zipfile
import json
from datetime import datetime
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import structlog

logger = structlog.get_logger()


def generate_pdf_summary(
    project_name: str,
    release_name: str,
    environment: str,
    test_plan_name: str,
    plan_id: str,
    scope: Optional[str],
    test_strategy: Optional[str],
    test_cases: list,
    signoffs: list,
    evidence_completeness: float,
    created_by: str,
    created_at: datetime,
    export_timestamp: datetime = None,
) -> bytes:
    """Generate PDF evidence report and return as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    story = []

    # Header
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=12,
        textColor=colors.HexColor("#1a365d"),
    )
    header_style = ParagraphStyle(
        "Header",
        parent=styles["Heading1"],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor("#2b6cb0"),
    )
    body_style = styles["Normal"]
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
    )

    story.append(Paragraph("Unit Test Artefact Portal (UTAP)", title_style))
    story.append(Paragraph("Release Evidence Pack", header_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2b6cb0")))
    story.append(Spacer(1, 0.5 * cm))

    # Summary table
    summary_data = [
        ["Field", "Value"],
        ["Project", project_name],
        ["Release", release_name],
        ["Environment", environment],
        ["Test Plan", test_plan_name],
        ["Plan ID", plan_id],
        ["Evidence Completeness", f"{evidence_completeness:.1f}%"],
        ["Created By", created_by],
        ["Created At", created_at.strftime("%Y-%m-%d %H:%M UTC") if created_at else "—"],
        ["Export Timestamp", (export_timestamp or datetime.utcnow()).strftime("%Y-%m-%d %H:%M UTC")],
    ]
    summary_table = Table(summary_data, colWidths=[5 * cm, 12 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b6cb0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#ebf4ff")),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * cm))

    # Scope & Strategy
    if scope:
        story.append(Paragraph("Scope", header_style))
        story.append(Paragraph(scope, body_style))
        story.append(Spacer(1, 0.3 * cm))

    if test_strategy:
        story.append(Paragraph("Test Strategy", header_style))
        story.append(Paragraph(test_strategy, body_style))
        story.append(Spacer(1, 0.3 * cm))

    # Test Cases Summary
    story.append(Paragraph("Test Execution Summary", header_style))

    total = len(test_cases)
    passed = sum(1 for tc in test_cases if tc.get("status") == "PASS")
    failed = sum(1 for tc in test_cases if tc.get("status") == "FAIL")
    not_run = sum(1 for tc in test_cases if tc.get("status") == "NOT_RUN")
    blocked = sum(1 for tc in test_cases if tc.get("status") == "BLOCKED")
    waived = sum(1 for tc in test_cases if tc.get("status") == "WAIVED")

    metrics_data = [
        ["Total", "Pass", "Fail", "Not Run", "Blocked", "Waived", "Pass Rate"],
        [
            str(total), str(passed), str(failed), str(not_run),
            str(blocked), str(waived),
            f"{(passed / total * 100):.1f}%" if total > 0 else "N/A"
        ],
    ]
    metrics_table = Table(metrics_data, colWidths=[2.5 * cm] * 7)
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b6cb0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#c6f6d5")),
        ("BACKGROUND", (2, 1), (2, 1), colors.HexColor("#fed7d7")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.5 * cm))

    # Detailed test cases table
    story.append(Paragraph("Test Case Details", header_style))
    tc_header = ["TC ID", "Category", "Component", "Objective", "Status", "Executed By"]
    tc_data = [tc_header]
    for tc in test_cases:
        status = tc.get("status", "")
        status_colour = {
            "PASS": colors.HexColor("#c6f6d5"),
            "FAIL": colors.HexColor("#fed7d7"),
            "NOT_RUN": colors.HexColor("#e2e8f0"),
            "BLOCKED": colors.HexColor("#feebc8"),
            "WAIVED": colors.HexColor("#e9d8fd"),
        }.get(status, colors.white)
        tc_data.append([
            tc.get("testcase_id", ""),
            tc.get("category", ""),
            tc.get("component", ""),
            Paragraph(str(tc.get("objective", ""))[:120], ParagraphStyle("small", fontSize=7)),
            status,
            tc.get("executed_by", "—") or "—",
        ])

    tc_table = Table(tc_data, colWidths=[1.5*cm, 2.5*cm, 2.5*cm, 7*cm, 2*cm, 3*cm])
    tc_table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b6cb0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ]
    tc_table.setStyle(TableStyle(tc_table_style))
    story.append(tc_table)

    # Sign-off chain
    story.append(PageBreak())
    story.append(Paragraph("Approval Sign-off Chain", header_style))

    if signoffs:
        so_data = [["Level", "Decision", "Signed By", "Signed At", "Comments"]]
        for so in signoffs:
            so_data.append([
                so.get("level", ""),
                so.get("decision", "PENDING"),
                so.get("signed_by_name") or so.get("signed_by") or "—",
                so.get("signed_at", "—") or "—",
                Paragraph(str(so.get("comments") or ""), ParagraphStyle("small", fontSize=7)),
            ])
        so_table = Table(so_data, colWidths=[2.5*cm, 2.5*cm, 4*cm, 4*cm, 5.5*cm])
        so_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b6cb0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
        ]))
        story.append(so_table)
    else:
        story.append(Paragraph("No sign-off records found.", body_style))

    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Paragraph(
        f"Generated by UTAP | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | CONFIDENTIAL",
        small_style
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_test_cases_csv(test_cases: list) -> bytes:
    """Generate CSV export of all test cases."""
    output = io.StringIO()
    fieldnames = [
        "testcase_id", "category", "component", "objective", "preconditions",
        "test_steps", "expected_result", "actual_result", "status",
        "defect_reference", "executed_by", "executed_at",
        "snowflake_query_ids", "snowflake_warehouse", "snowflake_database_schema_object",
        "iics_org", "iics_asset_name", "iics_run_ids", "iics_run_status",
        "evidence_count",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for tc in test_cases:
        row = {k: tc.get(k, "") for k in fieldnames}
        if isinstance(row.get("snowflake_query_ids"), list):
            row["snowflake_query_ids"] = "|".join(row["snowflake_query_ids"])
        if isinstance(row.get("iics_run_ids"), list):
            row["iics_run_ids"] = "|".join(row["iics_run_ids"])
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def generate_signoff_log_csv(signoffs: list) -> bytes:
    """Generate CSV export of the sign-off chain."""
    output = io.StringIO()
    fieldnames = ["level", "decision", "signed_by", "signed_by_name", "signed_at", "comments", "rejection_reason"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for so in signoffs:
        writer.writerow({k: so.get(k, "") for k in fieldnames})
    return output.getvalue().encode("utf-8")


def create_evidence_zip(
    pdf_bytes: bytes,
    test_cases_csv: bytes,
    signoff_csv: bytes,
    metadata: dict,
) -> bytes:
    """Create a ZIP file containing all export artefacts."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        plan_id = metadata.get("plan_id", "export")

        zf.writestr(f"UTAP_{plan_id}_Summary_{timestamp}.pdf", pdf_bytes)
        zf.writestr(f"UTAP_{plan_id}_TestCases_{timestamp}.csv", test_cases_csv)
        zf.writestr(f"UTAP_{plan_id}_SignoffLog_{timestamp}.csv", signoff_csv)
        zf.writestr(f"UTAP_{plan_id}_Metadata_{timestamp}.json", json.dumps(metadata, default=str, indent=2))

    zip_bytes = zip_buffer.getvalue()
    zip_buffer.close()
    return zip_bytes
