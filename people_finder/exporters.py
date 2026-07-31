from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from textwrap import wrap

from .models import PERSON_FIELDS, PersonRecord


EXPORT_FIELDS = ["id", *PERSON_FIELDS, "collected_at"]


def export_csv_text(records: list[PersonRecord]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow(record.as_dict())
    return output.getvalue()


def export_csv_file(records: list[PersonRecord], output_path: str | Path) -> None:
    Path(output_path).write_text(export_csv_text(records), encoding="utf-8", newline="")


def export_pdf_bytes(records: list[PersonRecord], title: str = "People Finder Export") -> bytes:
    lines = [title, ""]
    if not records:
        lines.append("No records found.")
    for index, record in enumerate(records, start=1):
        lines.extend(
            [
                f"{index}. {record.name}",
                f"   Role: {record.role or '-'}",
                f"   Organization: {record.organization or '-'}",
                f"   Location: {', '.join(part for part in [record.city, record.country] if part) or '-'}",
                f"   Email: {record.email or '-'}",
                f"   Phone: {record.phone or '-'}",
                f"   Profile: {record.profile_url or '-'}",
                f"   Source: {record.source or '-'}",
                f"   Tags: {record.tags or '-'}",
                f"   Consent / lawful basis: {record.consent_basis or '-'}",
            ]
        )
        for note_line in wrap(record.notes or "-", width=88):
            lines.append(f"   Notes: {note_line}" if note_line == (record.notes or "-")[: len(note_line)] else f"          {note_line}")
        lines.append("")
    return _simple_pdf(lines)


def export_pdf_file(records: list[PersonRecord], output_path: str | Path, title: str = "People Finder Export") -> None:
    Path(output_path).write_bytes(export_pdf_bytes(records, title=title))


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _simple_pdf(lines: list[str]) -> bytes:
    """Create a small text PDF without third-party dependencies."""

    page_width = 612
    page_height = 792
    margin_left = 54
    start_y = 738
    line_height = 14
    max_lines_per_page = 48

    pages: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        for wrapped in wrap(line, width=94) or [""]:
            current.append(wrapped)
            if len(current) >= max_lines_per_page:
                pages.append(current)
                current = []
    if current:
        pages.append(current)

    objects: list[bytes] = []

    def add_object(payload: str | bytes) -> int:
        if isinstance(payload, str):
            payload = payload.encode("latin-1", errors="replace")
        objects.append(payload)
        return len(objects)

    catalog_id = add_object(b"")
    pages_id = add_object(b"")
    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []

    for page_lines in pages or [["No records found."]]:
        text_ops = ["BT", f"/F1 10 Tf", f"{margin_left} {start_y} Td"]
        for line_index, line in enumerate(page_lines):
            if line_index:
                text_ops.append(f"0 -{line_height} Td")
            text_ops.append(f"({_escape_pdf_text(line)}) Tj")
        text_ops.append("ET")
        stream = "\n".join(text_ops).encode("latin-1", errors="replace")
        content_id = add_object(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        )
        page_id = add_object(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, payload in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
        pdf.extend(payload)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(pdf)
