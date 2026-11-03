# M5: MEH CAD tool + multi-label STEP route (`tools/cad/meh.py`)

Model: Sonnet. Wave 1. Read `00_MEH_CONTRACTS.md` C1-C3, C9; then `tools/cad/plughorn.py` and
`hornlab_search/mesh/step_build.py` (the CAD-tool registry `CAD_TOOLS`, plughorn's validation, the labelled-STEP
contract) and the `hornlab-shape-check` skill. Reference geometry: `docs/research/typologies/mini_meh_2026-10-29/calc/meh_layout.py`
(`geometry`, `_wall_frame`, `check`, `from_fractions`, `_narrowest`). Port its logic; keep numbers identical.

## Owns

`tools/cad/meh.py`, the `meh` entry in `CAD_TOOLS` + its validation + the multi-label mapping in
`hornlab_search/mesh/step_build.py` (other tools' behaviour byte-identical), `tests/test_mesh_meh_*.py`.

## Build steps

1. `tools/cad/meh.py` (build123d, optional `cad` extra, like plughorn): `KEYS`, `defaults()`, `derived(recipe)` (no
   CAD: pure numpy layout from `meh_layout.py`, incl. repairs and reasons), `build(recipe, step_path)`.
2. Solid (L1, C9): box minus horn air (pyramid frustum from z = 0 to z_m + mouth roundover of `roll_mm`) minus the CD
   bore; imprint port outlines (rectangles of `port_along_mm` x across, centred at each port centroid on the inner
   wall, edges parallel to the wall's slant and width directions) on the inner walls; quarter cut at x = 0, y = 0.
   The box's outer depth starts at the mouth plane and runs back `env_d_mm`.
3. Labels (C3): `driver` on the bore bottom, `entry_mid` on every imprinted port face, `wall` on everything else.
   Round-trip the STEP and assert the inventory (T2 quarter: driver 1, entry_mid 1 (half of the top port);
   T1 quarter: driver 1, entry_mid 2 (half top + half right)).
4. `step_build.py`: register `"meh": ("tools/cad/meh.py", "meh.step")`; for this tool only, map `entry_mid` -> 10 and
   `entry_aux` -> 11 with the mesher's physical names (C3); refine the mesh near EVERY driven face (reuse the
   `SOURCE_TRANSITION_MM` rule); echo per-tag area + centroid and the tool's `derived()` (with repairs) into
   `mesh_meta.json`. `multicell` / `plughorn` keep "exactly one driver, labels {driver, wall}".
5. Refuse a recipe whose `derived()` reasons are non-empty (`GeometryInvalidError` with the reasons).

## Tests

- Seeds from `calc/layout_out.md` "Final seeds": T2-A and T1 layout OK; `derived()` matches `meh_layout.py` (z_c,
  z_m, mouth W x H, port z, path to diaphragm, f_h) within 0.2 mm / 1 Hz.
- Wall angles and mouth W x H of the built solid within 0.2 mm of `derived()` (probe the STEP vertices).
- Every `entry_mid` face lies on an inner wall and inside it; area = port_along x across (/2 when split) +-1 %.
- Repair: a recipe with `slide_mm = -10` that hits the CD is repaired and logged; an envelope violation refuses.
- Quarter symmetry: mesh within x >= -1e-9, y >= -1e-9; quadrants "1"; `sizing.SYMMETRY_PLANE` pairing test passes.
- Mesh (CPU, `tools/shape_check.py` style): dofs under the cap at f_max 12 kHz; bbox in metres.
- Existing `tests/test_mesh_step_build.py` and `tests/test_mesh_plughorn.py` unchanged and passing.

## Checkpoint

The new tests + `tests/test_mesh_step_build.py tests/test_mesh_plughorn.py` + the full offline suite; a render of
both seeds with the `hornlab-render` skill (`docs/renders/2026-10-30/meh/`) if build123d is available.
