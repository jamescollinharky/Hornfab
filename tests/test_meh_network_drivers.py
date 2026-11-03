"""Tests for the MEH driver models and lumped network (contracts C6/C7/C8/C12).

The reference implementations are imported **by file path** (never from package code):
``docs/research/typologies/mini_meh_2026-10-29/calc/meh_1d_sketch.py`` and ``.../meh_zmatrix_check.py``.
Driver fixtures are written into ``tmp_path``; no driver YAML is committed by this work package.
"""
from __future__ import annotations

import importlib.util
import math
import sys
import types
from pathlib import Path

import numpy as np
import pytest
import yaml

from hornlab_search.constants import C_AIR, RHO_AIR
from hornlab_search.meh import drivers, network as net

# ------------------------------------------------------------------ reference imports by path

REPO = Path(__file__).resolve().parents[1]
CALC = REPO / "docs" / "research" / "typologies" / "mini_meh_2026-10-29" / "calc"


def _load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module          # meh_zmatrix_check imports ``meh_1d_sketch`` by name
    spec.loader.exec_module(module)
    return module


sketch = _load_by_path("meh_1d_sketch", CALC / "meh_1d_sketch.py")
zcheck = _load_by_path("meh_zmatrix_check", CALC / "meh_zmatrix_check.py")


def _cone_from_sketch(c) -> drivers.ConeDriver:
    """A ConeDriver that is numerically identical to the sketch's Cone.

    The sketch puts ``c.mms`` directly in Zm; C7 asks for the dry ``Mmd``. Supplying that value as
    ``mmd_kg`` (and the exact Cms/Rms) makes ``mmd_eff_kg == c.mms`` and removes all ambiguity.
    """
    return drivers.ConeDriver(
        name=c.name,
        re_ohm=c.re,
        le_h=c.le,
        bl_tm=c.bl,
        sd_m2=c.sd,
        xmax_m=c.xmax,
        p_aes_w=100.0,
        fs_hz=c.fs,
        qms=c.qms,
        rms_kg_s=c.rms,
        mmd_kg=c.mms,
        mms_kg=c.mms,
        cms_m_per_n=c.cms,
    )


# ------------------------------------------------------------------ entry Norton

@pytest.mark.parametrize(
    "cone, n, v_front, s_port, l_port, v_rear",
    [
        (sketch.MID4, 4, 30e-6, 12e-4, 0.012, 1.0e-3),
        (sketch.MID65, 2, 120e-6, 25e-4, 0.012, 4.0e-3),
    ],
    ids=["MID4", "MID65"],
)
def test_entry_norton_matches_sketch(cone, n, v_front, s_port, l_port, v_rear):
    """``entry_norton(n_end=2)`` == ``Entry.norton`` for 60 frequencies, rel 1e-12."""
    freqs = np.geomspace(100.0, 8000.0, 60)
    entry = sketch.Entry(cone, n=n, z=0.1, v_front=v_front, s_port=s_port, l_port=l_port, v_rear=v_rear)
    e_volts = 2.83

    ref = np.array([entry.norton(f, e_volts) for f in freqs], dtype=complex)
    u_ref, y_ref = ref[:, 0], ref[:, 1]

    u, y = net.entry_norton(freqs, _cone_from_sketch(cone), n, v_front, s_port, l_port, v_rear,
                            e_volts, n_end=2)

    assert u.dtype == np.complex128 and y.dtype == np.complex128
    np.testing.assert_allclose(u, u_ref, rtol=1e-12, atol=0.0)
    np.testing.assert_allclose(y, y_ref, rtol=1e-12, atol=0.0)


# ------------------------------------------------------------------ coupling vs direct solve

def _bare_hz(horn, entries, f):
    """(Z, H) of ``meh_zmatrix_check.bare_injection`` at one frequency, in the sketch's convention."""
    zs = [e.z for e in entries]
    n = len(entries) + 1
    z_mat = np.zeros((n, n), dtype=complex)
    h = np.zeros(n, dtype=complex)
    for j in range(n):
        z_mat[:, j], h[j] = zcheck.bare_injection(horn, zs, j, f)
    return z_mat, h


