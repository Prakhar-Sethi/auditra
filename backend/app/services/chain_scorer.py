"""
Chain risk scoring via LightGBM reconstructive accuracy.
Trains a model to predict the protected attribute from the chain's non-protected
features. Accuracy == how well the chain reconstructs the protected attribute.

Vertex AI AutoML is used when VERTEX_AI_ENDPOINT_ID is configured; otherwise
this local LightGBM scorer is used as a fully functional fallback.
"""
from typing import List, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder

try:
    import lightgbm as lgb
    LGB_AVAILABLE = True
except ImportError:
    LGB_AVAILABLE = False

from app.core.config import settings
from app.models.schemas import Chain


def score_chain(df: pd.DataFrame, chain: Chain) -> float:
    """
    Returns reconstructive accuracy [0, 1] for the chain.
    Tries Vertex AI AutoML first, falls back to local LightGBM.
    """
    feature_cols = [c for c in chain.path if c != chain.protected_attribute]
    target_col = chain.protected_attribute

    if target_col not in df.columns or not feature_cols:
        return chain.risk_score

    # Try Vertex AI first
    from app.services.vertex_ai_service import score_chain_vertex
    vertex_score = score_chain_vertex(df, chain)
    if vertex_score is not None:
        return vertex_score

    return _score_via_lgbm(df, feature_cols, target_col)


def _score_via_lgbm(df: pd.DataFrame, feature_cols: List[str], target_col: str) -> float:
    if not LGB_AVAILABLE:
        return 0.5

    subset = df[feature_cols + [target_col]].dropna()
    if len(subset) < 50:
        return 0.0

    X = subset[feature_cols].copy()
    y = subset[target_col].copy()

    # Encode categoricals
    for col in X.columns:
        if X[col].dtype == object or str(X[col].dtype) == "category":
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))

    if y.dtype == object or str(y.dtype) == "category":
        le = LabelEncoder()
        y = le.fit_transform(y.astype(str))
        n_classes = len(np.unique(y))
        objective = "multiclass" if n_classes > 2 else "binary"
    else:
        objective = "binary"
        n_classes = 2

    params = {
        "objective": objective,
        "num_leaves": 31,
        "learning_rate": 0.1,
        "n_estimators": 100,
        "verbose": -1,
        "num_class": n_classes if objective == "multiclass" else 1,
    }

    model = lgb.LGBMClassifier(**{k: v for k, v in params.items() if k != "num_class"})
    try:
        scores = cross_val_score(model, X, y, cv=3, scoring="accuracy")
        return float(np.mean(scores))
    except Exception:
        return 0.0


def _score_via_vertex(df: pd.DataFrame, feature_cols: List[str], target_col: str) -> float:
    """Calls Vertex AI online prediction endpoint."""
    try:
        from google.cloud import aiplatform

        aiplatform.init(project=settings.gcp_project_id, location=settings.gcp_region)
        endpoint = aiplatform.Endpoint(settings.vertex_ai_endpoint_id)

        subset = df[feature_cols + [target_col]].dropna().head(200)
        instances = subset[feature_cols].to_dict(orient="records")
        response = endpoint.predict(instances=instances)

        preds = [max(p, key=lambda k: p[k]) if isinstance(p, dict) else str(p) for p in response.predictions]
        actual = subset[target_col].astype(str).tolist()
        accuracy = sum(p == a for p, a in zip(preds, actual)) / max(len(actual), 1)
        return float(accuracy)
    except Exception:
        return _score_via_lgbm(df, feature_cols, target_col)


def score_all_chains(df: pd.DataFrame, chains: List[Chain]) -> List[Chain]:
    scored = []
    for chain in chains:
        acc = score_chain(df, chain)
        from app.services.graph_engine import _risk_label
        scored.append(
            chain.model_copy(
                update={"risk_score": round(acc, 4), "risk_label": _risk_label(acc)}
            )
        )
    return sorted(scored, key=lambda c: c.risk_score, reverse=True)
