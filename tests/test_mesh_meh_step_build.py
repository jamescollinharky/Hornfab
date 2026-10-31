"""MEH CAD -> labelled quarter STEP -> .msh (``tools/cad/meh.py`` + ``mesh/step_build.py``), task M5.

Real CAD + real gmsh, offline, CPU only. The T2-A and T1 seeds are the reference ``layout_out.md``
"Final seeds"; the mesh fixture is the 12 kHz verification mesh (final cap, quarter domain).
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from conftest import EXAMPLES, requires_build123d, requires_mesher
from hornlab_search.config import load_config
from hornlab_search.mesh import build, sizing, step_build, topology
from hornlab_search.types import GeometryInvalidError, MeshResult, MeshSpec

pytestmark = [requires_build123d, requires_mesher]

#: B&C 4NDF34 + FaitalPRO HF108 on all four walls (C9 T1). M1's driver files have not landed.
T1_RECIPE = dict(
    walls="tblr", exit_mm=25.4, cd_duct_mm=25.0, cd_body_d_mm=87.0, cd_body_len_mm=41.0,
    cone_cutout_mm=103.0, cone_depth_mm=66.0, across_frac=0.7, port_along_mm=20.0, spacer_mm=3.0,
)
#: 12 kHz quarter mesh: epw 4.2 puts the two source patches above 12 kHz (max valid 12.9-13.5 kHz)
#: while the quarter .msh stays under the FINAL cap (8,900 dofs).
MESH_12K = MeshSpec(epw=4.2, f_max_hz=12_000.0, quadrants="1", max_triangles=10**8,
                    allow_large_mesh=False)


@pytest.fixture(scope="module")
def cfg():
    return load_config(EXAMPLES / "typologies" / "multicell_3x3.yaml")


@pytest.fixture(scope="module")
def tool():
    return step_build.load_cad_tool(tool=step_build.MEH_TOOL)


def _recipe(tool, **changes):
    return {"tool": step_build.MEH_TOOL, **tool.defaults(), **changes}


@pytest.fixture(scope="module")
def t2(tool, tmp_path_factory):
    out = tmp_path_factory.mktemp("meh_t2_step")
    path = out / "cad" / step_build.MEH_STEP_FILENAME
    return step_build.build_cad_step(_recipe(tool), path), out


@pytest.fixture(scope="module")
def t1(tool, tmp_path_factory):
    out = tmp_path_factory.mktemp("meh_t1_step")
    path = out / "cad" / step_build.MEH_STEP_FILENAME
    return step_build.build_cad_step(_recipe(tool, **T1_RECIPE), path), out


@pytest.fixture(scope="module")
def mesh12(cfg, tool, tmp_path_factory):
    out = tmp_path_factory.mktemp("meh_mesh12")
    result = step_build.build_mesh_from_cad(_recipe(tool), MESH_12K, cfg, out, mode="final")
    meta = json.loads((out / "mesh_meta.json").read_text(encoding="utf-8"))
    return result, out, meta


# ------------------------------------------------------------------ inventory / labels


def test_t2_and_t1_quarter_inventory(t2, t1, tool):
    (result2, out2), (result1, out1) = t2, t1
    assert result2["inventory"] == {"driver": 1, "entry_mid": 1, "wall": 25}
    assert result1["inventory"] == {"driver": 1, "entry_mid": 2, "wall": 25}
    # the written STEP round-trips through the tool's own parser
    assert tool.read_face_inventory(out2 / "cad" / step_build.MEH_STEP_FILENAME) == result2["inventory"]
    assert tool.read_face_inventory(out1 / "cad" / step_build.MEH_STEP_FILENAME) == result1["inventory"]
    assert set(result2["inventory"]) <= set(step_build.MEH_LABELS)
    assert result2["solid"]["solids"] == 1 and result2["solid"]["valid"] is True
    assert result2["solid"]["all_shells_closed"] is True
    assert step_build.MEH_TAGS["entry_mid"] == 10 and step_build.MEH_TAGS["entry_aux"] == 11


def test_existing_cad_tools_keep_the_two_label_contract():
    assert step_build.LABELS == ("driver", "wall")
    assert step_build.CAD_TOOLS[step_build.CAD_TOOL][0] == step_build.CAD_TOOL_RELPATH
    assert step_build.CAD_TOOLS[step_build.PLUGHORN_TOOL][0] == step_build.PLUGHORN_TOOL_RELPATH
    assert step_build.CAD_TOOLS[step_build.MEH_TOOL] == (step_build.MEH_TOOL_RELPATH,
                                                        step_build.MEH_STEP_FILENAME)


# ------------------------------------------------------------------ built geometry vs derived()


def _step_vertices(path):
    import build123d as bd
    part = bd.import_step(str(path))
    return np.array([[v.X, v.Y, v.Z] for v in part.vertices()], dtype=float)


def test_mouth_and_wall_angles_of_the_step_match_derived(t2, tool):
    result, out = t2
    d = result["derived"]
    verts = _step_vertices(out / "cad" / step_build.MEH_STEP_FILENAME)
    mouth = verts[np.abs(verts[:, 2] - d["z_m"]) < 1e-3]
    throat = verts[np.abs(verts[:, 2]) < 1e-3]
    assert len(mouth) >= 3 and len(throat) >= 3
    assert 2.0 * float(mouth[:, 0].max()) == pytest.approx(d["mouth_w"], abs=0.2)
    assert 2.0 * float(mouth[:, 1].max()) == pytest.approx(d["mouth_h"], abs=0.2)
    half_w_throat = float(np.abs(throat[:, 0]).max())
    half_h_throat = float(np.abs(throat[:, 1]).max())
    cov_h = math.degrees(2.0 * math.atan((float(mouth[:, 0].max()) - half_w_throat) / d["z_m"]))
    cov_v = math.degrees(2.0 * math.atan((float(mouth[:, 1].max()) - half_h_throat) / d["z_m"]))
    assert cov_h == pytest.approx(result["params"].cov_h_deg, abs=0.05)
    assert cov_v == pytest.approx(result["params"].cov_v_deg, abs=0.05)
    # z_c is the apex distance that makes the section at z = 0 equal to the CD exit area
    a_exit = math.pi * (result["params"].exit_mm / 2.0) ** 2
    assert half_w_throat * half_h_throat == pytest.approx(a_exit / 4.0, rel=1e-6)


def _patch_faces(shell, tool, params, g, wall, sign=1):
    point, _t, n, e, _width = tool._wall_frame(wall, sign, g)
    expected = point(params.z_port_mm) + (params.port_across_mm / 4.0) * np.asarray(e, dtype=float)
    area = 0.5 * params.port_along_mm * params.port_across_mm
    hits = []
    for face in shell.faces():
        if tool._geom_name(face) != "PLANE":
            continue
        if not math.isclose(face.area, area, rel_tol=1e-3):
            continue
        fn = tool._normal(face)
        if abs(abs(float(np.dot(fn, n))) - 1.0) > 1e-6:
            continue
        if float(np.linalg.norm(tool._center(face) - expected)) > 0.5:
            continue
        hits.append(face)
    return hits, point, n, e, area


@pytest.mark.parametrize("which", ["t2", "t1"])
def test_entry_mid_faces_are_flush_inner_wall_patches(which, request, tool):
    result, _out = request.getfixturevalue(which)
    params = result["params"]
    g = tool.geometry(params)
    shell = result["part"]
    for wall in params.walls_list:
        hits, point, n, e, area = _patch_faces(shell, tool, params, g, wall, 1)
        assert len(hits) == 1, (which, wall, len(hits))
        face = hits[0]
        c = tool._center(face)
        # on the inner wall plane (and the inner side of it)
        assert abs(float(np.dot(c - point(params.z_port_mm), n))) < 1e-3
        # inside the wall's across extents: 0 <= e-coord <= width(z0) / 2
        z0 = params.z_port_mm - 0.5 * params.port_along_mm * tool._wall_frame(wall, 1, g)[1][2]
        width = tool._wall_frame(wall, 1, g)[4](z0)
        e_coord = float(np.dot(c, np.asarray(e, dtype=float)))
        assert 0.0 < e_coord < width / 2.0
        assert 5.0 < c[2] < g["z_m"] - 10.0
        # area = port_along x across / 2 (the quarter keeps one half of each port), +/- 1 %
        assert face.area == pytest.approx(area, rel=0.01)
        assert face.area == pytest.approx(params.port_along_mm * params.port_across_mm / 2.0,
                                          rel=0.01)


# ------------------------------------------------------------------ repair / refusals


def test_slide_repair_is_logged_and_exported(tool, tmp_path):
    d = tool.derived(_recipe(tool, slide_mm=-10.0))
    assert d["ok"] and d["repairs"]
    assert d["slide_mm"] == pytest.approx(32.0, abs=1e-9)
    result = tool.build(_recipe(tool, slide_mm=-10.0), tmp_path / "repaired.step")
    assert result["derived"]["slide_mm"] == pytest.approx(32.0, abs=1e-9)
    assert result["derived"]["repairs"][0]["from_mm"] == pytest.approx(-10.0)
    assert result["inventory"]["entry_mid"] == 1


def test_envelope_violation_refuses_before_writing(tool, tmp_path):
    bad = _recipe(tool, env_w_mm=300.0, env_h_mm=300.0)
    d = tool.derived(bad)
    assert d["ok"] is False and d["reasons"]
    out = tmp_path / "bad.step"
    with pytest.raises(ValueError, match="layout reasons"):
        tool.build(bad, out)
    assert not out.exists()
    with pytest.raises(GeometryInvalidError, match="layout reasons"):
        step_build.build_cad_step(bad, out)
    assert not out.exists()


def test_recipe_key_validation(tool):
    good = _recipe(tool)
    step_build.validate_cad_params(good)
    with pytest.raises(step_build.CadParamsError, match="unknown meh key"):
        step_build.validate_cad_params({**good, "bogus": 1.0})
    missing = dict(good)
    missing.pop("roll_mm")
    with pytest.raises(step_build.CadParamsError, match="missing required meh key"):
        step_build.validate_cad_params(missing)
    with pytest.raises(step_build.CadParamsError, match="cad.walls"):
        step_build.validate_cad_params({**good, "walls": "sides"})
    with pytest.raises(step_build.CadParamsError, match="finite numbers"):
        step_build.validate_cad_params({**good, "port_along_mm": "30"})
    with pytest.raises(ValueError, match="unknown meh key"):
        tool.params_from_recipe({**good, "bogus": 1.0})


def test_quadrants_must_be_the_quarter(cfg, tool, tmp_path):
    with pytest.raises(GeometryInvalidError, match="QUARTER"):
        step_build.build_mesh_from_cad(
            _recipe(tool), MeshSpec(epw=6.0, f_max_hz=2000.0, quadrants="1234",
                                    max_triangles=10**6), cfg, tmp_path, mode="screen")


# ------------------------------------------------------------------ real quarter mesh


def test_mesh_is_a_mesh_metres_quarter_mesh(mesh12, cfg):
    result, out, meta = mesh12
    assert isinstance(result, MeshResult)
    assert result.quadrants == "1"
    assert result.symmetry_plane == sizing.SYMMETRY_PLANE["1"] == "yz+xz"
    summary, xyz, tri = build.read_msh_summary(result.path, return_arrays=True)
    assert summary["tags"].get(1, 0) > 0 and summary["tags"].get(2, 0) > 0
    assert summary["tags"].get(10, 0) > 0
    assert summary["tag_names"][1] == "SD1G0"
    assert summary["tag_names"][2] == "SD1D1001"
    assert summary["tag_names"][10] == "mid_port_exit_left"
    # METRES, proven by the bbox (a mm file would be ~1000x larger and already refused)
    extent = max(summary["bbox_m"][3] - summary["bbox_m"][0],
                 summary["bbox_m"][4] - summary["bbox_m"][1],
                 summary["bbox_m"][5] - summary["bbox_m"][2])
    assert 0.10 < extent < 1.0
    # quarter symmetry: x >= 0, y >= 0 and the open edges lie on the two cut planes
    assert float(xyz[:, 0].min()) >= -1e-9
    assert float(xyz[:, 1].min()) >= -1e-9
    report = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["1"])
    assert report.bad_open_edges == 0
    assert report.nonmanifold_edges == 0
    # dof cap at f_max 12 kHz (final mode) and the 12 kHz source patches
    nodes = int(summary["n_nodes_used"])
    assert nodes <= int(cfg.mesh.dof_cap("final"))
    freq = meta["cad"]["frequency_validation"]
    for name in ("driver", "entry_mid"):
        assert freq["per_source"][name]["max_valid_frequency_hz"] >= MESH_12K.f_max_hz
    assert (out / "cad" / step_build.MEH_STEP_FILENAME).is_file()
    assert (out / "mesh.msh").is_file()


def test_mesh_meta_echoes_every_tag_area_and_centroid(mesh12, tool):
    _result, _out, meta = mesh12
    cad = meta["cad"]
    assert cad["physical_tags"] == {"1": "SD1G0", "2": "SD1D1001", "10": "mid_port_exit_left"}
    assert cad["entry_mid_surfaces"] == 1 and cad["entry_aux_surfaces"] == 0
    params = tool.params_from_recipe(_recipe(tool))
    expected_entry = 0.5 * params.port_along_mm * params.port_across_mm * 1e-6
    assert cad["tag_areas_m2"]["10"] == pytest.approx(expected_entry, rel=0.01)
    assert cad["tag_areas_m2"]["2"] > 0.0 and cad["tag_areas_m2"]["1"] > 0.0
    assert cad["tag_centroids_m"]["10"][1] > 0.0            # the surviving half is y > 0
    assert cad["tag_centroids_m"]["2"][2] == pytest.approx(-params.cd_duct_mm * 1e-3, abs=1e-4)
    assert cad["face_inventory"] == {"driver": 1, "entry_mid": 1, "wall": 25}
    assert cad["derived"]["repairs"] == [] or isinstance(cad["derived"]["repairs"], list)
    assert set(cad["derived"]["inferred_keys"]) == set(tool.INFERRED_KEYS)


def test_t1_mesh_keeps_two_entry_groups(cfg, tool, tmp_path):
    result = step_build.build_mesh_from_cad(
        _recipe(tool, **T1_RECIPE), MESH_12K, cfg, tmp_path, mode="final")
    summary = build.read_msh_summary(result.path)
    assert result.quadrants == "1" and result.symmetry_plane == "yz+xz"
    assert summary["tags"].get(2, 0) > 0 and summary["tags"].get(10, 0) > 0
    assert int(summary["n_nodes_used"]) <= int(cfg.mesh.dof_cap("final"))
    meta = json.loads((tmp_path / "mesh_meta.json").read_text(encoding="utf-8"))
    assert meta["cad"]["face_inventory"] == {"driver": 1, "entry_mid": 2, "wall": 25}
    assert meta["cad"]["entry_mid_surfaces"] == 2