@pytest.mark.parametrize("n_groups", [1, 2])
def test_couple_reproduces_direct_solve(n_groups):
    """``couple`` fed the bare-horn H/Z matches the sketch's direct solve, rel 1e-9."""
    horn = sketch.Horn(90.0, 60.0, depth=0.22)
    a4 = sketch.Entry(sketch.MID4, n=4, z=0.065, v_front=30e-6, s_port=12e-4,
                      l_port=0.012, v_rear=1.0e-3)
    w65 = sketch.Entry(sketch.MID65, n=2, z=0.15, v_front=120e-6, s_port=25e-4,
                       l_port=0.012, v_rear=4.0e-3)
    entries = [a4] if n_groups == 1 else [a4, w65]
    freqs = np.geomspace(100.0, 8000.0, 25)
    e_volts, u_cd = 2.83, 1e-4

    for f in freqs:
        z_mat, h = _bare_hz(horn, entries, f)
        u_sc = np.array([e.norton(f, e_volts)[0] for e in entries])
        y = np.array([e.norton(f, e_volts)[1] for e in entries])

        u_net = net.couple(z_mat[None, :, :], u_sc[None, :], y[None, :], np.array([u_cd]))
        assert u_net.shape == (1, len(entries) + 1)
        assert u_net[0, 0] == u_cd

        u_dir, p_throat, p_entries = sketch.solve(horn, entries, f, u_cd, [e_volts] * len(entries))
        u_dec = h[0] * u_cd + h[1:] @ u_net[0, 1:]
        assert abs(u_dec / u_dir - 1.0) <= 1e-9

        p_rec = z_mat[:, 0] * u_cd + z_mat[:, 1:] @ u_net[0, 1:]
        assert abs(p_rec[0] / p_throat - 1.0) <= 1e-9
        for i in range(len(entries)):
            assert abs(p_rec[i + 1] / p_entries[i] - 1.0) <= 1e-9


# ------------------------------------------------------------------ mmd_from_mms

@pytest.mark.parametrize(
    "mms_g, sd_cm2, expected_g",
    [(14.0, 149.0, 11.9), (4.2, 51.9, 3.8)],
    ids=["FaitalPRO_6FE100", "FaitalPRO_4FE32"],
)
def test_mmd_from_mms(mms_g, sd_cm2, expected_g):
    assert abs(drivers.mmd_from_mms(mms_g, sd_cm2) - expected_g) <= 0.1


# ------------------------------------------------------------------ from_bem

def _fake_response(freqs, tags, areas, cp, im):
    return types.SimpleNamespace(
        freqs_hz=np.asarray(freqs, dtype=float),
        channel_tags=tuple(tags),
        tag_areas_m2=dict(areas),
        channel_pressure=np.asarray(cp),
        impedance_matrix=np.asarray(im),
    )


