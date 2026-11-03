#!/usr/bin/env python3
"""Thin RunPod GraphQL client for hornlab-search cloud GPU pods.

Mac/dev-side only. Auth: RUNPOD_API_KEY in the environment (never commit keys).

  python tools/cloud/runpod_ctl.py create [--name NAME] [--gpu TYPE] [--volume ID]
  python tools/cloud/runpod_ctl.py status POD_ID
  python tools/cloud/runpod_ctl.py ssh POD_ID
  python tools/cloud/runpod_ctl.py stop POD_ID
  python tools/cloud/runpod_ctl.py terminate POD_ID

See docs/CLOUD_GPU_RUNBOOK.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

API_URL = "https://api.runpod.io/graphql"

DEFAULT_GPU = os.environ.get("RUNPOD_GPU_TYPE_ID", "NVIDIA GeForce RTX 4090")
DEFAULT_CLOUD = os.environ.get("RUNPOD_CLOUD_TYPE", "SECURE")
DEFAULT_IMAGE = os.environ.get(
    "RUNPOD_IMAGE",
    "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04",
)
DEFAULT_NAME = os.environ.get("RUNPOD_NAME", "hornlab-search")
DEFAULT_DISK_GB = int(os.environ.get("RUNPOD_CONTAINER_DISK_GB", "40"))
DEFAULT_VOLUME_MOUNT = os.environ.get("RUNPOD_VOLUME_MOUNT", "/workspace")


class RunPodError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not key:
        raise RunPodError(
            "RUNPOD_API_KEY is not set. Copy tools/cloud/runpod_env.example and export the key."
        )
    return key


def graphql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"query": query, "variables": variables or {}}
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_api_key()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RunPodError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RunPodError(f"network error: {exc}") from exc
    if body.get("errors"):
        raise RunPodError(json.dumps(body["errors"], indent=2))
    return body.get("data") or {}


def cmd_create(args: argparse.Namespace) -> int:
    gpu = args.gpu or DEFAULT_GPU
    cloud = (args.cloud or DEFAULT_CLOUD).upper()
    if cloud not in ("SECURE", "COMMUNITY"):
        raise RunPodError(f"cloud must be SECURE or COMMUNITY, got {cloud!r}")
    volume_id = args.volume or os.environ.get("RUNPOD_NETWORK_VOLUME_ID") or None
    name = args.name or DEFAULT_NAME
    image = args.image or DEFAULT_IMAGE

    # GraphQL input for on-demand deploy (RunPod public schema).
    inp: dict[str, Any] = {
        "cloudType": cloud,
        "gpuCount": 1,
        "volumeInGb": 0,
        "containerDiskInGb": args.disk_gb or DEFAULT_DISK_GB,
        "minVcpuCount": args.min_vcpu,
        "minMemoryInGb": args.min_ram_gb,
        "gpuTypeId": gpu,
        "name": name,
        "imageName": image,
        "dockerArgs": "",
        "ports": "22/tcp",
        "volumeMountPath": DEFAULT_VOLUME_MOUNT,
        "env": [
            {"key": "HORNLAB_CLOUD_POD_ID", "value": "pending"},
        ],
    }
    if volume_id:
        inp["networkVolumeId"] = volume_id

    mutation = """
    mutation Create($input: PodFindAndDeployOnDemandInput!) {
      podFindAndDeployOnDemand(input: $input) {
        id
        name
        imageName
        machineId
        desiredStatus
        costPerHr
        machine { podHostId }
      }
    }
    """
    data = graphql(mutation, {"input": inp})
    pod = data.get("podFindAndDeployOnDemand")
    if not pod:
        raise RunPodError(f"create returned no pod: {json.dumps(data)}")
    # Patch env with real pod id via stop/start is awkward; print for the operator.
    print(json.dumps(pod, indent=2))
    print(
        f"\n# next: wait until RUNNING, then:\n"
        f"#   python tools/cloud/runpod_ctl.py ssh {pod['id']}\n"
        f"# On the pod: export HORNLAB_CLOUD_POD_ID={pod['id']}\n"
        f"#   bash tools/cloud/bootstrap_linux.sh\n",
        file=sys.stderr,
    )
    return 0


def _pod(pod_id: str) -> dict[str, Any]:
    query = """
    query Pod($id: String!) {
      pod(input: {podId: $id}) {
        id
        name
        desiredStatus
        lastStatusChange
        imageName
        costPerHr
        machine { podHostId gpuDisplayName }
        runtime {
          uptimeInSeconds
          ports { ip isIpPublic privatePort publicPort type }
          gpus { id gpuUtilPercent memoryUtilPercent }
        }
      }
    }
    """
    data = graphql(query, {"id": pod_id})
    pod = data.get("pod")
    if not pod:
        raise RunPodError(f"pod not found: {pod_id}")
    return pod


def cmd_status(args: argparse.Namespace) -> int:
    print(json.dumps(_pod(args.pod_id), indent=2))
    return 0


def _ssh_endpoint(pod: dict[str, Any]) -> tuple[str, int]:
    runtime = pod.get("runtime") or {}
    ports = runtime.get("ports") or []
    for p in ports:
        if int(p.get("privatePort") or 0) == 22 and p.get("ip"):
            return str(p["ip"]), int(p["publicPort"])
    # Fallback: some pods expose a single public IP via machine.podHostId + proxy.
    raise RunPodError(
        "no public SSH port (22/tcp) in runtime yet — wait until desiredStatus is RUNNING "
        "and status shows ports, then retry ssh"
    )


def cmd_ssh(args: argparse.Namespace) -> int:
    pod = _pod(args.pod_id)
    host, port = _ssh_endpoint(pod)
    key = args.identity or os.environ.get("RUNPOD_SSH_KEY") or os.path.expanduser("~/.ssh/id_ed25519")
    user = args.user
    cmd = f"ssh -i {key} -p {port} -o StrictHostKeyChecking=accept-new {user}@{host}"
    if args.print_only:
        print(cmd)
        return 0
    print(cmd, file=sys.stderr)
    os.execvp("ssh", ["ssh", "-i", key, "-p", str(port),
                      "-o", "StrictHostKeyChecking=accept-new", f"{user}@{host}"])
    return 0  # pragma: no cover


def cmd_stop(args: argparse.Namespace) -> int:
    mutation = """
    mutation Stop($id: String!) {
      podStop(input: {podId: $id}) { id desiredStatus }
    }
    """
    print(json.dumps(graphql(mutation, {"id": args.pod_id}), indent=2))
    return 0


def cmd_terminate(args: argparse.Namespace) -> int:
    mutation = """
    mutation Term($id: String!) {
      podTerminate(input: {podId: $id})
    }
    """
    print(json.dumps(graphql(mutation, {"id": args.pod_id}), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="runpod_ctl", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="deploy an on-demand GPU pod")
    c.add_argument("--name", default=None)
    c.add_argument("--gpu", default=None, help=f"gpuTypeId (default {DEFAULT_GPU})")
    c.add_argument("--cloud", default=None, help="SECURE or COMMUNITY")
    c.add_argument("--image", default=None)
    c.add_argument("--volume", default=None, help="network volume id")
    c.add_argument("--disk-gb", type=int, default=None)
    c.add_argument("--min-vcpu", type=int, default=8)
    c.add_argument("--min-ram-gb", type=int, default=32)
    c.set_defaults(func=cmd_create)

    s = sub.add_parser("status", help="show pod JSON")
    s.add_argument("pod_id")
    s.set_defaults(func=cmd_status)

    sh = sub.add_parser("ssh", help="print or exec SSH to the pod")
    sh.add_argument("pod_id")
    sh.add_argument("-i", "--identity", default=None)
    sh.add_argument("--user", default="root")
    sh.add_argument("--print-only", action="store_true",
                    help="print the ssh command only (default: exec)")
    sh.set_defaults(func=cmd_ssh)

    st = sub.add_parser("stop", help="stop pod (keeps volume; billing may pause)")
    st.add_argument("pod_id")
    st.set_defaults(func=cmd_stop)

    t = sub.add_parser("terminate", help="terminate pod (disk wiped; volume kept)")
    t.add_argument("pod_id")
    t.set_defaults(func=cmd_terminate)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except RunPodError as exc:
        print(f"runpod_ctl: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
