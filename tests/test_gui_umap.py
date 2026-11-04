"""GUI design-cloud (UMAP/PCA) API — offline, fixture runs only."""
from __future__ import annotations

import json
import socket
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest
import yaml

from hornlab_search.gui import data as D
from hornlab_search.gui.server import App, make_handler

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "hornlab_search" / "gui" / "static"

RID = "20261103T120000Z-screen-aaa111"
HASHES = [f"{i:012x}" for i in range(1, 9)]


def _cfg() -> dict:
    return {
        "name": "umap_fixture",
        "family": "OSSE",
        "bounds": {
            "L_mm": {"lo": 100.0, "hi": 200.0},
            "a_deg": {"lo": 30.0, "hi": 50.0},
            "n": {"lo": 3.0, "hi": 7.0, "search": False},
        },
        "search": {"algorithm": "cma", "budget": 20, "seed": 1, "sigma0": 0.2},
        "mesh": {"epw": 6.0, "quadrants": "1"},
        "solve": {"backend": "beat_cpu"},
        "target": {"band_lo_hz": 300, "band_hi_hz": 5000,
                   "coverage_h_deg": 90, "coverage_v_deg": 90},
        "weights": {"cov": 1.0},
    }


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    runs = tmp_path / "runs"
    run = runs / RID
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump(_cfg()), encoding="utf-8")
    rows = []
    for i, h in enumerate(HASHES):
        # spread L and a so PCA has variance; J decreases with i for a clear best
        L = 110.0 + 10.0 * i
        a = 32.0 + 2.0 * i
        rows.append({
            "n": i,
            "design_hash": h,
            "ok": True,
            "objective": 20.0 - i,
            "mode": "screen",
            "family": "OSSE",
            "params": {"L_mm": L, "a_deg": a, "n": 5.0},
        })
    # one failure — must be ignored
    rows.append({
        "n": 99, "design_hash": "deadbeef0001", "ok": False, "objective": None,
        "error": "mesh_too_large", "params": {"L_mm": 150.0, "a_deg": 40.0},
    })
    (run / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    (run / "run.json").write_text(json.dumps({"backend": "beat_cpu"}), encoding="utf-8")
    return tmp_path


@pytest.fixture()
def server(repo: Path):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    app = App(repo, repo / "runs")
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, port))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def _req(base: str, path: str):
    import urllib.request
    u = urlparse(base)
    req = urllib.request.Request(
        base + path,
        headers={"Host": f"{u.hostname}:{u.port}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
        return resp.status, json.loads(body.decode("utf-8"))


def test_run_umap_cloud_pca_payload(repo: Path):
    d = D.run_umap_cloud(repo / "runs", RID, method="pca")
    assert d["method"] == "pca"
    assert d["keys"] == ["L_mm", "a_deg"]  # n is search:false
    assert d["n_ok"] == 8
    assert d["n_plot"] >= 1
    assert len(d["points"][0]["params"]) == 2
    assert len(d["points"][0]["u"]) == 2
    best = next(p for p in d["points"] if p["b"])
    assert best["J"] == pytest.approx(13.0)  # i=7 → J = 20 - 7
    assert "L_mm" in d["bounds"] and d["bounds"]["L_mm"]["lo"] == 100.0


def test_run_umap_cloud_rejects_bad_method(repo: Path):
    with pytest.raises(ValueError, match="method"):
        D.run_umap_cloud(repo / "runs", RID, method="tsne")


def test_run_umap_route(server: str):
    code, body = _req(server, f"/api/umap/{RID}?method=pca")
    assert code == 200
    assert body["method"] == "pca"
    assert body["n_ok"] == 8
    assert isinstance(body["points"], list) and body["points"]


def test_umap_js_wired_in_app():
    app = (STATIC / "app.js").read_text(encoding="utf-8")
    umap = (STATIC / "umap.js").read_text(encoding="utf-8")
    assert 'from "./umap.js"' in app
    assert 'viewUmap' in app
    assert "/umap" in app
    assert 'Design cloud' in app
    assert 'fetch("/api/umap/"' in umap
    assert "export async function viewUmap" in umap
