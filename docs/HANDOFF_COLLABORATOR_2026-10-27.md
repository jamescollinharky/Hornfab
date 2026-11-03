# Handoff for the collaborator: pulling the repo and finding the optimization data

Written 2026-10-27. Everything below is already on `main` of https://github.com/llevaachingada/Hornfab (commit `9bc046f`).

## 1. Get the code

```bash
git clone https://github.com/llevaachingada/Hornfab.git hornlab-search   # first time
cd hornlab-search
git checkout main && git pull origin main                                # if you already have it
```

`main` is the current branch; `unified-typologies` is identical to it right now. Start with `docs/CONTINUITY.md` (newest entry first) and `docs/INDEX.md` (every doc, one line each).

## 2. The data, no CUDA needed: `docs/data/campaign_v4_2026-10-27/`

| File | What it is |
|---|---|
| `evals.csv` | One row per evaluation (about 4,000). Columns: `cell`, `eval`, `ok`, `cached`, `J` (objective), `term_cov/rip/di/dislope/flat/load/distd/diag/penalty/total` (the tolerance-normalised terms), `p_*` (design parameters), and JSON arrays `freqs_hz`, `bw_h_deg`, `bw_v_deg`, `di_db`, `ripple_*`, `on_axis_db` (12-point grid, 500 Hz to 10 kHz). Refused candidates have blank J. |
| `cells_summary.csv` | One row per typology cell: family, seed J, best J, refusal rate, best eval number. |
| `best_designs.json` | Best parameters and terms for each cell. |
| `README.md` | Column definitions and caveats. |

Quick start:

```python
import pandas as pd, json
df = pd.read_csv("docs/data/campaign_v4_2026-10-27/evals.csv")
ok = df[df.ok]
print(ok.groupby("cell").J.min())                       # best J per cell
bw = ok.bw_h_deg.apply(json.loads)                      # horizontal -6 dB beamwidth per frequency
```

## 3. How to read it

- **J = sum(weight x term) + penalty.** Stored terms are normalised: raw value = term x tolerance. Tolerances are in `docs/evidence/OBJECTIVE_V4_TOLERANCES.md`; weights are in each cell's brief (`examples/briefs/campaign_2026-10-26_v4/*_v4.yaml`); design bounds are in the cell's config (`examples/typologies/campaign_2026-10-26_v4/*_v4.yaml`).
- **J is comparable only within a cell.** Each brief weights the terms differently.
- **Search method:** CMA-ES, one fixed seed per cell. Rows are in order, so you can plot J against `eval` for convergence. A "resume" extends the same run, so rows past about 100 are the second night.
- **Refusals:** many cells refuse 20-50% of candidates (invalid geometry); `b1w__biradial_keele` and `b3bw__biradial_keele` refuse about 90%, so their best J rests on very few valid designs.
- **Scoring code:** `hornlab_search/objective/scalar_v4.py` (terms), `hornlab_search/metrics/diagonal.py` (diagonal term). Why these terms and tolerances: `docs/research/V4_SCORING_REVIEW_2026-10-27.md` and `docs/research/V4_TOLERANCE_RESEARCH_2026-10-27.md`.

## 4. The raw data: public Hugging Face dataset repo (no account needed)

Git only carries text. The raw material is at

**<https://huggingface.co/datasets/chingadalleva/hornlab-search-data>**

It is **public** — no Hugging Face account, no token, no `hf auth login`. It holds seven tar shards
(11.56 GB / 10.76 GiB packed; 2026-11-02 pack of the tree at `task/hardware-decision-2026-11-01`).

Agent-executable runbook (sha256 table, verification counts, troubleshooting):
`docs/COLLABORATOR_PULL_RUNBOOK_2026-11-02.md`.

| Shard | Contents | Raw size |
|---|---|---|
| `text-*.tar` | every `.json`/`.ndjson`/`.yaml`/`.html`/`.md` under `runs/` (124,681 files) | 0.51 GB |
| `solve-*.tar` | `cache/solve/**` — `response.npz` + `status.json` per cache key (48,817 files) | 6.45 GB |
| `dataset-*.tar` | `dataset/` (24,083 files) | 4.24 GB |

**Pull it** (from the repo root, after cloning; needs `pip install huggingface_hub` for the `hf` CLI):

```bash
hf download chingadalleva/hornlab-search-data --repo-type dataset --include "*.tar" --local-dir .hf_stage
python -c "import glob,tarfile;[tarfile.open(t).extractall('.',filter='data') for t in sorted(glob.glob('.hf_stage/*.tar'))]"
```

or the repo's own wrapper: `python tools/hf_sync.py pull --repo chingadalleva/hornlab-search-data --dest .`

Shards untar **in place** (arcnames are repo-relative), so `runs/`, `cache/solve/` and `dataset/` land
next to your checkout and every path in the CSVs/NDJSON still resolves. Delete `.hf_stage/` afterwards.
Slow link: set `HF_XET_HIGH_PERFORMANCE=1`; the download resumes if interrupted (re-run the same command).

**Why the solve cache matters:** it is keyed on geometry + solver settings, **not** on the objective, so
you can re-score the same designs under a different objective/weights with no CUDA and no new solves.
`tools/rescore/rescore_v2.py` is the worked example of an offline re-score.

**Not uploaded (16.81 GB):** `cache/mesh/**` and `runs/**/*.msh`. Rebuild those locally with the mesher
(`hornlab_mesher`, CPU-only) if you need geometry; ask the owner if you need the exact stored meshes and
they can be packed as a separate `meshes` group (`python tools/hf_sync.py pack --groups meshes`).

## 5. Things still changing

- A second 100-evaluation resume night is still running. Re-run `tools/export_campaign_tables.py` (or pull again later) for the final numbers.
- Two cells need a re-run (`crease__osse_b1w`, `b2t__rosse_morph`), so their rows are short.
