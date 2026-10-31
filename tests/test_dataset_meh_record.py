"""MEH additive record content (docs/meh/00_MEH_CONTRACTS.md C5/C12).

A record carrying the multi-source Response fields stores the three complex arrays in the npz and
the two tag metadata keys + the chosen NetworkSolution JSON in the metadata; a single-source record
is byte-identical to before (no new metadata keys, no new arrays). Old records load unchanged.
"""
from __future__ import annotations

import numpy as np

from hornlab_search.dataset.record import ARRAY_KEYS, build_record, validate_record
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.types import Response
from test_dataset_factory import GRID, LIB_SHAS, TARGET, make_eval, solve_spec

MEH_ARRAYS = ("channel_pressure", "channel_sphere_pressure", "impedance_matrix")

NETWORK_SOLUTION = {
    "cd": "faitalpro_hf1440", "mid": "bc_6ndl38", "xo_hz": 950.0, "xo_order": 4,
    "mid_delay_ms": 0.35, "mid_polarity": 1, "gains_db": {"cd": 0.0, "mid": -3.5},
    "v_front_m3": 0.0004, "v_rear_m3": 0.0021, "eq_db": [0.0, 1.5, 0.0],
    "spl_max_db": [118.0, 121.5], "inner_J": 2.75, "n_evals": 1200, "seed": 7,
}


def _meh_response(resp: Response, nch: int = 2) -> Response:
    """Attach contract-shaped MEH fields to a fake Response (deterministic, distinct)."""
    nf, na = resp.spl_h_db.shape
    nb = resp.spl_balloon_db.shape[1]
    rng = np.random.default_rng(11)
    resp.channel_tags = (2, 10)[:nch]
    resp.channel_pressure = (
        rng.normal(size=(nf, nch, 2, na)) + 1j * rng.normal(size=(nf, nch, 2, na))
    ).astype(np.complex128)
    resp.channel_sphere_pressure = (
        rng.normal(size=(nf, nch, nb)) + 1j * rng.normal(size=(nf, nch, nb))).astype(np.complex128)
    resp.impedance_matrix = (
        rng.normal(size=(nf, nch, nch)) + 1j * rng.normal(size=(nf, nch, nch))).astype(np.complex128)
    resp.tag_areas_m2 = {2: 0.0012, 10: 0.0008}
    return resp


def _meh_eval():
    ev = make_eval(3)
    ev.outcome.response = _meh_response(ev.outcome.response)
    return ev


def test_meh_arrays_and_metadata_are_stored():
    ev = _meh_eval()
    meta, arrays = build_record(ev, TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID,
                                area_m2=0.125, created_utc="2026-10-30T00:00:00Z",
                                network_solution=NETWORK_SOLUTION)
    validate_record(meta)
    assert set(MEH_ARRAYS) <= set(ARRAY_KEYS)
    for name in MEH_ARRAYS:
        assert name in arrays
        assert np.array_equal(arrays[name], getattr(ev.outcome.response, name))
        assert arrays[name].dtype == np.complex128
    assert meta["channel_tags"] == [2, 10]
    assert meta["tag_areas_m2"] == {"2": 0.0012, "10": 0.0008}
    assert meta["network_solution"] == NETWORK_SOLUTION
    assert meta["schema_version"] == 1        # additive only: no schema bump


def test_network_solution_is_absent_when_not_supplied():
    meta, _ = build_record(_meh_eval(), TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID,
                           area_m2=0.125, created_utc="2026-10-30T00:00:00Z")
    validate_record(meta)
    assert "network_solution" not in meta


def test_single_source_record_is_unchanged():
    meta, arrays = build_record(make_eval(3), TARGET, LIB_SHAS, solve_spec=solve_spec(),
                                grid=GRID, area_m2=0.125,
                                created_utc="2026-10-30T00:00:00Z")
    validate_record(meta)
    for key in ("channel_tags", "tag_areas_m2", "network_solution"):
        assert key not in meta
    for name in MEH_ARRAYS:
        assert name not in arrays


def test_store_round_trips_the_meh_arrays(tmp_path):
    ev = _meh_eval()
    meta, arrays = build_record(ev, TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID,
                                area_m2=0.125, created_utc="2026-10-30T00:00:00Z",
                                network_solution=NETWORK_SOLUTION)
    store = DatasetStore(tmp_path / "dataset")
    store.append(meta, arrays)
    got_meta, got_arrays = store.read(0, 0)
    assert got_meta == meta
    validate_record(got_meta)
    for name in MEH_ARRAYS:
        assert got_arrays[name].dtype == arrays[name].dtype
        assert got_arrays[name].shape == arrays[name].shape
        assert got_arrays[name].tobytes() == arrays[name].tobytes()
    assert got_meta["network_solution"] == NETWORK_SOLUTION
