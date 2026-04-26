# Auditra — Technology Stack

## Backend

### Runtime
| Technology | Version | Role |
|---|---|---|
| Python | 3.11 | Runtime |
| FastAPI | 0.11x | REST API framework, async request handling |
| Uvicorn | — | ASGI server |
| Pydantic v2 | — | Request/response schema validation, settings |
| pydantic-settings | — | `.env` file → `Settings` class auto-mapping |

FastAPI chosen for: automatic OpenAPI docs at `/docs`, Pydantic integration, async support, and static file serving (serves compiled React bundle in production).

### Data Processing
| Technology | Role |
|---|---|
| pandas | DataFrame operations, CSV parsing, group-level aggregations |
| numpy | Array math, geometric mean, ECE computation, weight arrays |
| scipy.stats | `chi2_contingency` (Cramér's V), `pearsonr`, `f_oneway` (eta-squared) |
| scikit-learn | `StratifiedKFold`, `cross_val_predict`, `cross_val_score`, `LabelEncoder`, `DummyClassifier` |

### ML Models
| Technology | Role |
|---|---|
| LightGBM | Fallback classifier for chain scoring, fairness metrics, calibration, conjunctive proxies |
| scikit-learn DummyClassifier | Majority-class baseline for skill score computation |

LightGBM used throughout as the local fallback for three distinct tasks:
1. **Chain scoring** — predicts protected attribute from chain features (Vertex AI primary)
2. **Fairness metrics** — predicts outcome from non-protected features (Vertex AI primary)
3. **Calibration audit** — predicts outcome to get probability outputs for ECE computation

### Graph Processing
| Technology | Role |
|---|---|
| NetworkX | `DiGraph` for correlation graph; node/edge management; successor traversal |

The graph is a directed graph where edges point from proxy features toward protected attributes. Protected attributes are sink nodes (no outgoing edges). DFS runs over this graph to enumerate chains.

### Vertex AI / GCP
| Technology | Role |
|---|---|
| `google-cloud-aiplatform` | AutoML training jobs, endpoint deployment, online prediction |
| `vertexai` | Gemini generative models (`GenerativeModel`, `Content`, `Part`) |
| `google-cloud-storage` | Dataset uploads to GCS bucket for AutoML training |
| Application Default Credentials (ADC) | Auth on GCP VM — no JSON key needed |

Two Vertex AI product types used:
- **AutoML Tabular** — trains classification models on tabular data with no code
- **Vertex AI Generative AI** — Gemini 1.5 Flash 8B (explanations) + Gemini 2.5 Flash (chat)

### Report Generation
| Technology | Role |
|---|---|
| FPDF / reportlab | PDF generation for audit reports |

### Statistical Methods
| Method | Source | Implementation |
|---|---|---|
| Bias-corrected Cramér's V | Bergsma (2013) | `graph_engine._cramers_v_with_p` |
| Eta-squared | Cohen (1988) | `graph_engine._eta_squared_with_p` |
| Bonferroni correction | — | Applied to all pairwise p-values |
| Baseline-adjusted skill score | — | `(accuracy − baseline) / (1 − baseline)` |
| Kamiran & Calders reweighing | 2012 | `reweighing.compute_sample_weights` |
| Expected Calibration Error | Guo et al. 2017 | `calibration._ece` |
| Intersectional SPD | Kearns et al. 2018 | `intersectional.compute_intersectional_audit` |

---

## Frontend

### Core
| Technology | Version | Role |
|---|---|---|
| React | 18 | Component framework |
| TypeScript | 5 | Type safety |
| Vite | 5 | Build tool, dev server |

### Styling
| Technology | Role |
|---|---|
| Tailwind CSS | Utility-first CSS, responsive layout |

### Visualization
| Technology | Role |
|---|---|
| D3.js | Force-directed graph visualization of the correlation graph |

D3 used specifically for the interactive graph view: nodes are features, edges are correlations, chains are highlighted paths. Force simulation positions nodes automatically.

### Build Output
Production build (`npm run build`) outputs to `frontend/dist/`. FastAPI mounts this as static files and serves `index.html` for all non-API routes (SPA pattern).

---

## Infrastructure

### GCP Resources
| Resource | Spec | Purpose |
|---|---|---|
| VM: auditra-vm | e2-standard-4 (4 vCPU, 16 GB RAM), Ubuntu 22.04, us-central1-a | Runs FastAPI server |
| GCS Bucket: auditra-ml-6bf0badc | Standard, us-central1 | Dataset storage for AutoML |
| Vertex AI AutoML Tabular | 8 training jobs × 1000 milli-node-hours | Chain-scorer + outcome-scorer models |
| Vertex AI Endpoints | 8 × n1-standard-4, 1 replica | Online prediction serving |
| Vertex AI Generative | Gemini 1.5 Flash 8B, Gemini 2.5 Flash | Chain explanations + chat |

### Firewall
- GCP VPC firewall rule `allow-8000`: TCP port 8000, source 0.0.0.0/0
- Allows public access to the FastAPI server at `http://34.41.3.184:8000`

### Process Management
- Server runs via `nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &`
- Persists after SSH session close
- Logs to `server.log` in the backend directory

---

## Datasets

| Dataset | Rows | Source |
|---|---|---|
| COMPAS | ~5,278 (filtered) | ProPublica 2016 — `compas-scores-two-years.csv` |
| Adult Income (train) | ~30,162 | UCI ML Repository — `adult.data` |
| Adult Income (test) | ~15,060 | UCI ML Repository — `adult.test` |
| German Credit | 1,000 | UCI ML Repository — `german.data` |

COMPAS filtering follows Angwin et al. (2016): days_b_screening_arrest ∈ [−30,30], is_recid ≠ −1, c_charge_degree ≠ 'O', score_text ≠ 'N/A', race ∈ {African-American, Caucasian}.

Adult Income normalization: trailing period stripped from test file income labels; `fnlwgt` column dropped (sampling weight, not a feature).

German Credit: `personal_status_sex` decoded to binary `sex` column; `credit_risk` (1=good, 2=bad) binarized to `credit_risk_binary`.

---

## Test Suite

| File | Tests | Coverage |
|---|---|---|
| `test_engine.py` | 7 | Graph engine, chain detection, DFS |
| `test_benchmarks.py` | 43 | Unit metric correctness (SPD, DI, ECE, etc.) |
| `test_new_services.py` | 30 | Calibration, intersectional, reweighing |
| `test_real_datasets.py` | 32 | Real dataset metrics vs paper baselines |

112 tests total. Run with: `python -m pytest tests/ -v --tb=short`

Real dataset tests require internet access to download datasets from UCI and GitHub.

---

## Dependency Graph (key services)

```
audit.py (route)
  ├─ graph_engine.py         ← scipy, networkx, numpy
  ├─ chain_scorer.py         ← vertex_ai_service.py, lightgbm
  ├─ gemini_service.py       ← vertexai
  ├─ fairness_metrics.py     ← vertex_ai_service.py, lightgbm, sklearn
  ├─ reweighing.py           ← numpy
  ├─ interaction_scanner.py  ← lightgbm, sklearn
  ├─ calibration.py          ← lightgbm, sklearn
  └─ intersectional.py       ← pandas, numpy

vertex_ai_service.py         ← google-cloud-aiplatform, config
gemini_service.py            ← vertexai, config
config.py                    ← pydantic-settings
session_store.py             ← stdlib (dict)
```
