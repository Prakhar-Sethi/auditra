"""
Pre-loaded demo modes: Adult Income (primary) + COMPAS (secondary).
Adult Income is the primary demo — shows HIGH-risk chains (occupation → sex)
matching the Amazon hiring AI story. COMPAS demo kept for reference.
"""
import io
import os
import uuid

import pandas as pd
import requests
from fastapi import APIRouter, HTTPException

from app.api.routes.audit import run_audit
from app.core import session_store
from app.models.schemas import AuditRequest, ColumnInfo, UploadResponse
from app.services.graph_engine import detect_column_types

router = APIRouter()

COMPAS_URL = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"
COMPAS_LOCAL = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "compas.csv")

COMPAS_PROTECTED = ["race", "sex"]
COMPAS_DROP_COLS = ["id", "name", "first", "last", "dob", "compas_screening_date",
                    "c_jail_in", "c_jail_out", "c_offense_date", "r_offense_date",
                    "vr_offense_date", "screening_date", "v_screening_date",
                    "in_custody", "out_custody", "event"]

COMPAS_KEEP_COLS = [
    "age", "c_charge_degree", "race", "age_cat", "score_text",
    "sex", "priors_count", "days_b_screening_arrest", "decile_score",
    "is_recid", "two_year_recid", "juv_fel_count", "juv_misd_count", "juv_other_count"
]


def _load_compas() -> pd.DataFrame:
    # Try local cache first
    if os.path.exists(COMPAS_LOCAL):
        return pd.read_csv(COMPAS_LOCAL)

    # Try downloading
    try:
        resp = requests.get(COMPAS_URL, timeout=15)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(COMPAS_LOCAL), exist_ok=True)
        with open(COMPAS_LOCAL, "wb") as f:
            f.write(resp.content)
        return pd.read_csv(io.BytesIO(resp.content))
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not load COMPAS dataset: {e}. "
                   "Please download it manually: "
                   "curl -L https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv "
                   "-o backend/data/compas.csv"
        )


@router.post("/demo/compas")
async def load_compas_demo():
    """
    Loads the COMPAS dataset, selects relevant columns, registers a session,
    and returns upload metadata - frontend can then call /audit immediately.
    """
    df_raw = _load_compas()

    # Keep only meaningful columns that exist
    keep = [c for c in COMPAS_KEEP_COLS if c in df_raw.columns]
    df = df_raw[keep].dropna(subset=["race", "sex"]).reset_index(drop=True)

    session_id = str(uuid.uuid4())
    col_types = detect_column_types(df)

    session_store.set(session_id, "df", df)
    session_store.set(session_id, "col_types", col_types)
    session_store.set(session_id, "filename", "compas-scores-two-years.csv")
    session_store.set(session_id, "chat_history", [])
    session_store.set(session_id, "fixes_applied", [])

    columns = [
        ColumnInfo(
            name=col,
            dtype=col_types[col],
            unique_count=int(df[col].nunique()),
            null_pct=round(float(df[col].isnull().mean()), 4),
        )
        for col in df.columns
    ]

    upload_response = UploadResponse(
        session_id=session_id,
        columns=columns,
        row_count=len(df),
    )

    # Auto-run audit so the demo loads instantly
    audit_req = AuditRequest(
        session_id=session_id,
        protected_attributes=COMPAS_PROTECTED,
        max_depth=4,
        threshold=0.15,
    )
    audit_result = await run_audit(audit_req)

    return {
        "upload": upload_response,
        "audit": audit_result,
        "protected_attributes": COMPAS_PROTECTED,
        "description": (
            "COMPAS (Correctional Offender Management Profiling for Alternative Sanctions) "
            "is the criminal justice risk scoring tool found by ProPublica to discriminate "
            "against Black defendants. This is the exact dataset that sparked the algorithmic "
            "fairness research movement."
        ),
    }


# ---------------------------------------------------------------------------
# Adult Income demo (primary — shows HIGH-risk chains)
# ---------------------------------------------------------------------------

@router.post("/demo/adult")
async def load_adult_demo():
    """
    UCI Adult Income dataset. Shows HIGH-risk relay chains:
    occupation → marital_status → relationship → sex (skill 0.51, above baseline).
    Matches the Amazon hiring AI discrimination story.
    Includes full fairness metrics: SPD, DI ratio, EOD vs Kamiran/Feldman baselines.
    """
    from app.services.data_loader import load_adult

    df = load_adult()
    if df is None:
        raise HTTPException(
            status_code=503,
            detail="Could not load Adult Income dataset from UCI repository."
        )

    # Sample for demo speed — 8000 rows still shows strong patterns
    if len(df) > 8000:
        df = df.sample(n=8000, random_state=42).reset_index(drop=True)

    session_id = str(uuid.uuid4())
    col_types = detect_column_types(df)

    session_store.set(session_id, "df", df)
    session_store.set(session_id, "col_types", col_types)
    session_store.set(session_id, "filename", "adult-income.csv")
    session_store.set(session_id, "chat_history", [])
    session_store.set(session_id, "fixes_applied", [])

    columns = [
        ColumnInfo(
            name=col,
            dtype=col_types[col],
            unique_count=int(df[col].nunique()),
            null_pct=round(float(df[col].isnull().mean()), 4),
        )
        for col in df.columns
    ]

    upload_response = UploadResponse(
        session_id=session_id,
        columns=columns,
        row_count=len(df),
    )

    audit_req = AuditRequest(
        session_id=session_id,
        protected_attributes=["sex", "race"],
        max_depth=4,
        threshold=0.10,
        outcome_column="income",
        privileged_groups={"sex": "Male", "race": "White"},
        positive_outcome=">50K",
    )
    audit_result = await run_audit(audit_req)

    return {
        "upload": upload_response,
        "audit": audit_result,
        "protected_attributes": ["sex", "race"],
        "description": (
            "UCI Adult Income: occupation and marital status form multi-hop chains "
            "that reconstruct sex with 51% skill above random baseline — exactly the "
            "pattern behind Amazon's 2018 hiring AI discrimination scandal."
        ),
    }
