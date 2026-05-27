from __future__ import annotations

import html
import math
import textwrap
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.exceptions import ReportNotFoundError
from app.models.report import Report
from app.repositories.report_repository import ReportRepository
from app.schemas.analytics import CaptureAnalytics
from app.services.capture_analytics_service import CaptureAnalyticsService


class ReportService:
    def __init__(self, reports: ReportRepository, analytics: CaptureAnalyticsService, reports_dir: Path):
        self.reports = reports
        self.analytics = analytics
        self.reports_dir = reports_dir

    async def list(self, *, limit: int = 50, offset: int = 0) -> tuple[list[Report], int]:
        return await self.reports.list(limit=limit, offset=offset)

    async def get(self, report_id: uuid.UUID) -> Report:
        report = await self.reports.get(report_id)
        if report is None:
            raise ReportNotFoundError()
        return report

    async def create(self, *, capture_id: uuid.UUID, format: str = "pdf") -> Report:
        analytics = await self.analytics.build(capture_id)
        report_dir = self.reports_dir / str(capture_id)
        report_dir.mkdir(parents=True, exist_ok=True)
        filename = f"report_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.{format}"
        path = report_dir / filename

        html_content = self._render_html(analytics)
        if format == "html":
            path.write_text(html_content, encoding="utf-8")
        else:
            path.write_bytes(self._render_pdf_bytes(analytics))

        return await self.reports.create(session_id=capture_id, file_path=str(path), format=format)

    def download_path(self, report: Report) -> Path:
        path = Path(report.file_path)
        if not path.exists():
            raise ReportNotFoundError("Report file not found")
        return path

    def _render_html(self, analytics: CaptureAnalytics) -> str:
        capture = analytics.capture
        generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        rows = "\n".join(
            "<tr>"
            f"<td>{html.escape(str(flow.flow_timestamp or '-'))}</td>"
            f"<td>{html.escape(str(flow.src_ip or '-'))}:{flow.src_port or '-'} -> "
            f"{html.escape(str(flow.dst_ip or '-'))}:{flow.dst_port or '-'}</td>"
            f"<td>{flow.protocol or '-'}</td>"
            f"<td>{flow.anomaly_score:.4f}</td>"
            f"<td>{'ANOMALY' if flow.prediction == 1 else 'BENIGN'}</td>"
            "</tr>"
            for flow in analytics.recent_flows[:30]
        )
        score_rows = "\n".join(
            "<tr>"
            f"<td>{bucket.min_score:.3f} - {bucket.max_score:.3f}</td>"
            f"<td>{bucket.count}</td>"
            f"<td><div class=\"bar\"><span style=\"width:{self._percent(bucket.count, analytics.summary.total_flows):.1f}%\"></span></div></td>"
            "</tr>"
            for bucket in analytics.score_distribution
        )
        top_sources = "".join(f"<li><span>{html.escape(item.value)}</span><b>{item.count}</b></li>" for item in analytics.top_sources[:10])
        top_destinations = "".join(f"<li><span>{html.escape(item.value)}</span><b>{item.count}</b></li>" for item in analytics.top_destinations[:10])
        return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <title>ML-NIDS Report</title>
  <style>
    :root {{ --ink:#17202a; --muted:#64748b; --line:#d9dee7; --panel:#f4f7fb; --accent:#0f766e; --danger:#b91c1c; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, sans-serif; color: var(--ink); margin: 0; background: #eef2f6; }}
    main {{ max-width: 1080px; margin: 0 auto; background: #fff; min-height: 100vh; padding: 34px; }}
    header {{ display: flex; justify-content: space-between; gap: 24px; border-bottom: 3px solid var(--accent); padding-bottom: 18px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin: 26px 0 10px; font-size: 18px; }}
    .muted {{ color: var(--muted); font-size: 12px; line-height: 1.45; }}
    .badge {{ display: inline-block; border-radius: 999px; background: #ccfbf1; color: #134e4a; padding: 4px 10px; font-size: 12px; font-weight: 700; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 20px; }}
    .card {{ border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: var(--panel); }}
    .label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
    .value {{ margin-top: 6px; font-size: 22px; font-weight: 700; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
    th, td {{ border: 1px solid var(--line); padding: 8px 10px; font-size: 12px; vertical-align: top; }}
    th {{ background: var(--panel); text-align: left; color: var(--muted); text-transform: uppercase; font-size: 11px; }}
    .split {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
    ul.rank {{ list-style: none; padding: 0; margin: 0; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
    ul.rank li {{ display: flex; justify-content: space-between; gap: 10px; padding: 8px 10px; border-bottom: 1px solid var(--line); font-size: 12px; }}
    ul.rank li:last-child {{ border-bottom: 0; }}
    .bar {{ height: 8px; background: #e2e8f0; border-radius: 999px; overflow: hidden; }}
    .bar span {{ display: block; height: 100%; background: var(--accent); }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>ML-NIDS Capture Report</h1>
      <div class="muted">Session: {html.escape(str(capture.id))}</div>
      <div class="muted">Name: {html.escape(str(capture.name or capture.source_filename or '-'))}</div>
    </div>
    <div>
      <span class="badge">{html.escape(capture.status.upper())}</span>
      <div class="muted" style="margin-top:10px">Mode: {html.escape(capture.mode)}</div>
      <div class="muted">Generated: {generated_at}</div>
    </div>
  </header>
  <div class="grid">
    <div class="card"><div class="label">Total flows</div><div class="value">{analytics.summary.total_flows}</div></div>
    <div class="card"><div class="label">Anomalies</div><div class="value">{analytics.summary.anomaly_flows}</div></div>
    <div class="card"><div class="label">Anomaly rate</div><div class="value">{analytics.summary.anomaly_rate:.2f}%</div></div>
    <div class="card"><div class="label">Stored flows</div><div class="value">{len(analytics.recent_flows)}</div></div>
  </div>
  <div class="split">
    <section>
      <h2>Top sources</h2>
      <ul class="rank">{top_sources or "<li><span>-</span><b>0</b></li>"}</ul>
    </section>
    <section>
      <h2>Top destinations</h2>
      <ul class="rank">{top_destinations or "<li><span>-</span><b>0</b></li>"}</ul>
    </section>
  </div>
  <h2>Score distribution</h2>
  <table>
    <thead><tr><th>Score range</th><th>Flows</th><th>Share</th></tr></thead>
    <tbody>{score_rows}</tbody>
  </table>
  <h2>Recent anomaly flows</h2>
  <table>
    <thead><tr><th>Timestamp</th><th>Endpoint</th><th>Protocol</th><th>Score</th><th>Prediction</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</main>
</body>
</html>
"""

    def _render_pdf_bytes(self, analytics: CaptureAnalytics) -> bytes:
        pdf = _PdfDocument()
        self._render_pdf_cover(pdf, analytics)
        self._render_pdf_details(pdf, analytics)
        return pdf.to_bytes()

    def _render_pdf_cover(self, pdf: "_PdfDocument", analytics: CaptureAnalytics) -> None:
        capture = analytics.capture
        page = pdf.add_page()
        page.rect(0, 0, 595, 842, fill=(248, 250, 252))
        page.rect(0, 0, 595, 92, fill=(15, 118, 110))
        page.text(42, 790, "ML-NIDS Capture Report", size=24, color=(255, 255, 255), bold=True)
        page.text(42, 765, "Network anomaly detection summary", size=11, color=(204, 251, 241))
        page.text(430, 790, datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"), size=10, color=(255, 255, 255))

        y = 710
        page.text(42, y, "Capture", size=15, bold=True)
        y -= 24
        for label, value in [
            ("Session ID", str(capture.id)),
            ("Name", str(capture.name or capture.source_filename or "-")),
            ("Mode", capture.mode),
            ("Status", capture.status.upper()),
            ("Started", self._format_dt(capture.started_at)),
            ("Finished", self._format_dt(capture.finished_at)),
        ]:
            page.text(48, y, label, size=9, color=(100, 116, 139))
            page.text(150, y, value, size=9)
            y -= 17

        self._metric_card(page, 42, 475, "Total flows", str(analytics.summary.total_flows), (14, 116, 144))
        self._metric_card(page, 198, 475, "Anomalies", str(analytics.summary.anomaly_flows), (185, 28, 28))
        self._metric_card(page, 354, 475, "Anomaly rate", f"{analytics.summary.anomaly_rate:.2f}%", (15, 118, 110))

        page.text(42, 410, "Top sources", size=14, bold=True)
        self._rank_list(page, 42, 388, analytics.top_sources[:8])
        page.text(314, 410, "Top destinations", size=14, bold=True)
        self._rank_list(page, 314, 388, analytics.top_destinations[:8])

        page.text(42, 210, "Score distribution", size=14, bold=True)
        self._score_distribution(page, 42, 188, analytics)

    def _render_pdf_details(self, pdf: "_PdfDocument", analytics: CaptureAnalytics) -> None:
        page = pdf.add_page()
        page.text(42, 790, "Recent anomaly flows", size=18, bold=True, color=(15, 118, 110))
        y = 758
        headers = ["Endpoint", "Proto", "Score", "Prediction"]
        widths = [315, 55, 65, 80]
        self._table_row(page, 42, y, headers, widths, header=True)
        y -= 24
        for flow in analytics.recent_flows[:25]:
            endpoint = f"{flow.src_ip or '-'}:{flow.src_port or '-'} -> {flow.dst_ip or '-'}:{flow.dst_port or '-'}"
            row = [
                endpoint,
                str(flow.protocol or "-"),
                f"{flow.anomaly_score:.4f}",
                "ANOMALY" if flow.prediction == 1 else "BENIGN",
            ]
            self._table_row(page, 42, y, row, widths)
            y -= 22
            if y < 80:
                page = pdf.add_page()
                page.text(42, 790, "Recent anomaly flows", size=18, bold=True, color=(15, 118, 110))
                y = 758
                self._table_row(page, 42, y, headers, widths, header=True)
                y -= 24

        if not analytics.recent_flows:
            page.text(42, y, "No anomaly flow samples are stored for this capture.", size=10, color=(100, 116, 139))

    def _metric_card(self, page: "_PdfPage", x: float, y: float, label: str, value: str, color: tuple[int, int, int]) -> None:
        page.rect(x, y, 132, 78, fill=(255, 255, 255), stroke=(217, 222, 231))
        page.text(x + 12, y + 52, label.upper(), size=8, color=(100, 116, 139))
        page.text(x + 12, y + 24, value, size=20, color=color, bold=True)

    def _rank_list(self, page: "_PdfPage", x: float, y: float, items: list[Any]) -> None:
        max_count = max([item.count for item in items], default=1)
        for index, item in enumerate(items):
            row_y = y - index * 20
            page.text(x, row_y, self._truncate(item.value, 28), size=9)
            page.text(x + 178, row_y, str(item.count), size=9, color=(100, 116, 139))
            page.rect(x, row_y - 8, 220 * (item.count / max_count), 3, fill=(15, 118, 110))
        if not items:
            page.text(x, y, "-", size=9, color=(100, 116, 139))

    def _score_distribution(self, page: "_PdfPage", x: float, y: float, analytics: CaptureAnalytics) -> None:
        total = max(1, analytics.summary.total_flows)
        for index, bucket in enumerate(analytics.score_distribution[:8]):
            row_y = y - index * 17
            label = f"{bucket.min_score:.2f}-{bucket.max_score:.2f}"
            width = 300 * (bucket.count / total)
            page.text(x, row_y, label, size=8, color=(100, 116, 139))
            page.rect(x + 70, row_y - 6, max(1, width), 8, fill=(15, 118, 110))
            page.text(x + 385, row_y, str(bucket.count), size=8)

    def _table_row(self, page: "_PdfPage", x: float, y: float, cells: list[str], widths: list[int], *, header: bool = False) -> None:
        fill = (241, 245, 249) if header else (255, 255, 255)
        page.rect(x, y - 14, sum(widths), 20, fill=fill, stroke=(217, 222, 231))
        current_x = x
        for cell, width in zip(cells, widths, strict=False):
            page.text(current_x + 5, y - 8, self._truncate(str(cell), max(8, math.floor(width / 5.3))), size=8, bold=header)
            current_x += width

    def _format_dt(self, value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.strftime("%Y-%m-%d %H:%M:%S %Z")

    def _truncate(self, value: str, limit: int) -> str:
        return value if len(value) <= limit else f"{value[: max(0, limit - 1)]}..."

    def _percent(self, value: int, total: int) -> float:
        return 0.0 if total <= 0 else min(100.0, (value / total) * 100)


class _PdfDocument:
    def __init__(self):
        self.pages: list[_PdfPage] = []

    def add_page(self) -> "_PdfPage":
        page = _PdfPage()
        self.pages.append(page)
        return page

    def to_bytes(self) -> bytes:
        font_regular_id = 3 + len(self.pages) * 2
        font_bold_id = font_regular_id + 1
        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"",
        ]
        page_ids = []
        for index, page in enumerate(self.pages):
            page_id = 3 + index * 2
            content_id = page_id + 1
            page_ids.append(page_id)
            stream = page.stream().encode("latin-1", errors="replace")
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>".encode("ascii")
            )
            objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
        objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>".encode("ascii")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        return _pdf_objects_to_bytes(objects)


class _PdfPage:
    def __init__(self):
        self.ops: list[str] = []

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: int = 10,
        color: tuple[int, int, int] = (23, 32, 42),
        bold: bool = False,
    ) -> None:
        font = "F2" if bold else "F1"
        self.ops.append(f"{_rgb(color)} rg")
        for offset, line in enumerate(textwrap.wrap(value, width=95) or [""]):
            self.ops.append(f"BT /{font} {size} Tf {x:.1f} {y - offset * (size + 3):.1f} Td ({_pdf_escape(line)}) Tj ET")

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill: tuple[int, int, int] | None = None,
        stroke: tuple[int, int, int] | None = None,
    ) -> None:
        if fill:
            self.ops.append(f"{_rgb(fill)} rg {x:.1f} {y:.1f} {width:.1f} {height:.1f} re f")
        if stroke:
            self.ops.append(f"{_rgb(stroke)} RG {x:.1f} {y:.1f} {width:.1f} {height:.1f} re S")

    def stream(self) -> str:
        return "\n".join(self.ops)


def _pdf_objects_to_bytes(objects: list[bytes]) -> bytes:
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def _rgb(color: tuple[int, int, int]) -> str:
    return " ".join(f"{channel / 255:.3f}" for channel in color)


def _pdf_escape(value: str) -> str:
    return value.encode("latin-1", errors="replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
