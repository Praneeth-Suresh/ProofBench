from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from proofbench.logging.result_store import summarize


SUMMARY_COLUMNS = [
    "agent",
    "tasks",
    "solved_tasks",
    "success_rate",
    "proof_metric_coverage",
    "avg_proof_completion",
    "avg_verified_prefix_ratio",
    "avg_repairability_score",
    "avg_total_tokens",
    "avg_model_calls",
    "avg_tool_calls",
    "avg_total_elapsed_s",
]

ROW_COLUMNS = [
    "created_at",
    "agent",
    "task_id",
    "split",
    "proof_system",
    "model",
    "metric_validity",
    "solved",
    "success_score",
    "proof_completion",
    "verified_prefix_ratio",
    "repairability_score",
    "failure_profile",
    "model_calls",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "tool_calls",
    "agent_elapsed_s",
    "model_latency_s",
    "verification_elapsed_s",
    "total_elapsed_s",
    "verifier",
    "verifier_available",
]


def write_excel(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_rows = _summary_sheet_rows(rows)
    detail_rows = _detail_sheet_rows(rows)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types())
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("xl/workbook.xml", _workbook())
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels())
        archive.writestr("xl/styles.xml", _styles())
        archive.writestr("xl/worksheets/sheet1.xml", _worksheet(summary_rows))
        archive.writestr("xl/worksheets/sheet2.xml", _worksheet(detail_rows))
    return output_path


def _summary_sheet_rows(rows: list[dict]) -> list[list[object]]:
    summary = summarize(rows)
    sheet_rows: list[list[object]] = [SUMMARY_COLUMNS]
    for agent, values in sorted(summary.items()):
        sheet_rows.append([agent, *[values.get(column, "") for column in SUMMARY_COLUMNS[1:]]])
    return sheet_rows


def _detail_sheet_rows(rows: list[dict]) -> list[list[object]]:
    sheet_rows: list[list[object]] = [ROW_COLUMNS]
    for row in rows:
        efficiency = row.get("efficiency", {})
        speed = row.get("speed", {})
        verification = row.get("verification", {})
        sheet_rows.append(
            [
                row.get("created_at", ""),
                row.get("agent", ""),
                row.get("task_id", ""),
                row.get("split", ""),
                row.get("proof_system", ""),
                row.get("model", ""),
                row.get("metric_validity", ""),
                row.get("solved", ""),
                row.get("success_score", ""),
                row.get("proof_completion", ""),
                row.get("verified_prefix_ratio", ""),
                row.get("repairability_score", ""),
                row.get("failure_profile", ""),
                efficiency.get("model_calls", ""),
                efficiency.get("input_tokens", ""),
                efficiency.get("output_tokens", ""),
                efficiency.get("total_tokens", ""),
                efficiency.get("tool_calls", ""),
                speed.get("agent_elapsed_s", ""),
                speed.get("model_latency_s", ""),
                speed.get("verification_elapsed_s", ""),
                speed.get("total_elapsed_s", ""),
                verification.get("verifier", ""),
                verification.get("verifier_available", ""),
            ]
        )
    return sheet_rows


def _worksheet(rows: list[list[object]]) -> str:
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            ref = f"{_column_name(column_index)}{row_index}"
            cells.append(_cell(ref, value))
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        "</worksheet>"
    )


def _cell(ref: str, value: object) -> str:
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    text = _clean_text(value)
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'


def _clean_text(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _content_types() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""


def _root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _workbook() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Summary" sheetId="1" r:id="rId1"/>
    <sheet name="Rows" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""


def _workbook_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _styles() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>"""
