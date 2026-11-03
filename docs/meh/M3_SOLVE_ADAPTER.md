# M3: hornlab-search solve adapter for several source tags

Model: Sonnet. Wave 1 (codes against C4/C5 with fakes; the real fork lands via M8's pin bump). Read
`00_MEH_CONTRACTS.md` C4-C5, then `hornlab_search/solve/beat.py`, `hornlab_search/types.py`, `tests/test_solve_fake.py`,
`hornlab_search/dataset/record.py`.

## Owns

Additive fields in `hornlab_search/types.py::Response`; the MEH path in `solve/beat.py`; additive optional fields in
`dataset/record.py`; `tests/test_solve_meh_*.py`, `tests/test_dataset_meh_*.py`.

## Build steps

1. `types.py`: add the C5 optional fields (default `None`); no existing field changes.
2. `solve/beat.py::make_config`: if `spec.extra.get("source_tags")` -> `velocity_sources = {t: 1.0 for t in tags}`,
   `impedance_matrix=True`; refuse (ConfigError) when the installed `SolveConfig` lacks `impedance_matrix` (old pin),
   with a message naming M8's pin bump. Absent key = today's config byte-for-byte (the solve hash must not change).
3. Result conversion: copy `channel_tags`, `channel_pressure`, `channel_sphere_pressure`, `impedance_matrix`,
   `tag_areas_m2` into `Response`; legacy fields unchanged (channel 0 = CD).
4. `check_symmetry_pairing` and the bbox check apply unchanged; additionally assert every requested tag exists in
   the mesh (`mesh_meta` per-tag areas from M5) before any worker starts.
5. `dataset/record.py`: store the new arrays when present (optional fields, record version note), plus the chosen
   `NetworkSolution` JSON (M7 fills it); old records load unchanged.
6. bempp cross-check path: refuse `source_tags` (not supported yet) with a clear message.

## Tests

- Fake `hornlab_beat_bem` (pattern of `tests/test_solve_fake.py`): single-tag config identical to today (dict
  compare incl. absence of new keys); multi-tag config carries all tags + `impedance_matrix=True`; a fake 2-channel
  result lands in `Response` with the right shapes; legacy fields = channel 0.
- Solve-hash / cache-key for an existing config unchanged (golden value from the current code).
- Dataset round trip with and without the new fields.

## Checkpoint

New tests + `tests/test_solve_fake.py` + dataset tests + the full offline suite.
