Envelope: 406.4 x 406.4 mm face (16 in), 380 mm deep, 18 mm walls, 20 mm mouth roll.

### Seeds

| seed | coverage | mouth W x H | horn length (mm) | port z (mm) | path to diaphragm (mm) | quarter-wave f (Hz) | V_front (cm^3) | port / Sd | f_h (Hz) | box interior (L) | layout |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T2 2 x 6NDL38 top/bottom, HF108 | 90x60 | 330 x 191 | 150 | 60 | 85 | 1009 | 264 | 0.14 | 662 | 47 | driver_hits_cd |
| T2 2 x 6NDL38 sides, HF108 | 90x60 | 330 x 191 | 150 | 60 | 85 | 1009 | 264 | 0.14 | 662 | 47 | port_wider_than_wall |
| T2 2 x 6PR160 top/bottom, HF108 | 90x60 | 330 x 191 | 150 | 60 | 85 | 1009 | 260 | 0.14 | 667 | 47 | driver_hits_cd |
| T2 2 x 6NDL38 top/bottom, HF1440 | 90x60 | 330 x 191 | 144 | 70 | 110 | 780 | 264 | 0.14 | 662 | 47 | OK |
| T1 4 x 4NDF34 all walls, HF108 | 90x60 | 330 x 191 | 150 | 45 | 70 | 1225 | 89 | 0.14 | 898 | 47 | OK |
| T1 4 x 4NDF34 all walls 80x80 | 80x80 | 330 x 330 | 183 | 45 | 70 | 1225 | 89 | 0.14 | 898 | 47 | drivers_collide |
| T1 4 x 4NDF34 all walls, DH450 | 90x60 | 330 x 191 | 150 | 45 | 70 | 1225 | 89 | 0.14 | 898 | 47 | OK |

### Random knob-box sweeps (n = 400 each)

#### T2: 2 x 6NDL38 on the top/bottom walls, HF108

feasible 48/400; failure reasons (count): driver_hits_cd 182, driver_past_mouth 138, driver_outside_face 109, drivers_collide 59, port_wider_than_wall 35, port_at_mouth 31

| knob / output | feasible range |
|---|---|
| cov_h | 71-95 |
| cov_v | 45-88 |
| z_port (mm) | 38-132 |
| port_across (mm) | 20-86 |
| slide (mm) | -47-46 |
| mouth W (mm) | 268-330 |
| mouth H (mm) | 148-330 |
| horn length z_m (mm) | 138-212 |
| quarter-wave f at diaphragm (Hz) | 546-1358 |
| f_h port corner (Hz) | 373-801 |

#### T2: 2 x 6NDL38 on the side walls, HF108

feasible 39/400; failure reasons (count): driver_outside_face 207, driver_hits_cd 151, driver_past_mouth 91, port_wider_than_wall 72, drivers_collide 60, port_at_mouth 28

| knob / output | feasible range |
|---|---|
| cov_h | 70-96 |
| cov_v | 47-89 |
| z_port (mm) | 39-133 |
| port_across (mm) | 21-90 |
| slide (mm) | -50-49 |
| mouth W (mm) | 246-330 |
| mouth H (mm) | 146-330 |
| horn length z_m (mm) | 134-219 |
| quarter-wave f at diaphragm (Hz) | 543-1340 |
| f_h port corner (Hz) | 335-701 |

#### T1: 4 x 4NDF34, one per wall, HF108

feasible 117/400; failure reasons (count): driver_outside_face 131, driver_hits_cd 118, drivers_collide 107, port_wider_than_wall 97, driver_past_mouth 66, port_at_mouth 23

| knob / output | feasible range |
|---|---|
| cov_h | 70-100 |
| cov_v | 40-90 |
| z_port (mm) | 26-136 |
| port_across (mm) | 21-89 |
| slide (mm) | -49-49 |
| mouth W (mm) | 252-330 |
| mouth H (mm) | 116-330 |
| horn length z_m (mm) | 125-219 |
| quarter-wave f at diaphragm (Hz) | 532-1690 |
| f_h port corner (Hz) | 538-1286 |

### Reparameterised knob box with deterministic repair (n = 400 each)

Box: cov_h 75-95, cov_v 50-80, z_frac 0-1, across_frac 0.35-0.9, port_along 12-35 mm, spacer 2-8 mm, slide -10..40 mm (repaired), fill 0-0.7 (6.5-inch only).

| typology | feasible | remaining failures | z_port 5-95 % (mm) | quarter-wave f 5-95 % (Hz) | f_h 5-95 % (Hz) | port / Sd 5-95 % (%) |
|---|---|---|---|---|---|---|
| T2 2 x 6NDL38 top/bottom, HF108 | 308/400 | driver_outside_face 84, driver_hits_cd 8, driver_past_mouth 4 | 23-131 | 550-1780 | 466-960 | 4-37 |
| T2 2 x 6NDL38 top/bottom, HF1440 | 289/400 | driver_outside_face 82, driver_hits_cd 29, driver_past_mouth 20 | 24-126 | 516-1336 | 504-924 | 4-33 |
| T2 2 x 6NDL38 sides, HF108 | 163/400 | driver_outside_face 237 | 20-74 | 866-1925 | 389-726 | 2-14 |
| T1 4 x 4NDF34 one per wall, HF108 | 222/400 | driver_outside_face 147, drivers_collide 31 | 22-93 | 725-1810 | 648-1202 | 6-46 |
| T1b 2 x 4NDF34 top/bottom, HF108 | 372/400 | driver_outside_face 28 | 22-133 | 543-1806 | 722-1416 | 8-79 |

### Final seeds (after repair)

| seed | coverage | mouth W x H | horn length (mm) | port z (mm) | path to diaphragm (mm) | quarter-wave f (Hz) | V_front (cm^3) | port / Sd | f_h (Hz) | box interior (L) | layout |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T2-A seed: 2 x 6NDL38 t/b + HF1440, no fill | 90x60 | 330 x 191 | 144 | 45 | 85 | 1011 | 251 | 0.18 | 732 | 47 | OK |
| T2-B seed: 2 x 6NDL38 t/b + HF108, 60 % fill | 90x60 | 330 x 191 | 150 | 41 | 66 | 1298 | 172 | 0.15 | 847 | 47 | OK |
| T1 seed: 4 x 4NDF34 + HF108 | 90x60 | 330 x 191 | 150 | 44 | 69 | 1246 | 89 | 0.13 | 872 | 47 | OK |
