# M2: solver fork, several source tags + impedance matrix (opt-in)

Model: Sonnet. Wave 1. Depends on nothing. Runs in the cloud for code + Python tests; Julia/CUDA validation runs on
the owner's GPU box in M8. Read `00_MEH_CONTRACTS.md` C4 first, then `docs/FORKS.md` (the fork rules: branch,
opt-in, byte-identical default, commit, validation ladder).

## Owns

Repository `llevaachingada/hornlab-beat-bem`, new branch `hornlab-search/meh-multisource` from `hornlab-search/base`
(if the fused-CUDA branch is what the pin uses today, branch from the pinned SHA in `TOOLCHAIN.md`; say which in the
evidence doc). Plus `docs/evidence/MEH_M2_FORK_<date>.md` in hornlab-search.

## What exists (verified 2026-10-29 on the fork's main)

- Julia `hornlab_beat_bem/julia/BeatEngineDriver.jl`:
  - `radiator_inputs_from_config` (~line 402) ALREADY accepts `config["radiators"]` (name, tag, channel, offsets, filters).
  - `channel_neumann_columns` (~767) builds one Neumann column per channel; the fused CUDA path builds all in one pass.
  - `channel_names = sort(unique(...))` (~1196) is LEXICOGRAPHIC: hence the zero-padded names in C4.
  - Per channel the solve loop keeps `channel_boundary_pressures` (~1605) and emits per-channel H/V/diagonal/sphere
    rows (`complex_rows_to_wire`, ~1670).
  - `impedance_for_radiators` (~1030) integrates the MIXED pressure over each radiator: no mutual matrix.
- Python:
  - `hornlab_beat_bem/config.py:462-466` refuses `len(velocity_sources) != 1`; `source_tag` property (~561).
  - `hornlab_beat_bem/sweep.py`: `_request_payload` (~139) sends only `tag_throat`; the result loop (~385) raises if
    `len(channel_names) != 1` and takes row `[0]`; impedance unpacking (~405-418).
  - `capabilities.py` `_sources()` (~236) and `per_tag_mean_pressures` (~388) say "one".

## Build steps

1. `config.py`: allow 1..8 tags; keep the per-amplitude refusals (complex, non-unit) for every entry; add
   `impedance_matrix: bool = False`; keep `source_tag` = smallest tag; add `source_tags` property (sorted tuple).
2. `sweep.py::_request_payload`: with >= 2 tags add `"radiators"` exactly as C4; with `impedance_matrix` add
   `"impedance_matrix_enabled": True`. With one tag and no matrix: **no new keys** (golden-payload test).
3. `sweep.py` mesh check: every tag must have area > 0 (`mesh_info.physical_tag_areas_m2`).
4. Julia: add (next to `impedance_for_radiators`, same force-scale rule and x10 packing):

```julia
# MEH (opt-in): row j = force on every radiator from channel j's own boundary pressure at unit drive.
function impedance_matrix_for_channels(mesh, element_mesh_ids, channel_boundary_pressures, radiators, ::Type{T};
                                       symmetry_mode::Symbol=:off) where {T<:AbstractFloat}
    matrix = Vector{Vector{Vector{Float32}}}()
    for pressure in channel_boundary_pressures
        force_scale = eltype(pressure)(symmetry_mode == :ground ? 1 : symmetry_reduction_factor(symmetry_mode))
        row = Vector{Vector{Float32}}()
        for radiator in radiators
            total_force = zero(eltype(pressure))
            tag = Int(radiator["tag"])
            for element_index in eachindex(mesh.physical_tags)
                mesh.physical_tags[element_index] == tag || continue
                radiator_owns_element(radiator, element_mesh_ids, element_index) || continue
                face = mesh.faces[element_index]
                p_avg = (pressure[face[1]] + pressure[face[2]] + pressure[face[3]]) / eltype(pressure)(3.0)
                total_force += p_avg * eltype(pressure)(mesh.areas[element_index]) * force_scale
            end
            total_force *= eltype(pressure)(10.0)
            push!(row, [Float32(real(total_force) / 2), Float32(-imag(total_force) / 2)])
        end
        push!(matrix, row)
    end
    return matrix
end
```

   Call it after the per-channel loop when `get_value(config, "impedance_matrix_enabled", false)` and emit
   `"impedance_matrix" => matrix` in the result Dict (else omit the key). Confirm by reading the code that
   `channel_boundary_pressures[j]` is channel j's field at UNIT drive (velocity_offset 0 dB, no flat-target
   correction); if it is not, divide by channel j's drive and say so in the evidence doc.
5. `sweep.py` result loop: with >= 2 tags expect `channel_names == [f"tag{t:03d}" ...]`, stack ALL rows into
   `channel_pressure (F, C, P, A)` (same acceleration scale as `pressure`), sphere likewise; legacy fields = channel 0.
   Unpack `impedance_matrix[j][i]` with the existing impedance formula using tag i's reduced area -> `[f, i, j]`.
   Fill `tag_areas_m2` (full domain). Add the fields to `SolveResult` (`result.py`), default `None`.
6. `capabilities.py`: report sources count 1..8 and `per_tag_mean_pressures` supported when `impedance_matrix`.

## Tests (fork repo)

- Python, no Julia: golden payload byte-identical for one tag; multi-tag payload; parsing a fake 2-channel reply
  (rows, matrix unpacking, areas, legacy fields = channel 0); refusals still raise.
- Julia testset (runs in M8 on the GPU box; write it now): a closed test mesh with two driven tags (e.g. a small box
  with two patches; reuse `julia/test_meshes` helpers if present):
  - **superposition**: two-channel run vs one radiator list with both tags in channel "main": sum of channel rows ==
    main rows (rel 1e-5);
  - **reciprocity**: force matrix symmetric, |F_ij - F_ji| / max|F| < 1e-3;
  - **single-tag parity**: impedance_matrix[0][0] equals the existing `impedance` (rel 1e-6);
  - **symmetry**: quarter vs full model F within 1e-3 (symmetric patch layout).

## Checkpoint

`python -m pytest <fork>/tests -q` (paste the full output); the Julia testsets are listed as "pending M8" in the
evidence doc with the exact command for the owner. Commit on the branch; push; record the SHA in the evidence doc.
Do NOT bump the hornlab-search pin (M8 does that after GPU validation).

## Done when

All Python tests pass; the Julia code compiles in principle (syntax reviewed against neighbouring functions); the
evidence doc lists SHA, changed functions, tests, and the M8 commands.
