#!/usr/bin/env bash
# Idempotent on-pod bootstrap for hornlab-search CUDA (RunPod / Linux).
# Run from the repo root on the pod:
#   bash tools/cloud/bootstrap_linux.sh
#
# Expects: NVIDIA driver + CUDA-capable GPU, git, python3.11|3.12.
# Puts Julia depot + BEAT runtime on /workspace when that mount exists
# so network volumes survive pod recycle.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# gmsh (round-trip / mesh) needs libGLU on headless CUDA images
if command -v apt-get >/dev/null 2>&1 && ! ldconfig -p 2>/dev/null | grep -q 'libGLU\.so\.1'; then
  echo "bootstrap: installing libGLU / X11 libs for gmsh"
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    libglu1-mesa libgl1 libxrender1 libxcursor1 libxft2 libxinerama1 rsync >/dev/null
fi

WORKSPACE="${HORNLAB_CLOUD_WORKSPACE:-}"
if [[ -z "$WORKSPACE" ]]; then
  if [[ -d /workspace ]]; then
    WORKSPACE=/workspace
  else
    WORKSPACE="$REPO_ROOT"
  fi
fi

export JULIA_DEPOT_PATH="${JULIA_DEPOT_PATH:-$WORKSPACE/julia-depot}"
export HORNLAB_BEAT_RUNTIME_DIR="${HORNLAB_BEAT_RUNTIME_DIR:-$WORKSPACE/hornlab-beat-runtime}"
mkdir -p "$JULIA_DEPOT_PATH" "$HORNLAB_BEAT_RUNTIME_DIR"

PYTHON_BIN="${HORNLAB_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for c in python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      PYTHON_BIN="$(command -v "$c")"
      break
    fi
  done
fi
if [[ -z "${PYTHON_BIN:-}" ]]; then
  echo "bootstrap: no python3 found" >&2
  exit 1
fi
PY_VER="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
case "$PY_VER" in
  3.11|3.12) ;;
  *)
    echo "bootstrap: need Python 3.11 or 3.12, got $PY_VER ($PYTHON_BIN)" >&2
    exit 1
    ;;
esac

VENV="${HORNLAB_VENV:-$REPO_ROOT/.venv}"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "bootstrap: creating venv at $VENV"
  "$PYTHON_BIN" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

python -m pip install -U pip wheel setuptools
# Editable install pulls pinned hornlab-* SHAs from pyproject.toml.
# Default extras include crosscheck (bempp) so CP-9a can run on a fresh pod.
EXTRAS="${HORNLAB_PIP_EXTRAS:-crosscheck}"
python -m pip install -e ".[${EXTRAS}]"

echo "bootstrap: provisioning beat CUDA runtime (may download several GB on first run)"
python -m hornlab_beat_bem.provision --backend cuda

echo "bootstrap: doctor"
python -m hornlab_search.cli doctor

echo "bootstrap: OK"
echo "  REPO_ROOT=$REPO_ROOT"
echo "  VENV=$VENV"
echo "  JULIA_DEPOT_PATH=$JULIA_DEPOT_PATH"
echo "  HORNLAB_BEAT_RUNTIME_DIR=$HORNLAB_BEAT_RUNTIME_DIR"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
fi
