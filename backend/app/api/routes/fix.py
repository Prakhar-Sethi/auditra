from fastapi import APIRouter, HTTPException

from app.core import session_store
from app.models.schemas import FixRequest, FixResponse
from app.services.fix_engine import apply_fix

router = APIRouter()


@router.post("/fix", response_model=FixResponse)
async def apply_chain_fix(req: FixRequest):
    if not session_store.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    audit = session_store.get(req.session_id, "audit")
    if not audit:
        raise HTTPException(status_code=400, detail="Run /audit first.")

    chain = next((c for c in audit.chains if c.id == req.chain_id), None)
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found.")

    df = session_store.get(req.session_id, "df")
    fixed_df, shap_entries = apply_fix(df, chain)

    session_store.set(req.session_id, "df", fixed_df)
    fixes = session_store.get(req.session_id, "fixes_applied") or []
    fixes.append(chain.weakest_link)
    session_store.set(req.session_id, "fixes_applied", fixes)

    # Remove chain from audit
    remaining = [c for c in audit.chains if c.id != req.chain_id]
    updated_audit = audit.model_copy(update={"chains": remaining})
    session_store.set(req.session_id, "audit", updated_audit)

    return FixResponse(
        session_id=req.session_id,
        chain_id=req.chain_id,
        removed_feature=chain.weakest_link or "",
        shap_values=shap_entries,
        success=True,
        message=f"Removed '{chain.weakest_link}' from dataset. Chain broken.",
    )
