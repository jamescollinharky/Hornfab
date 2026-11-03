# Runbook: pull the campaign solves (agent-executable, 2026-11-02)

**Audience:** the GitHub collaborator on `Hornfab`, or an AI coding agent acting for them.
**Goal:** put the raw campaign data (full acoustic responses, readable results, dataset records) on a machine
with **no GPU**, so the same designs can be re-scored under a different objective without re-solving anything.
**Owner of this data:** `chingadalleva` (Hugging Face). Repo is **public** — no account, token or login.

Everything below was verified by the owner on 2026-11-02 (download, checksum, in-place extraction).

---

## 0. TL;DR for an agent

```bash
git clone https://github.com/llevaachingada/Hornfab.git hornlab-search
cd hornlab-search
pip install -U huggingface_hub                       # provides the `hf` CLI
hf download chingadalleva/hornlab-search-data --repo-type dataset --include "*.tar" --local-dir .hf_stage
python -c "import glob,tarfile;[tarfile.open(t).extractall('.',filter='data') for t in sorted(glob.glob('.hf_stage/*.tar'))]"
rm -rf .hf_stage
```

Then run the checks in section 4. Do not commit anything this produced (section 6).

---

## 1. What you are downloading

| Property | Value |
|---|---|
| Repo | <https://huggingface.co/datasets/chingadalleva/hornlab-search-data> |
| Visibility | **public** (anonymous download works; anonymous `HTTP 206` on a tar was verified) |
| Snapshot | 2026-11-02 ~20:53 local, tree at `task/hardware-decision-2026-11-01` |
| Files | 7 tar shards + `.gitattributes` |
| Size | **11.56 GB** transfer (10.76 GiB), unpacked ~11.2 GB |
| Source files inside | **197,581** |

| Shard | Contents | Bytes | sha256 |
|---|---|---|---|
| `text-000.tar` | every `.json`/`.ndjson`/`.yaml`/`.yml`/`.html`/`.md` under `runs/` (124,681 files) | 731,473,920 | `700d1d1546239ff033e14e17c8a26751d8485776c755b41c183eaa63eb6f0b11` |
| `solve-000.tar` | `cache/solve/**` part 1 | 2,176,225,280 | `01981bd6305834b45a3014ca74cbb05f4da0a102274c101863e01a0324b9168c` |
| `solve-001.tar` | `cache/solve/**` part 2 | 2,176,327,680 | `8b23755ca82f1549c447a788c63696b5ae1e5faf9ad86b7bf1207fd686d70388` |
| `solve-002.tar` | `cache/solve/**` part 3 | 2,180,864,000 | `9414a48433e7a9deec5f027fb91e51c61750dfc6fb9e53a63fa023e29ed746f1` |
| `solve-003.tar` | `cache/solve/**` part 4 (tail) | 8,550,400 | `2fd9994513ff3722044dfb6f36cf8defe4122ebe446d10851bbe8c473b5a3d50` |
| `dataset-000.tar` | `dataset/` part 1 | 2,191,677,440 | `49cf6f0b883f4a20a95e510d9e197cbf76d24a1c3725aa6e7d0fe5b9b1243b70` |
| `dataset-001.tar` | `dataset/` part 2 | 2,091,612,160 | `c3f8ffaa40d54b58d727b567adad14cc7838ef70d4af51ba7317259b1e3449d1` |

Each shard is a plain `tar` (uncompressed — the payload is already `.npz`/JSON, so compression buys nothing).
Arcnames are **repo-relative**, so extracting at the repo root recreates `runs/`, `cache/solve/`, `dataset/`
exactly where the code expects them.

**Why the solve cache is the valuable part:** it is keyed on *geometry + solver settings*, **not** on the
objective. Given `cache/solve/<key>/response.npz`, you can re-score any stored design under new weights,
tolerances or a new objective version with **zero CUDA and zero new solves**. `tools/rescore/rescore_v2.py`
is the worked example (it produced `docs/evidence/OBJECTIVE_V2_RESCORE.md`).

**Not included:** `cache/mesh/**` and `runs/**/*.msh` (16.81 GB) — the stored GPU meshes. Rebuild them with
the CPU mesher if you need geometry, or ask the owner to publish a `meshes` group.

---

## 2. Prerequisites

| Requirement | Check |
|---|---|
| `git` | `git --version` |
| Python ≥ 3.12 | `python --version` (the repo pins its own `.venv`; 3.12/3.13 both work for reading data) |
| `huggingface_hub` ≥ 1.0 (gives the `hf` CLI) | `pip install -U huggingface_hub` then `hf version` |
| Free disk ≥ 25 GB | 11.56 GB in `.hf_stage` + ~11.2 GB unpacked |

No Hugging Face account, no token, no `hf auth login`, no GPU, no CUDA, no Julia.

---

## 3. Download

From the repo root:

```bash
hf download chingadalleva/hornlab-search-data --repo-type dataset --include "*.tar" --local-dir .hf_stage
```

- `--repo-type dataset` is **required**; without it the CLI looks for a *model* repo and 404s.
- Resumable: if it dies, re-run the **same** command; completed shards are skipped.
- `HF_XET_HIGH_PERFORMANCE=1` is a safe download speed knob. (`hf_transfer` / `HF_HUB_ENABLE_HF_TRANSFER` are
  dead in hub v1 — they are ignored.)

