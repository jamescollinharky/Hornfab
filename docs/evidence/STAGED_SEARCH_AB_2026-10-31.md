# Staged vs joint search A/B — 2026-10-31

Equal-budget protocol for hierarchical block CMA (macro → shape → joint polish) vs one
joint CMA run on `crease__core_law`. Implements the staged-search recommendation.

## Protocol

| Arm | Budget | Active set |
|---|---|---|
| Stage A macro | 20 | `L_mm`, `a_deg`, `n`, `s`, `k` |
| Stage B shape | 20 | `az_*` polish + `morph_corner_mm` / `morph_rate` / `morph_fixed` (macro pinned from A's best) |
| Stage C polish | 20 | A∪B, boxes ±12 % of joint full width around B's best, `sigma0=0.06` |
| Joint control | 60 | all jointly searchable keys, `sigma0=0.15` |

Configs: `examples/typologies/staged_ab_2026-10-31/`.
Harness: `tools/run_staged_search.py` (seeds B from A's `best.json`, builds C, writes `COMPARE.md`).

## Offline suite

```
..........                                                               [100%]
```

`pytest tests/test_tools_staged_search.py -q` — 10 passed (config partition, seed-from-best,
narrow boxes, crease a(0/45/90) mirror, dry-run materialisation, synthetic A/B).

## Synthetic coupled A/B (no GPU) — directional method check

Landscape: `J = ||m−m*||² + ||s − (s* + 0.7(m−m*))||²` with 5 macro + 12 shape dims,
equal budget 60, (1+1)-ES. Pasted from `SYNTHETIC.json`:

```json
{
  "kind": "synthetic_coupled",
  "n_macro": 5,
  "n_shape": 12,
  "coupling": 0.7,
  "budget_total": 60,
  "staged": {
    "J_A": 0.39940886884729376,
    "J_B": 0.3164239112835432,
    "J_C": 0.10047618320056202,
    "n_evals": 60,
    "budgets": {"A": 20, "B": 20, "C": 20}
  },
  "joint": {"J": 0.3018938610007795, "n_evals": 60},
  "verdict": "staged+polish wins",
  "seed_J": 1.261790841194032
}
```

**Verdict (synthetic): staged+polish wins** (final J 0.100 vs joint 0.302). This supports
keeping the chaining harness; it is **not** an acoustic claim.

## Acoustic GPU A/B — blocked on this machine

Machine: Apple M3 MacBook, no NVIDIA GPU, no project `.venv`, `cma` / mesher / beat not
installed. Attempt:

```
$ python -m hornlab_search.cli search --config examples/typologies/staged_ab_2026-10-31/stageA_macro__crease_core_law.yaml --mode screen
search FAILED: ModuleNotFoundError: No module named 'cma'
```

Dry-run on this machine did emit the four derived configs under
`runs/staged_ab_2026-10-31/configs/` (gitignored).

### GPU-box command (Windows RTX, one job at a time)

```powershell
.\.venv\Scripts\python.exe tools\run_staged_search.py `
  --out runs\staged_ab_2026-10-31 --both
```

(`--backend auto` → `beat_cuda` on Windows.)

### Apple Silicon Mac (Metal)

`beat_metal` is wired through `solve.base` / `BeatBackend` / CLI `--backend`. The harness
defaults to Metal on Darwin and clears `cuda_fused` on the emitted configs:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev,crosscheck]"
python tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both
# equivalent explicit: --backend beat_metal
```

Do not mix Metal and CUDA runs in one leaderboard until a Mac↔4060 A/B is within ~0.2 dB
(NEXT_DEV_PRIORITIES P3). Fallback: `--backend beat_cpu` (slow).

Record into this doc (or a dated follow-up): per-arm best J, evals/valid from
`search.ndjson`, crease a(0/45/90) / strength from the harness `COMPARE.md`, wall-clock.
Smoke-night joint reference on the same cell at budget 60: seed J 19.022 → best **2.784**
(`docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md`).

## Decision (2026-10-31)

| Question | Answer |
|---|---|
| Keep thin stage-chaining helper? | **Yes** — `tools/run_staged_search.py` (seed-from-best, pin sets, narrow polish boxes, COMPARE). Synthetic coupled A/B supports the schedule. |
| Change default `search` path / promote into `hornlab_search/search/`? | **Not yet** — wait for the GPU acoustic A/B above. |
| Parallel higher leverage | Objective **term normalisation** and diagonal scoring for crease knobs remain higher leverage than search scheduling (smoke night findings). |

## Reproduce offline

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_tools_staged_search.py -q
.\.venv\Scripts\python.exe tools\run_staged_search.py --synthetic --dry-run --out runs\staged_ab_check
```