def test_from_bem_known_per_acceleration_values():
    freqs = np.array([50.0, 500.0, 5000.0])
    tags = (2, 10)
    areas = {2: 1.2e-3, 10: 2.4e-4}
    n_f, n_c, n_p, n_a = freqs.size, len(tags), 2, 3

    cp = (np.arange(n_f * n_c * n_p * n_a, dtype=float).reshape(n_f, n_c, n_p, n_a)
          + 1j * np.arange(100, 100 + n_f * n_c * n_p * n_a, dtype=float).reshape(n_f, n_c, n_p, n_a))
    im = (np.arange(n_f * n_c * n_c, dtype=float).reshape(n_f, n_c, n_c)
          + 1j * np.arange(200, 200 + n_f * n_c * n_c, dtype=float).reshape(n_f, n_c, n_c))

    h_net, z_net, out_freqs = net.from_bem(_fake_response(freqs, tags, areas, cp, im))
    assert h_net.dtype == np.complex128 and z_net.dtype == np.complex128
    np.testing.assert_array_equal(out_freqs, freqs)
    assert h_net.shape == (n_f, n_c, n_p, n_a)
    assert z_net.shape == (n_f, n_c, n_c)

    w = 2.0 * np.pi * freqs
    area_c = np.array([areas[t] for t in tags])
    expected_h = np.zeros_like(cp)
    for c in range(n_c):
        expected_h[:, c] = np.conj(cp[:, c] * (-1j * w)[:, None, None] / area_c[c])
    expected_z = np.zeros_like(im)
    for j in range(n_c):
        expected_z[:, :, j] = np.conj(im[:, :, j] * (-1j * w)[:, None] / area_c[j])

    np.testing.assert_allclose(h_net, expected_h, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(z_net, expected_z, rtol=0.0, atol=0.0)


def test_from_bem_symmetric_force_matrix_gives_symmetric_z_net():
    freqs = np.array([100.0, 1000.0, 4000.0])
    tags = (2, 10, 11)
    area = 2.5e-3
    areas = {t: area for t in tags}
    rng = np.random.default_rng(20261031)
    n = len(tags)
    im = np.zeros((freqs.size, n, n), dtype=complex)
    cp = np.zeros((freqs.size, n, 2, 3), dtype=complex)
    for k in range(freqs.size):
        m = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
        im[k] = m + m.T          # deliberately symmetric force matrix
        cp[k] = 1.0 + 0.5j

    _, z_net, _ = net.from_bem(_fake_response(freqs, tags, areas, cp, im))
    np.testing.assert_allclose(z_net, np.swapaxes(z_net, 1, 2), rtol=1e-15, atol=0.0)
    assert np.max(np.abs(z_net[:, 0, 1])) > 0.0


def test_from_bem_requires_meh_fields():
    with pytest.raises(ValueError, match="MEH channel fields"):
        net.from_bem(types.SimpleNamespace(freqs_hz=np.array([100.0])))


# ------------------------------------------------------------------ energy balance

def test_energy_balance_one_entry_into_resistive_load():
    """Electrical power in == Re-loss + Rms-loss + port-loss + acoustic power out, rel 1e-9."""
    cone = _cone_from_sketch(sketch.MID65)
    n = 2
    v_front, s_port, l_port, v_rear = 120e-6, 25e-4, 0.012, 4.0e-3
    q_port = 10.0
    load_r = 1.0e6                    # purely resistive horn load, Pa per (m^3/s)
    e_volts = 2.83
    freqs = np.geomspace(100.0, 5000.0, 12)

    u_sc, y = net.entry_norton(freqs, cone, n, v_front, s_port, l_port, v_rear, e_volts,
                               n_end=1, q_port=q_port)
    u_group = u_sc / (1.0 + y * load_r)       # U = U_sc - Y Z_load U
    u_out = u_group / n                        # per driver through its port
    p_horn = load_r * u_group

    v = net.cone_velocity_rms(freqs, cone, n, v_front, s_port, l_port, v_rear, e_volts,
                              p_horn, n_end=1, q_port=q_port)

    w = 2.0 * np.pi * freqs
    ze = cone.re_ohm + 1j * w * cone.le_h
    i_coil = (e_volts - cone.bl_tm * v) / ze

    r_eq = math.sqrt(s_port / math.pi)
    l_eff = l_port + 0.85 * r_eq                  # n_end = 1
    x_port = w * RHO_AIR * l_eff / s_port
    z_port = 1j * x_port + x_port / q_port

    p_electrical = n * np.real(e_volts * np.conj(i_coil))
    p_coil_loss = n * cone.re_ohm * np.abs(i_coil) ** 2
    p_rms_loss = n * cone.rms_kg_s * np.abs(v) ** 2
    p_port_loss = n * np.real(z_port) * np.abs(u_out) ** 2
    p_acoustic_out = np.real(load_r) * np.abs(u_group) ** 2
    p_sum = p_coil_loss + p_rms_loss + p_port_loss + p_acoustic_out

    assert np.all(p_electrical > 0.0)
    assert np.all(np.abs(p_electrical - p_sum) <= 1e-9 * np.abs(p_electrical))


# ------------------------------------------------------------------ CD source / conversions

def test_cd_volume_velocity_is_mass_controlled():
    cd = drivers.CDSource(
        name="test CD", exit_mm=35.8, p_aes_w=80.0, min_xo_hz=700.0, sens_db_1w=110.0,
        body_d_mm=124.0, body_len_mm=75.0, fs_cd_hz=500.0, q_cd=1.0,
    )
    f_lo = np.array([1.0, 2.0])
    low = np.abs(net.cd_volume_velocity(f_lo, cd, 1.0))
    assert low[1] / low[0] == pytest.approx(2.0, rel=1e-2)     # mass-controlled below fs: |U| ~ f

    f_hi = np.array([50_000.0, 100_000.0])
    high = np.abs(net.cd_volume_velocity(f_hi, cd, 1.0))
    assert high[1] / high[0] == pytest.approx(0.5, rel=1e-3)  # above fs: |U| ~ 1/f


def test_excursion_and_port_velocity_conversions():
    f = np.array([100.0])
    exc = net.cone_excursion_peak_mm(f, np.array([1.0 + 0.0j]))
    assert exc[0] == pytest.approx(math.sqrt(2.0) / (2.0 * math.pi * 100.0) * 1e3, rel=1e-15)

    v_port = net.port_velocity_peak(np.array([1.0e-4 + 0.0j]), 1.0e-3)
    assert v_port[0] == pytest.approx(math.sqrt(2.0) * 1.0e-4 / 1.0e-3, rel=1e-15)


# ------------------------------------------------------------------ driver loaders (fixtures in tmp_path)

def _write_yaml(directory: Path, stem: str, data: dict) -> Path:
    path = directory / f"{stem}.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _cone_data() -> dict:
    return {
        "name": "Test 6.5-inch mid",
        "kind": "cone",
        "re_ohm": 5.5,
        "le_mh": 0.2,
        "bl_tm": 9.0,
        "sd_cm2": 135.0,
        "xmax_mm": 4.0,
        "p_aes_w": 100.0,
        "fs_hz": 80.0,
        "qms": 5.0,
        "mmd_g": 12.0,
        "cms_mm_per_n": 0.3,
        "cutout_mm": 145.0,
        "depth_mm": 85.0,
        "source": "https://example.invalid/test-cone.pdf",
    }


def _cd_data() -> dict:
    return {
        "name": "Test 1.4-inch CD",
        "kind": "compression_meh",
        "exit_mm": 35.8,
        "p_aes_w": 80.0,
        "min_xo_hz": 700.0,
        "sens_db_1w": 110.0,
        "body_d_mm": 124.0,
        "body_len_mm": 75.0,
        "source": "https://example.invalid/test-cd.pdf",
    }


def test_load_cone_from_yaml(tmp_path):
    _write_yaml(tmp_path, "test_cone", _cone_data())
    cone = drivers.load_cone("test_cone", directory=tmp_path)

    assert isinstance(cone, drivers.ConeDriver)
    assert cone.kind == "cone"
    assert cone.name == "Test 6.5-inch mid"
    assert cone.re_ohm == 5.5
    assert cone.le_h == pytest.approx(0.2e-3)
    assert cone.bl_tm == 9.0
    assert cone.sd_m2 == pytest.approx(135.0e-4)
    assert cone.mmd_eff_kg == pytest.approx(12.0e-3)
    assert cone.mms_kg == pytest.approx(12.0e-3 + cone.air_load_kg)
    assert cone.cms_m_per_n == pytest.approx(0.3e-3)
    assert cone.rms_kg_s == pytest.approx(2.0 * math.pi * 80.0 * cone.mms_kg / 5.0)
    assert cone.vas_l > 0.0


def test_load_cd_from_yaml_defaults(tmp_path):
    _write_yaml(tmp_path, "test_cd", _cd_data())
    cd = drivers.load_cd("test_cd", directory=tmp_path)

    assert isinstance(cd, drivers.CDSource)
    assert cd.kind == "compression_meh"
    assert cd.fs_cd_hz == pytest.approx(700.0 / 1.4)
    assert cd.q_cd == 1.0
    assert cd.di_ref_db == 10.0
    assert cd.duct_mm == 0.0
    assert cd.s_exit_m2 == pytest.approx(math.pi * (35.8e-3 / 2.0) ** 2)


def test_load_cone_refuses_wrong_kind(tmp_path):
    data = _cone_data()
    data["kind"] = "compression_meh"
    _write_yaml(tmp_path, "wrong_cone", data)
    with pytest.raises(ValueError, match="kind"):
        drivers.load_cone("wrong_cone", directory=tmp_path)


def test_load_cd_refuses_wrong_kind(tmp_path):
    data = _cd_data()
    data["kind"] = "cone"
    _write_yaml(tmp_path, "wrong_cd", data)
    with pytest.raises(ValueError, match="kind"):
        drivers.load_cd("wrong_cd", directory=tmp_path)