Equivalent via the repo's own wrapper:

```bash
python tools/hf_sync.py pull --repo chingadalleva/hornlab-search-data --dest .
```

---

## 4. Verify before trusting the data

**a. Checksums** (must match the table in section 1):

```bash
# macOS
shasum -a 256 .hf_stage/*.tar
# Linux
sha256sum .hf_stage/*.tar
# Windows PowerShell
Get-FileHash .hf_stage\*.tar -Algorithm SHA256 | Select-Object Hash,Path
```

**b. Extract in place, then count:**

```bash
python -c "import glob,tarfile;[tarfile.open(t).extractall('.',filter='data') for t in sorted(glob.glob('.hf_stage/*.tar'))]"
```

```bash
find runs -type f \( -name '*.json' -o -name '*.ndjson' -o -name '*.yaml' -o -name '*.yml' -o -name '*.html' -o -name '*.md' \) | wc -l   # 124681
find cache/solve -type f | wc -l                                                                                                          # 48817
find dataset -type f | wc -l                                                                                                              # 24083
```

Windows PowerShell equivalents: `(Get-ChildItem cache\solve -Recurse -File).Count` → `48817`, etc.

**c. One real record loads** (proves `numpy` can read the responses, not just that bytes landed):

```bash
python -c "import glob,numpy as np; f=sorted(glob.glob('cache/solve/*/response.npz'))[0]; d=np.load(f); print(f, list(d.keys())[:6])"
```

Then `rm -rf .hf_stage` (or delete `.hf_stage` on Windows).

A verified-good reference from the owner's machine: `cache/solve/ff8f40ce3d46-768ae9851967-cfdb0910d126/`
contains `response.npz` (266,816 B) + `status.json` (92 B).

---

## 5. What to do with it next

- **Results table (already in git, no download needed):** `docs/data/campaign_v4_2026-10-27/evals.csv`,
  `cells_summary.csv`, `best_designs.json` — read `docs/HANDOFF_COLLABORATOR_2026-10-27.md` section 2-3 first.
- **Offline re-score:** copy `tools/rescore/rescore_v2.py`'s pattern (read `cache/solve/<key>/response.npz`,
  rebuild `Response`, call the objective). No GPU, runs on a laptop.
- **Config that produced a design:** `examples/briefs/campaign_2026-10-26_v4/*_v4.yaml` (weights, tolerances)
  and `examples/typologies/campaign_2026-10-26_v4/*_v4.yaml` (bounds).
- **J is per-cell only.** Never compare J across cells; briefs weight the terms differently.

---

## 6. Rules for an agent working in this checkout

1. **Never commit the pulled data.** `/runs/`, `/cache/`, `/dataset/` are git-ignored; keep them that way.
   A commit that adds them is a defect.
2. **Never hand-edit `.venv`** and never modify installed `hornlab_*` / BEAT / Boundary Lab packages
   (repo hard rules 1-2; changes go through the pinned forks per `docs/FORKS.md`).
3. **Do not run GPU solves or searches.** This machine is for reading/re-scoring. One BEM solve at a time is
   the owner's rule; a shared GPU box is not part of this workflow.
4. **Push rule:** any push updates `docs/CONTINUITY.md` **and** `docs/ISSUES.md` in the same commit.
5. **Branches:** `task/<NN>-<slug>` or `fix/<slug>`; PRs into `main` only, with real pasted terminal output.
6. **Read before writing:** `AGENTS.md` → `docs/CONTINUITY.md` → `docs/plan/01_CONTRACTS.md` (frozen).

---

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `404 Repository not found` | Missing `--repo-type dataset` (it defaults to `model`). The repo is public, so auth is not the issue. |
| Download crawls or stalls, then resumes | Flaky link. Re-run the same command; shards resume. Try `HF_XET_HIGH_PERFORMANCE=1`. |
| `PermissionError`/duplicate files on Windows | Symlinks need Developer Mode; set `HF_HUB_DISABLE_SYMLINKS=1`. |
| `filter` argument error on extract | Python < 3.12: use `tarfile.open(t).extractall('.')` instead. |
| Want only part of it | Add `--include "solve-*.tar"` (6.45 GB) — the cache is the useful minimum. |
| Data looks stale vs the repo | The snapshot is fixed at 2026-11-02 ~20:53 local. Later runs are **not** in it; ask the owner for a re-pack (`python tools/hf_sync.py pack --groups text,solve,dataset`). |
| Uploading your own results back | **Uploads from the owner's machine stall on the Xet path** — set `HF_HUB_DISABLE_XET=1`. Downloads are unaffected. |

---

## 8. Provenance

- Packed with `tools/hf_sync.py pack --groups text,solve,dataset` (no GPU night writing at the time: julia
  host idle, VRAM 706 MiB of 8188, newest `runs/` write 9 min before the pack).
- Uploaded with `hf upload` (7 commits, one per shard); remote sizes verified byte-identical to local.
- Anonymous access verified: `curl -r 0-2047 .../resolve/main/solve-003.tar` → `206`, 2048 bytes.
