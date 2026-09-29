# 🛰️ TruthLens — AI-Powered Misinformation Review

> A human-in-the-loop tool that scores news-style text for misinformation risk, **explains why**, and routes uncertain cases to a reviewer.

<!-- TODO: add a screenshot: ![TruthLens](docs/screenshots/analyze.png) -->

**Hackathon:** Intra IIT Tech Meet 1.0 · **Demo:** `<video or live link>`

---

## The problem

Misinformation spreads faster than moderators and fact-checkers can read it. A plain "fake / real" classifier isn't enough: reviewers need to know *how confident* the model is, *which passages* drove the score, and *which cases* deserve human attention first.

## What TruthLens does

| Capability | How it works |
|---|---|
| **Verdict + probabilities** | Returns *Likely Real*, *Likely Misinformation*, or *Uncertain* with the model's real probabilities. If the top probability is below **0.65**, the case is marked *Uncertain* instead of being forced into a label. |
| **Explanations** | Breaks down five writing-style signals (sentiment, subjectivity, readability, exclamation use, ALL-CAPS use) in plain language. |
| **Passage highlighting** | Highlights sentences that shifted the model's score (found by re-scoring the article with each sentence removed) plus style cues such as shouting words and exclamations. |
| **Source credibility** | Looks up the outlet in a small credibility table and shows a blended score (`0.8 × model confidence + 0.2 × source credibility`). This is context only; it does **not** change the verdict label. |
| **Review workflow** | Cases are prioritised (Uncertain → High, Likely Misinformation → Medium, Likely Real → Low) and can be Confirmed, Dismissed, or Relabeled with a reviewer note. |
| **History & reports** | Browse past cases and export CSV or PDF (whole session or a single case). |
| **UI extras** | Light/dark theme, confidence shown as % or decimal, responsible-use notices, and a warning before closing the tab so session data isn't lost. |


### Dataset and evaluation setup

- **Dataset:** LIAR and ISOT
- **Task:** binary classification of news-style text (label 1 = REAL, label 0 = FAKE)
- **Split:** 70 : 15 : 15 (train / validation / test). Deduplication and train/validation/test overlap removal are applied after splitting, so the final row counts differ slightly from the nominal ratio.
- **Features:** 773 per article (768 DistilBERT embedding + 5 linguistic features)
  
## Model performance

XGBoost classifier, evaluated on the held-out test split:

| Metric | Score |
|---|---|
| Accuracy | 89.71% |
| Precision | 88.02% |
| Recall | 92.26% |
| F1 score | 90.09% |
| ROC-AUC | 97.32% |

**Read these numbers carefully:**
- They describe the XGBoost classifier alone. They do **not** include the *Uncertain* band (top probability below 0.65), the source-credibility blend, or the human review step, so end-to-end behaviour in the app differs.
- The training preprocessing (`backend/preprocessing.py`) deduplicates each split and removes train/validation/test overlap to limit data leakage.
- `<Add: dataset name and source, number of train/validation/test rows, class balance, and which class is treated as positive for precision/recall.>`

## How it works

```
 Article text (+ optional title / source / author)
          │
          ▼
  preprocessing.py ──► clean & normalise text
          │
          ▼
  feature_extraction.py ──► 773 features
          │                    ├─ 768  DistilBERT embedding (mean-pooled)
          │                    └─   5  sentiment, subjectivity, readability,
          │                            exclamation ratio, uppercase ratio
          ▼
  model_prediction.py ──► XGBoost classifier (binary:logistic, 200 trees)
          │                 → fake_prob / real_prob
          ▼
  labels.py ──► UI verdict (Real / Misinformation / Uncertain @ 0.65)
          │
          ├─► explanation_user_improved.py ──► plain-language signal breakdown
          ├─► source_credibility.py ─────────► outlet credibility context
          └─► text_highlights.py ────────────► passages that mattered
          ▼
  Streamlit UI (Analyze → Review Queue → Review Case → History → Reports)
```

## Tech stack

Python · Streamlit · XGBoost · PyTorch + Hugging Face Transformers (`distilbert-base-uncased`) · TextBlob · textstat · pandas / NumPy · Plotly · ReportLab

## Project structure

```
truthlens/
├── app.py                  # Streamlit entry point
├── backend_processor.py    # Runs the ML pipeline for one article
├── labels.py               # Model output → UI labels, threshold logic
├── paths.py                # Finds the backend + results folder from any cwd
├── mock_data.py            # Loads/saves cases from the results CSV (name is historical)
├── styles.py               # Custom CSS
├── app_pages/              # Analyze, Review Queue, Review Case, History, Reports, Settings
├── components/             # Cards, charts, explanations, sidebar, review widgets
├── utils/export.py         # CSV / PDF export helpers
├── backend/                # ML backend
│   ├── xgboost_model.json          # trained classifier
│   ├── preprocessing.py
│   ├── feature_extraction.py
│   ├── model_prediction.py
│   ├── explanation_user_improved.py
│   ├── text_highlights.py
│   ├── source_credibility.py
│   ├── source_credibility_lookup.csv
│   └── main.py                     # standalone interactive CLI (single article or CSV batch)
├── docs/                   # screenshots + development notes
├── requirements.txt
└── README.md
```

## Getting started

**Prerequisites:** Python 3.10+ (developed on 3.13) and internet access on the first analysis (downloads DistilBERT, a few hundred MB, once).

```bash
# 1. Clone
git clone <your-repo-url>
cd truthlens

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501), paste an article on **Analyze**, and click **Analyze Content**. The first run is slow while DistilBERT downloads; later runs are fast. Review Queue, History and Reports stay empty until you have analysed at least one article.

### Optional: backend only (CLI)

```bash
cd backend
python main.py     # interactive: analyse one article or a CSV of articles
```

### Troubleshooting

| Symptom | Fix |
|---|---|
| `xgboost ... is too old to load xgboost_model.json` | `pip install -U "xgboost>=3.1"` |
| `ML backend not found` | Run from the repo root, or set `TRUTHLENS_BACKEND` to the folder containing `xgboost_model.json` |
| Hangs / fails on first analysis | DistilBERT needs internet once to download |

## Current limitations and future plan

- **This is a triage aid, not a fact-checker.** It scores writing patterns and semantics learned from training data; it does not verify claims against external sources. Every verdict is meant to be reviewed by a human.
- The source-credibility table is small (about 20 outlets) and hand-set; unknown sources default to 0.5.
- Results are stored in a local CSV; there is no database or multi-user support. Can be moved to a database system where user can have a secure and private usage of the app.

## Responsible use

TruthLens supports human review; it should not be the sole basis for removing content or making claims about a person or outlet. Model errors are expected, especially on satire, breaking news, and topics unlike the training data.

## Roadmap

- Web batch upload wired to the existing backend pipeline
- Retrieval-based claim checking against trusted sources
- Larger, data-driven source-credibility scoring
- Persistent storage and multi-reviewer accounts

## License

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
