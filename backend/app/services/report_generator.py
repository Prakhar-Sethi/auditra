"""
Generates a PDF compliance report from audit results.
Uses Jinja2 for HTML templating, then WeasyPrint for PDF conversion.
"""
import os
import uuid
from datetime import datetime
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader

from app.models.schemas import AuditResponse, Chain


REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "reports")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates")


def generate_report(
    audit: AuditResponse,
    dataset_name: str,
    fixes_applied: List[str],
) -> str:
    """Returns the path to the generated PDF file."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("report.html")

    critical = [c for c in audit.chains if c.risk_label == "CRITICAL"]
    high = [c for c in audit.chains if c.risk_label == "HIGH"]
    medium = [c for c in audit.chains if c.risk_label == "MEDIUM"]
    low = [c for c in audit.chains if c.risk_label == "LOW"]

    html = template.render(
        dataset_name=dataset_name,
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        total_chains=len(audit.chains),
        critical_chains=critical,
        high_chains=high,
        medium_chains=medium,
        low_chains=low,
        fixes_applied=fixes_applied,
        eu_compliant=len(critical) == 0 and len(high) == 0,
    )

    report_id = str(uuid.uuid4())[:8]
    html_path = os.path.join(REPORTS_DIR, f"fairlens_report_{report_id}.html")
    pdf_path = os.path.join(REPORTS_DIR, f"fairlens_report_{report_id}.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(pdf_path)
        os.remove(html_path)
        return pdf_path
    except Exception:
        # WeasyPrint may need system libs; return HTML as fallback
        return html_path
