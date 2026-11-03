# Cloud GPU runbook (RunPod-first)

2026-11-02. Operator steps to run **hornlab-search** CUDA jobs on a rented GPU.
Research basis: [`CLOUD_GPU_REPORT.md`](CLOUD_GPU_REPORT.md) (CP-9). Hardware sizing
caveats: [`evidence/HARDWARE_2026-11-01.md`](evidence/HARDWARE_2026-11-01.md).

**Defaults:** RunPod **SECURE** pod, **RTX 4090 24 GB**, Linux + CUDA. First
workload = Solana / SAWMOD **screen `run`** (not CMA search until CP-9a passes).
Suggested pilot spend cap: **~$50** (not enforced in code).

**Hardware neutrality:** cloud results must record `run.json.backend = beat_cuda`.
Do not silently swap backends. Do not pool cloud CUDA rows with Mac Metal without a
measured parity check.

## 0. One-time account setup

1. Create a [RunPod](https://www.runpod.io/) account; add a payment method.
2. Create an API key (console → Settings → API Keys).
3. Add your SSH public key to the RunPod account (Pods → SSH Public Keys).
4. Create a **network volume** in a region that has 4090s (e.g. US). Note its id.
5. On your Mac, copy the env template and fill secrets locally (never commit):

```bash
cp tools/cloud/runpod_env.example tools/cloud/.env.local   # gitignored if you keep it out of tree
# edit: RUNPOD_API_KEY, RUNPOD_NETWORK_VOLUME_ID, RUNPOD_SSH_KEY
set -a && source tools/cloud/.env.local && set +a
```

Ensure `tools/cloud/.env.local` is not tracked (`git check-ignore` or keep it outside the repo).

## 1. Push the branch the pod will clone

```bash
git push -u fork HEAD   # or origin — whichever hosts your working branch
```

## 2. Create the pod (Mac)

```bash
python tools/cloud/runpod_ctl.py create \
  --name hornlab-solana \
  --gpu "NVIDIA GeForce RTX 4090" \
  --cloud SECURE \
  --volume "$RUNPOD_NETWORK_VOLUME_ID"
```

Wait until SSH is up:

```bash
python tools/cloud/runpod_ctl.py status <POD_ID>
python tools/cloud/runpod_ctl.py ssh <POD_ID> --print-only
python tools/cloud/runpod_ctl.py ssh <POD_ID>
```

## 3. Bootstrap on the pod (once per volume / image)

```bash
export HORNLAB_CLOUD_POD_ID=<POD_ID>
cd /workspace   # or clone into /workspace/Hornfab
git clone <your-fork-url> Hornfab && cd Hornfab
git checkout feat/solana-sawmod-wg-bench   # or the branch you pushed
bash tools/cloud/bootstrap_linux.sh
```

First CUDA provision downloads several GB into `JULIA_DEPOT_PATH` /
`HORNLAB_BEAT_RUNTIME_DIR` under `/workspace` so they survive pod recycle.

## 4. CP-9a proof (required before campaigns)

```bash
bash tools/cloud/run_job.sh -- selftest --analytic
bash tools/cloud/run_job.sh -- selftest --crosscheck
```

**Pass criteria** (from CLOUD_GPU_REPORT §6):

| Check | Expect |
|---|---|
| `doctor` | green (from bootstrap) |
| `selftest --analytic` | spread about **0.02 dB** |
| `selftest --crosscheck` | about **0.04 dB** |
| After `run_job` | **no** leftover `julia` / `worker_host` processes |

Stop and terminate if these fail; do not start Solana/search.

## 5. First product job: Solana screen

Replica config: all knobs pinned — use **`run`**, not `search`.

```bash
bash tools/cloud/run_job.sh -- \
  run --config examples/typologies/solana_osse.yaml --mode screen
```

Optional SAWMOD twins:

```bash
bash tools/cloud/run_job.sh -- \
  run --config examples/typologies/sawmod_control_osse.yaml --mode screen
bash tools/cloud/run_job.sh -- \
  run --config examples/typologies/sawmod_knuckle_osse.yaml --mode screen
```

Provenance: `runs/cloud_job_<utc>.json` (pod id, GPU name, VRAM before/after, argv, git SHA).
Usual run dir: `runs/<timestamp>-screen-<id>/`.

Qualitative compare to Mac Metal `20261101T211314Z-screen-72f3bd` is allowed; **parity is not claimed**.

## 6. Pull results home and stop billing

On the Mac (from a second terminal, or after `scp`/`rsync` over the ssh endpoint):

```bash
# example — adjust user@host -p port from: runpod_ctl.py ssh POD --print-only
rsync -avz -e 'ssh -i $RUNPOD_SSH_KEY -p PORT' \
  root@HOST:/workspace/Hornfab/runs/ ./runs/cloud_pull/
```

Then:

```bash
python tools/cloud/runpod_ctl.py stop <POD_ID>        # pause compute; volume kept
# or when done with the pilot:
python tools/cloud/runpod_ctl.py terminate <POD_ID>   # wipe container disk; volume kept
```

Idle pods still bill. Prefer **stop/terminate** as soon as the job finishes.

## 7. Hygiene rules (same as local)

- **One GPU job at a time** on the pod.
- `run_job.sh` force-clears BEAT hosts before the job and `shutdown(verify=True)` after.
- POSIX orphan `julia … solver.jl --worker` processes are now discoverable by
  `hornlab_search.solve.worker.beat_host_roots` (2026-11-02).
- Do not raise dof caps or change Solana mouth geometry in the same step as the first
  cloud pilot.

## Tooling map

| Path | Role |
|---|---|
| `tools/cloud/runpod_env.example` | Env var template |
| `tools/cloud/runpod_ctl.py` | Mac: create / status / ssh / stop / terminate |
| `tools/cloud/bootstrap_linux.sh` | Pod: venv, pins, CUDA provision, doctor |
| `tools/cloud/run_job.sh` | Pod: clear hosts → CLI → verified shutdown → provenance |
| `docs/CLOUD_GPU_REPORT.md` | Cost / GPU choice research (CP-9) |
