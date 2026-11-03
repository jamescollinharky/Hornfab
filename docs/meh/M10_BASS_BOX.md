# M10: bass box (30-120 Hz flat) to pair with the MEH top

Model: Sonnet (Haiku acceptable for the datasheet table). Wave 1, independent of everything else. CPU only.
Read `00_MEH_CONTRACTS.md` C0, C7, C8 and `docs/research/typologies/mini_meh_2026-10-29/calc/bassbox_sizing.md`.

## Targets (owner 2026-10-30)

Flat 30-120 Hz (DSP allowed: EQ, Linkwitz transform), crossover to the MEH at the brief's `hp_hz` (120 T2 / 160 T1),
"keep up with a powered 12 in + horn PA" in a living room / DJ booth: >= 112 dB at 40 Hz and >= 118 dB at 63-120 Hz,
sine, 1 m, half space, BEFORE room/corner gain. Size: as small as meets that; one or two boxes (stereo pair allowed).

Sizing already done [measured, `bassbox_sizing.md`]: 1 x 15 in long-throw (Xmax 9) ~106 / 111 / 114 dB at
30 / 40 / 50 Hz; 1 x 15 in high-excursion (Xmax 13) or 1 x 18 in ~109 / 114 / 118 dB; ideal vented B4 with f3 30 Hz
gives ~91-92 dB / 1 W in 120-150 L.

## Owns

`tools/bassbox.py`, new woofer files (kind `cone`, C8 keys) in `examples/drivers/`, `tests/test_bassbox.py`,
`docs/research/typologies/mini_meh_2026-10-29/BASSBOX_<date>.md`.

## Steps

1. Shortlist 4-6 long-throw 15 in and 18 in pro woofers with full datasheet T/S (B&C, FaitalPRO, 18 Sound, Beyma);
   write their driver files (M1 rules: datasheet only, URL in `source`).
2. `tools/bassbox.py`: lumped sealed and vented box (driver T/S + box compliance + port mass/loss + leakage Ql 7),
   electrical input impedance, SPL at 2.83 V and at max input, cone excursion, port air velocity; DSP block (LR4 HP
   at an infrasonic corner, Linkwitz transform for sealed, PEQ); max SPL per frequency from Xmax, P_AES and port air
   17 m/s. Reuse `hornlab_search/meh/network.py` maths where it exists (after M4), otherwise self-contained numpy.
3. For each driver: best vented and best sealed + LT design meeting the targets; box litres, tuning, port size and
   length; max SPL curve. Recommend one (and a two-box option). Build sheet in the BASSBOX doc.

## Tests

Small-signal response of a textbook B4 alignment (fs = fb, Qts 0.383, alpha 1) is -3 dB at fs within 0.2 dB;
energy balance; port velocity formula against a hand calculation.

## Checkpoint

New tests + the full offline suite; the BASSBOX doc with the recommendation table.
