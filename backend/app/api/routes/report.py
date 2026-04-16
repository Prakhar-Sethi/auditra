import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core import session_store
from app.models.schemas import ReportRequest, ReportResponse
from app.services.report_generator import generate_report

router = APIRouter()


@router.post("/report", response_model=ReportResponse)
async def create_report(req: ReportRequest):
    if not session_store.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    audit = session_store.get(req.session_id, "audit")
    if not audit:
        raise HTTPException(status_code=400, detail="Run /audit first.")

    filename = session_store.get(req.session_id, "filename") or "unknown.csv"
    fixes = session_store.get(req.session_id, "fixes_applied") or []

    report_path = generate_report(audit, filename, fixes)
    report_filename = os.path.basename(report_path)

    return ReportResponse(download_url=f"/api/report/download/{report_filename}")


@router.get("/report/download/{filename}")
async def download_report(filename: str):
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "reports")
    path = os.path.abspath(os.path.join(reports_dir, filename))
    if not path.startswith(os.path.abspath(reports_dir)):
        raise HTTPException(status_code=400, detail="Invalid path.")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found.")

    media_type = "application/pdf" if path.endswith(".pdf") else "text/html"
    return FileResponse(path, media_type=media_type, filename=filename)
