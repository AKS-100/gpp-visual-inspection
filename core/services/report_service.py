"""
Report service.

Builds the data structures four report types need, and exports them to
CSV/PDF under exports/. Export was deferred in Phase 5 pending stable
data structures — those structures haven't changed since, so export is
now safe to add without touching the report-building logic above it.
"""

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.services.dashboard_service import DashboardService, TrendPoint
from core.services.machine_service import MachineService

logger = logging.getLogger(__name__)

EXPORTS_DIR = Path("exports")


@dataclass(frozen=True)
class DailyProductionReport:
    report_date: str
    total_inspected: int
    accepted: int
    rejected: int
    acceptance_rate: float


@dataclass(frozen=True)
class InspectionSummaryReport:
    date_range_days: int
    total_inspections: int
    accepted: int
    rejected: int
    acceptance_rate: float
    defect_rate: float
    trend: list[TrendPoint] = field(default_factory=list)


@dataclass(frozen=True)
class DefectSummaryReport:
    defect_counts: dict[str, int]
    total_defects: int


@dataclass(frozen=True)
class MachinePerformanceReport:
    utilization_by_machine: dict[str, int]


class ReportService:
    """
    Builds report data structures from DashboardService and
    MachineService, and exports them to CSV/PDF under exports/.
    """

    def __init__(
        self,
        dashboard_service: DashboardService,
        machine_service: MachineService,
        ai_model_repository,
        report_repository,
    ) -> None:
        self._dashboard_service = dashboard_service
        self._machine_service = machine_service
        self._ai_model_repository = ai_model_repository
        self._report_repository = report_repository

    def build_daily_production_report(self) -> DailyProductionReport:
        from datetime import datetime, timezone

        summary = self._dashboard_service.get_summary()
        trend = self._dashboard_service.get_trend(days=1)
        today_trend = trend[0] if trend else None

        return DailyProductionReport(
            report_date=datetime.now(timezone.utc).date().isoformat(),
            total_inspected=summary.today_production,
            accepted=today_trend.good_count if today_trend else 0,
            rejected=today_trend.defective_count if today_trend else 0,
            acceptance_rate=summary.acceptance_rate,
        )

    def build_inspection_summary_report(self, days: int = 7) -> InspectionSummaryReport:
        summary = self._dashboard_service.get_summary()
        trend = self._dashboard_service.get_trend(days)

        return InspectionSummaryReport(
            date_range_days=days,
            total_inspections=summary.total_inspections,
            accepted=summary.accepted_count,
            rejected=summary.rejected_count,
            acceptance_rate=summary.acceptance_rate,
            defect_rate=summary.defect_rate,
            trend=trend,
        )

    def build_defect_summary_report(self) -> DefectSummaryReport:
        breakdown = self._dashboard_service.get_defect_breakdown()
        return DefectSummaryReport(defect_counts=breakdown, total_defects=sum(breakdown.values()))

    def build_machine_performance_report(self) -> MachinePerformanceReport:
        utilization = self._dashboard_service.get_machine_utilization()
        return MachinePerformanceReport(utilization_by_machine=utilization)

    def get_confidence_statistics(self) -> dict[str, float]:
        """Min/max/mean confidence across recent inspections — used by the full export."""
        recent = self._dashboard_service.get_recent_inspections(limit=500)
        if not recent:
            return {"min": 0.0, "max": 0.0, "mean": 0.0}
        scores = [r.confidence_score for r in recent]
        return {"min": round(min(scores), 4), "max": round(max(scores), 4), "mean": round(sum(scores) / len(scores), 4)}

    def build_full_export_payload(self, generated_by_id: int) -> dict:
        """Everything a complete report needs, assembled once and shared by both CSV and PDF export."""
        active_model = self._ai_model_repository.get_active_model()
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "ai_model_used": f"{active_model.model_name} ({active_model.version})" if active_model else "None active",
            "inspection_summary": self.build_inspection_summary_report(),
            "defect_summary": self.build_defect_summary_report(),
            "machine_performance": self.build_machine_performance_report(),
            "batch_statistics": self._dashboard_service.get_batch_statistics(),
            "confidence_statistics": self.get_confidence_statistics(),
        }

    def export_csv(self, generated_by_id: int) -> Path:
        """Export a full report as CSV under exports/. Registers the export in the reports table."""
        payload = self.build_full_export_payload(generated_by_id)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = EXPORTS_DIR / filename

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["GPP Manufacturing Quality Report"])
            writer.writerow(["Generated at", payload["generated_at"]])
            writer.writerow(["AI model used", payload["ai_model_used"]])
            writer.writerow([])

            summary = payload["inspection_summary"]
            writer.writerow(["Inspection Summary"])
            writer.writerow(["Total inspections", summary.total_inspections])
            writer.writerow(["Accepted", summary.accepted])
            writer.writerow(["Rejected", summary.rejected])
            writer.writerow(["Acceptance rate (%)", summary.acceptance_rate])
            writer.writerow(["Defect rate (%)", summary.defect_rate])
            writer.writerow([])

            writer.writerow(["Confidence Statistics"])
            for key, value in payload["confidence_statistics"].items():
                writer.writerow([key, value])
            writer.writerow([])

            writer.writerow(["Defect Distribution"])
            writer.writerow(["Defect type", "Count"])
            for name, count in payload["defect_summary"].defect_counts.items():
                writer.writerow([name, count])
            writer.writerow([])

            writer.writerow(["Machine Performance (batches processed, proxy metric)"])
            writer.writerow(["Machine", "Batches processed"])
            for name, count in payload["machine_performance"].utilization_by_machine.items():
                writer.writerow([name, count])
            writer.writerow([])

            writer.writerow(["Batch Statistics"])
            writer.writerow(["Status", "Count"])
            for status, count in payload["batch_statistics"].items():
                writer.writerow([status, count])

        self._report_repository.create(
            generated_by=generated_by_id, report_type="Full Report (CSV)",
            date_start=payload["generated_at"][:10], date_end=payload["generated_at"][:10],
            file_path=str(output_path),
        )
        logger.info("CSV report exported to %s", output_path)
        return output_path

    def export_pdf(self, generated_by_id: int) -> Path:
        """Export a full report as PDF under exports/. Registers the export in the reports table."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        payload = self.build_full_export_payload(generated_by_id)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = EXPORTS_DIR / filename

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(output_path), pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
        elements = [
            Paragraph("GPP Manufacturing Quality Report", styles["Title"]),
            Paragraph(f"Generated: {payload['generated_at']}", styles["Normal"]),
            Paragraph(f"AI model used: {payload['ai_model_used']}", styles["Normal"]),
            Spacer(1, 0.5 * cm),
        ]

        summary = payload["inspection_summary"]
        elements.append(Paragraph("Inspection Summary", styles["Heading2"]))
        elements.append(_make_table([
            ["Total inspections", str(summary.total_inspections)],
            ["Accepted", str(summary.accepted)],
            ["Rejected", str(summary.rejected)],
            ["Acceptance rate", f"{summary.acceptance_rate}%"],
            ["Defect rate", f"{summary.defect_rate}%"],
        ]))
        elements.append(Spacer(1, 0.4 * cm))

        elements.append(Paragraph("Confidence Statistics", styles["Heading2"]))
        elements.append(_make_table([[k.capitalize(), str(v)] for k, v in payload["confidence_statistics"].items()]))
        elements.append(Spacer(1, 0.4 * cm))

        elements.append(Paragraph("Defect Distribution", styles["Heading2"]))
        defect_rows = [["Defect type", "Count"]] + [[k, str(v)] for k, v in payload["defect_summary"].defect_counts.items()]
        elements.append(_make_table(defect_rows, header=True) if len(defect_rows) > 1 else Paragraph("No defects recorded.", styles["Normal"]))
        elements.append(Spacer(1, 0.4 * cm))

        elements.append(Paragraph("Machine Performance", styles["Heading2"]))
        machine_rows = [["Machine", "Batches processed"]] + [
            [k, str(v)] for k, v in payload["machine_performance"].utilization_by_machine.items()
        ]
        elements.append(_make_table(machine_rows, header=True) if len(machine_rows) > 1 else Paragraph("No machine activity recorded.", styles["Normal"]))
        elements.append(Spacer(1, 0.4 * cm))

        elements.append(Paragraph("Batch Statistics", styles["Heading2"]))
        batch_rows = [["Status", "Count"]] + [[k, str(v)] for k, v in payload["batch_statistics"].items()]
        elements.append(_make_table(batch_rows, header=True) if len(batch_rows) > 1 else Paragraph("No batches created.", styles["Normal"]))

        doc.build(elements)

        self._report_repository.create(
            generated_by=generated_by_id, report_type="Full Report (PDF)",
            date_start=payload["generated_at"][:10], date_end=payload["generated_at"][:10],
            file_path=str(output_path),
        )
        logger.info("PDF report exported to %s", output_path)
        return output_path


def _make_table(rows: list[list[str]], header: bool = False):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table = Table(rows, hAlign="LEFT")
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")))
        style.append(("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    return table
