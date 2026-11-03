# M1: MEH driver files (`examples/drivers/`)

Model: Sonnet (Haiku acceptable for the transcription; the drawing reads need care). Wave 1. Read
`00_MEH_CONTRACTS.md` C8, then `examples/drivers/_template.yaml` and appendix A s8 of the dossier
(`docs/research/typologies/mini_meh_2026-10-29/appendix_A_web_survey_raw.md`, driver table with datasheet URLs).

## Owns

New files only: `examples/drivers/<stem>.yaml` for the list below; `tests/test_meh_driver_files.py`.

| stem | kind | notes |
|---|---|---|
| `bc_6ndl38` | cone | T2 primary mid (JW DH350 MEH uses it) |
| `faitalpro_6pr160` | cone | T2 alternative (publishes Mmd, Cms, Rms) |
| `eighteensound_6nmb420` | cone | T2 backup (low Le) |
| `bc_4ndf34` | cone | T1 mid |
| `faitalpro_4fe32` | cone | T1 alternative (publishes Mmd) |
| `faitalpro_hf1440` | compression_meh | T2 CD (1.4 in, min XO 0.7 kHz) |
| `faitalpro_hf108` | compression_meh | T1 CD (1 in, min XO 1.3 kHz) |
| `bc_dh450` | compression_meh | T1 alternative (1 in, 1 kHz) |

## Steps

1. Open each maker datasheet PDF (URLs in appendix A s8); copy every C8 key with its datasheet unit; put the PDF URL
   in `source`. A value derived by formula (Mmd from Mms, Cms from Vas) lists the key under `derived:` and the formula
   in `notes`. Never guess.
2. Mechanical: `cutout_mm`, `depth_mm` (mounting depth), and where the drawing shows them `frame_od_mm`,
   `motor_od_mm`, `dish_mm` (cone dish depth below the flange). CDs: `body_d_mm`, `body_len_mm`, and `duct_mm`
   (diaphragm to exit) if the drawing or a section view shows it; otherwise omit it and write "duct depth not
   published" in `notes` (M5 then keeps the contract's [inferred] default and flags it).
3. `tests/test_meh_driver_files.py`: every new file parses, has the C8 required keys for its kind, positive finite
   numbers, an `http` source, and (cones) Fs/Qms/Mms consistent with Cms within 3 % where both are published.

## Checkpoint

The new test + the full offline suite (paste outputs). Report a table: stem, every value, which were derived, which
mechanical values are missing.
