# M9: Boundary Lab export + cross-check (refinement level L3)

Model: Sonnet. Wave 3, after M8 produced finalist meshes. BL lives in its OWN environment (it pins BEAT 0.6.0
exactly); call it as a subprocess. Read `docs/BOUNDARY_LAB_0.5_RESEARCH.md`, `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`,
dossier s7.4, and BL's `examples/Multi_region_SAWMOD/Multi_region_SAWMOD.blab.json` (the template: coupled FEM
regions, electrodynamic transducers, voltage ports, interfaces, channels, symmetry xy).

## Owns

`tools/bl_export_meh.py`, `tests/test_bl_export_meh.py`, `docs/evidence/MEH_M9_<date>.md`.

## Steps

1. **A: BEM-only cross-check of M2.** Export the finalist's L1 mesh (metres, `scale_to_m = 1.0`) as a BL exterior
   project with one `ideal_velocity_source` + `normal_velocity` port per tag (tags 2 and 10), symmetry `xy`,
   explicit `frequencies_hz` overlay, sphere sampling on. `blab project solve` headless. Compare per-port pressures
   with our `channel_pressure` (conjugate: BL is exp(+i w t); BL is 1 m/s basis, ours is unit acceleration) and the
   acoustic-impedance matrix: <= 0.5 dB / 5 deg to 8 kHz.
2. **B: coupled refinement.** Build the finalist with FEM front chambers + throat (one connected FEM volume, as the
   MEH Studio audit recommends), port interfaces, `electrodynamic_transducer` per driver from the driver files
   (`mmd_kg`, never Mms), `lumped_sealed_rear_chamber` per mid, voltage ports, and channels from the NetworkSolution
   (LR orders, xo, delays, polarity; BL channels support LR/BW 4 and 6). Solve; compare the summed on-axis and
   listening-window response and the port air speed (`interface_average_normal_velocity`) with our L1 prediction.
3. GPU hygiene: BL's CLI leaves its Julia host running: clear it after every solve (CLAUDE.md rules 1, 2, 6).

## Tests (CPU, no BL install needed)

The exported JSON validates against the schema-10 shape we read from the template (ids unique, every surface group
has one boundary, one port per component, symmetry consistent with the mesh), units metres.
