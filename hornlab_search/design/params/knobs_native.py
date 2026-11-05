"""Authored prose for the NATIVE mesher-family knobs (domain ``native``).

These are the keys of ``hornlab_search/design/families.py``'s own tables: the OSSE,
R-OSSE, ICW and FREEFORM mesher families. The module ONLY annotates them. It imports
nothing but :mod:`.schema`, so it stays import-light; it never imports numpy, the mesher,
the registry or the generator code.

NUMBERS RULE
    No default value and no hard limit is typed here. Every :class:`KnobDoc` carries
    ``default=None``, ``hard_lo=None`` and ``hard_hi=None`` on purpose. The builder lane
    reads the real numbers from ``families.KeySpec`` and the YAML seeds. Numbers inside a
    prose ``formula`` string are the published formula, not a configured value. The one
    disputed default (``exponent``) is stated as a documented mismatch, with both sources,
    and no winner is picked.

UNIT RULE
    The unit comes from the key suffix: ``_mm`` -> mm, ``_deg`` -> deg, ``_hz`` -> Hz.
    A name without a recognised suffix is dimensionless. Explicit exceptions, each also
    stated on the entry:

      * ``s1`` is mm/deg and ``s2`` is 1/mm, per the KeySpec notes in ``families.py``;
      * ``kappa0``, ``kappa_abs_max`` and each ``icw_coeffs`` value are 1/mm; ``icw_S``
        is mm (MESHER_TYPOLOGIES.md section 3a);
      * ``dkappa_ds_abs_max`` is left unitless: the mesher's solver docstring says
        ``max|dkappa/dsigma|`` and gives its own ambiguous wording, so no token is asserted;
      * ``hold_start`` / ``hold_end``, ``gcurve_dist`` and ``morph_fixed`` are fractions
        (of normalised arc length or of the main axial station);
      * ``n_coeff`` is an integer count, not a length;
      * ``morph_allow_shrinkage`` is a 0/1 flag;
      * ``mode``, ``termination``, ``pin_mouth_radius``, ``icw_seed``, ``gcurve_sf``,
        ``profileH``, ``profileV``, ``crossSections`` and ``mid_ports`` are categorical /
        boolean / container keys and carry no unit.

CONTEXTS
    Context ids are domain-scoped. The base fields and the ``"native"`` context carry the
    general native meaning; ``"native:osse"``, ``"native:rosse"`` and ``"native:icw"``
    carry a family-specific meaning where one name genuinely changes law (``q``,
    ``L_mm``, ``R_mm``). Nothing here restates a generator or rows meaning.

LOOKUP
    ``LOOKUP`` is a mesher formula (``lookupProfile``, MESHER_TYPOLOGIES.md section 5)
    but it has no entry in ``families.FAMILY_KEYS`` and no shipped config, so it has no
    native knob table to annotate. It is recorded here, not fabricated as knobs.
"""
from __future__ import annotations

from .schema import KnobContext, KnobDoc

DOMAIN = "native"

_OVL = frozenset({"overloaded"})
_DOC = frozenset({"doc_mismatch"})
_NOT_KNOB = frozenset({"not_a_knob"})
_OVL_DOC = _OVL | _DOC

_MESHER = "docs/research/typologies/MESHER_TYPOLOGIES.md"
_BASIS = "docs/plan/12_RESEARCH_BASIS.md"

_PF = "hornlab_mesher.profile_formulas."
_FF = "hornlab_mesher.freeform.build_freeform_geometry"
_PM = "hornlab_mesher.profile_morph."
_TS = "hornlab_mesher.throat_stretch.stretch_coefficients"
_FAM = "hornlab_search.design.families."


def _make(knob: str, *, label: str, unit: str | None, summary: str, detail: str,
          formula: str | None, physical: str, code_ref: str,
          doc_ref: tuple[str, str], contexts: dict | None = None,
          flags: frozenset[str] = frozenset()) -> KnobDoc:
    """Build one doc with the numeric fields deliberately unset."""
    return KnobDoc(
        knob=knob,
        label=label,
        unit=unit,
        summary=summary,
        detail=detail,
        formula=formula,
        physical=physical,
        contexts=contexts or {},
        flags=flags,
        code_ref=code_ref,
        doc_ref=doc_ref,
        default=None,
        hard_lo=None,
        hard_hi=None,
    )


def _ctx(label: str, summary: str, detail: str, *, formula: str | None = None,
         physical: str = "") -> KnobContext:
    return KnobContext(label=label, summary=summary, detail=detail, formula=formula,
                       physical=physical)


NATIVE_KNOBS: dict[str, KnobDoc] = {
    # ---------------------------------------------------------------- throat
    "r0_mm": _make(
        "r0_mm",
        label="Throat radius",
        unit="mm",
        summary="Throat radius every native family starts its meridian from.",
        detail=("OSSE and R-OSSE use it as the base radius of the wall law, ICW uses it "
                "as the throat integration constant, and a FREEFORM meridian starts at "
                "its own first anchor radius. It is shared by the H and V planes unless a "
                "per-azimuth expression is used. The mesher rejects a non-positive value."),
        formula="OSSE: base(z) starts at k r0 + r0(1-k); ICW: r(s) = r0 + S integral sin(theta)",
        physical="Sets the throat area and the driver exit the wall must match.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
    ),
    "a_deg": _make(
        "a_deg",
        label="Coverage half-angle",
        unit="deg",
        summary="Coverage half-angle the OSSE/R-OSSE wall approaches, in the mesher convention.",
        detail=("In OSSE a_deg is the far-field wall half-angle; in R-OSSE it enters the "
                "throat-radius curve through tan(a)^2. The target block's coverage_*_deg "
                "is the TOTAL included angle, so it is not numerically equal to a_deg. "
                "Biradial and QTW reuse this name for different angles in the generator "
                "domain; this context asserts only the native mesher meaning."),
        formula="OSSE: base(z) carries tan(a); R-OSSE: c3 = tan(a)^2",
        physical="Widens or narrows the horn's coverage for a fixed depth.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
        contexts={
            "native": _ctx(
                "Native coverage half-angle",
                "OSSE/R-OSSE coverage half-angle in the mesher's own convention.",
                "The mesher measures the angle as a half-angle from the axis. The target "
                "block in a config measures the total included angle, which is the value "
                "the objective scores. Read the block before comparing the two.",
                physical="Sets how wide the wall opens relative to the axis.",
            ),
        },
        flags=_OVL,
    ),
    "a0_deg": _make(
        "a0_deg",
        label="Throat half-angle",
        unit="deg",
        summary="Wall half-angle at the throat, passed to the OSSE, R-OSSE and ICW meridian.",
        detail=("OSSE carries it in the 2 k r0 z tan(a0) term of the base radius, and "
                "R-OSSE carries the same term in its throat-radius curve. ICW uses it as "
                "the initial tangent angle theta0 of the curvature integral. It should "
                "match the driver exit angle when the wall is meant to continue the driver."),
        formula="OSSE/R-OSSE: c2 = 2 k r0 tan(a0); ICW: theta(0) = theta0",
        physical="Sets the initial expansion slope at the driver exit.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
    ),
    "k": _make(
        "k",
        label="OS-SE shape factor",
        unit=None,
        summary="Blends the OS-SE base radius between its radius term and its tangent term.",
        detail=("The base radius carries (k r0) and r0(1-k) terms plus the tangent-driven "
                "z term, so k reshapes the wall between the throat and the far-field "
                "angle. R-OSSE reuses it in its throat-radius curve. It is dimensionless "
                "and is not a termination control."),
        formula="base(z) = sqrt((k r0)^2 + 2 k r0 z tan(a0) + z^2 tan(a)^2) + r0(1-k)",
        physical="Reshapes the wall between the throat and the far-field angle.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
    ),
    "q": _make(
        "q",
        label="Termination / blend exponent",
        unit=None,
        summary="OSSE superellipse saturation, or the R-OSSE throat-to-mouth blend exponent.",
        detail=("In OSSE q scales the normalised axial station of the superellipse "
                "termination term and must stay positive while s is nonzero. In R-OSSE the "
                "same key is the exponent of the t^q blend between the throat-radius and "
                "mouth-radius curves. The generator domain's q is only the OSSE saturation; "
                "the two native meanings share a name, not a law."),
        formula=("OSSE: z_norm = q z/L; "
                 "R-OSSE: r(t) = (1 - t^q) throat_r(t) + t^q mouth_r(t)"),
        physical="Changes the mouth termination in OSSE and the blend timing in R-OSSE.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
        contexts={
            "native": _ctx(
                "Family-dependent exponent",
                "OSSE saturation or R-OSSE blend exponent; resolve the family first.",
                "The same numeric value changes a different equation in the two families. "
                "A tooltip must not say 'termination saturation' for an R-OSSE design, nor "
                "'blend exponent' for an OSSE design.",
                physical="Moves the termination in OSSE; moves the blend timing in R-OSSE.",
            ),
            "native:osse": _ctx(
                "OSSE termination saturation",
                "Superellipse saturation of the OSSE termination; positive while s is nonzero.",
                "It sets how quickly the termination term saturates with axial station. The "
                "mesher requires it positive whenever the termination amplitude s is nonzero.",
                formula="z_norm = q z/L; term = (s L/q)(1 - (1 - z_norm^n)^(1/n))",
                physical="Changes how abruptly the terminated outline reaches its corner.",
            ),
            "native:rosse": _ctx(
                "R-OSSE blend exponent",
                "Exponent of the throat-to-mouth blend; not the OSSE saturation.",
                "R-OSSE has no superellipse termination term in the OSSE sense. Here q "
                "controls how long the throat-radius curve dominates before the mouth-radius "
                "curve takes over.",
                formula="r(t) = (1 - t^q) throat_r(t) + t^q mouth_r(t)",
                physical="Moves the hand-over from throat law to mouth law along the curve.",
            ),
        },
        flags=_OVL,
    ),
    "s1": _make(
        "s1",
        label="Throat stretch coefficient 1",
        unit="mm/deg",
        summary="Strength of the OSSE/R-OSSE nonlinear throat-stretch mapping.",
        detail=("The mesher maps the main-section axial coordinate through "
                "x + s1 * degrees(atan(s2 x)), so s1 multiplies an angle and is not "
                "dimensionless. It is active only with a nonzero s2. The coefficients must "
                "be plain finite numbers, and various rotation/slot combinations are refused."),
        formula="x_stretched = x + s1 * degrees(atan(s2 * x))",
        physical="Redistributes axial stations toward or away from the throat.",
        code_ref=_TS,
        doc_ref=(_MESHER, "### 6f. Throat stretch (OSSE, R-OSSE)"),
    ),
    "s2": _make(
        "s2",
        label="Throat stretch coefficient 2",
        unit="1/mm",
        summary="Inverse-length scale inside the throat-stretch arctangent.",
        detail=("s2 sets how quickly the arctangent saturates with axial distance, so its "
                "unit is inverse length. It is active only together with a nonzero s1. The "
                "mesher refuses a slot combined with throat stretch and refuses per-azimuth "
                "forms of either coefficient."),
        formula="x_stretched = x + s1 * degrees(atan(s2 * x))",
        physical="Moves where the stretched region becomes nearly linear again.",
        code_ref=_TS,
        doc_ref=(_MESHER, "### 6f. Throat stretch (OSSE, R-OSSE)"),
    ),
    "throat_ext_length_mm": _make(
        "throat_ext_length_mm",
        label="Throat extension length",
        unit="mm",
        summary="Length of the tapered tube prepended before the main OSSE/R-OSSE meridian.",
        detail=("The extension tapers back from the main throat radius, then the optional "
                "slot and the main meridian follow. A zero length leaves the main meridian "
                "starting at the throat. It is a prefix of the composite meridian, not part "
                "of the OS wall law itself."),
        formula="r = r0_throat + z tan(throat_ext_angle), r0_throat = r0 - ext_len tan(angle)",
        physical="Adds a short driver-adapter tube ahead of the horn.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 6e. Throat extensions and slots (OSSE, R-OSSE)"),
    ),
    "throat_ext_angle_deg": _make(
        "throat_ext_angle_deg",
        label="Throat extension angle",
        unit="deg",
        summary="Taper angle of the prepended throat extension, measured from the axis.",
        detail=("The extension radius falls back from the main throat radius by the "
                "extension length times this angle's tangent. The mesher refuses a taper "
                "that would drive the start radius negative. A zero angle makes the "
                "extension cylindrical."),
        formula="r0_throat = r0 - ext_len tan(throat_ext_angle)",
        physical="Sets how much the adapter tube narrows or widens ahead of the horn.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 6e. Throat extensions and slots (OSSE, R-OSSE)"),
    ),
    "slot_length_mm": _make(
        "slot_length_mm",
        label="Slot length",
        unit="mm",
        summary="Straight cylindrical section at the throat radius between extension and main horn.",
        detail=("The slot holds the radius constant over this axial length. OSSE refuses a "
                "slot combined with throat stretch, so s1/s2 and a nonzero slot are "
                "alternatives there. A zero length disables the slot."),
        formula="r = r0_main over [ext_len, ext_len + slot_len]",
        physical="Adds a cylindrical throat spacer before the flared section.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 6e. Throat extensions and slots (OSSE, R-OSSE)"),
    ),
    # ---------------------------------------------------------------- cross-section
    "exponent": _make(
        "exponent",
        label="Cross-section superellipse exponent",
        unit=None,
        summary="Superellipse exponent of the cross-section outline; squarer as it rises.",
        detail=("In the OSSE-like families this is the family-level cross-section exponent; "
                "in FREEFORM it is the alias into the first superellipse station of "
                "crossSections. The documented default is disputed: 12_RESEARCH_BASIS.md "
                "states 2.0, while registry.DEFAULT_KNOBS['mouth_exponent'] ships 4.0. "
                "Both claims are recorded with their sources, and this layer picks no winner."),
        formula="station radius uses (|cos(phi)/a|^e + |sin(phi)/b|^e)^(-1/e)",
        physical="Squares off or rounds the cross-section outline.",
        code_ref=_FAM + "FAMILY_KEYS",
        doc_ref=(_BASIS, "## 4. The geometry we would have written already exists"),
        contexts={
            "native": _ctx(
                "Native cross-section exponent",
                "Superellipse exponent of the outline; the documented default is disputed.",
                "The research basis states a default of 2.0 (a plain ellipse); the shipped "
                "generator default for the same idea is 4.0 (registry.DEFAULT_KNOBS). This "
                "entry records both claims and does not choose between them. It is not the "
                "generator's mouth_exponent key, although the two describe the same idea.",
                formula="( |cos(phi)/a|^e + |sin(phi)/b|^e )^(-1/e)",
                physical="Squares off or rounds the cross-section outline.",
            ),
        },
        flags=_OVL_DOC,
    ),
    "aspect_ratio": _make(
        "aspect_ratio",
        label="Cross-section aspect ratio",
        unit=None,
        summary="Width-to-height scaling of the cross-section relative to the meridian radius.",
        detail=("The mesher scales the horizontal and vertical half-widths of the outline by "
                "this ratio. A value of one gives a circular section; larger values widen "
                "it. It does not change either meridian and is not a coverage angle."),
        formula="b = a * aspect_ratio in the ellipse/superellipse station",
        physical="Widens or narrows the cross-section without changing the wall profiles.",
        code_ref=_FAM + "FAMILY_KEYS",
        doc_ref=(_MESHER, "## 7. Geometric / cross-section model (all formulas)"),
    ),
    # ---------------------------------------------------------------- common config
    "mode": _make(
        "mode",
        label="Build mode",
        unit=None,
        summary="Mesher build mode: freestanding shell, enclosure, or infinite baffle.",
        detail=("The mode selects which shell or enclosure treatment the mesher builds "
                "around the acoustic surface. families.py accepts the documented aliases "
                "and to_mesher_config writes the top-level value; a mounting block switches "
                "it to enclosure. It does not change the profile geometry."),
        formula=None,
        physical="Changes the outer shell and boundary model, not the inner wall.",
        code_ref=_FAM + "to_mesher_config",
        doc_ref=(_MESHER, "## 7. Geometric / cross-section model (all formulas)"),
        contexts={
            "native": _ctx(
                "Native build mode",
                "Top-level mesher mode for the native family configs.",
                "The config value is the mesher's own token; the search layer only forces "
                "enclosure when a mounting block is present. Aliases are accepted by "
                "families.py and are not renamed here.",
                physical="Chooses the shell/enclosure treatment around the horn.",
            ),
        },
    ),
    "wall_thickness_mm": _make(
        "wall_thickness_mm",
        label="Shell thickness",
        unit="mm",
        summary="Printed shell thickness offset outward from the acoustic wall.",
        detail=("The mesher offsets an outer surface from the wall by this thickness. The "
                "generator domain also carries the same name for its generated shell; the "
                "native meaning is the mesher mesh-section value. It is mechanical, not an "
                "acoustic dimension, and a strongly curved throat limits how thick it can be."),
        formula=None,
        physical="Changes the printed wall thickness, not the acoustic inner surface.",
        code_ref=_FAM + "FAMILY_KEYS",
        doc_ref=(_MESHER, "## 7. Geometric / cross-section model (all formulas)"),
        contexts={
            "native": _ctx(
                "Native shell thickness",
                "Mesh-section shell thickness for the native families.",
                "This is the mesher's offset distance, not the generator's generated shell "
                "knob, although both are printed-wall thicknesses. The mesher validates "
                "curvature against it.",
                physical="Changes the printed wall thickness only.",
            ),
        },
    ),
    # ---------------------------------------------------------------- morph
    "morph_target": _make(
        "morph_target",
        label="Morph target shape",
        unit=None,
        summary="Cross-section shape the mouth morphs toward: off, rectangle, circle or superellipse.",
        detail=("families.py names the off, rectangle, circle and superellipse codes; the "
                "superellipse target reads morph_exponent. The morph factor begins at "
                "morph_fixed and follows the rate power toward the mouth. Ath's own "
                "vocabulary calls this control Morph.TargetShape."),
        formula="r(t, phi) = r_base(t, phi) + factor * (r_target(phi) - r_mouth_base(phi))",
        physical="Blends the round section into a target outline toward the mouth.",
        code_ref=_PM + "_morph_target_shape",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_width_mm": _make(
        "morph_width_mm",
        label="Morph target width",
        unit="mm",
        summary="Full target width of a rectangular or superellipse morph at the mouth.",
        detail=("A zero width lets the mesher infer the target width from the mouth extent. "
                "The value is a full width, not a half-width. Ath calls the same control "
                "Morph.TargetWidth."),
        formula=None,
        physical="Sets how wide the morphed mouth outline becomes.",
        code_ref=_PM + "_morph_factor",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_height_mm": _make(
        "morph_height_mm",
        label="Morph target height",
        unit="mm",
        summary="Full target height of a rectangular or superellipse morph at the mouth.",
        detail=("A zero height lets the mesher infer the target height from the mouth "
                "extent. The value is a full height, not a half-height. Ath calls the same "
                "control Morph.TargetHeight."),
        formula=None,
        physical="Sets how tall the morphed mouth outline becomes.",
        code_ref=_PM + "_morph_factor",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_corner_mm": _make(
        "morph_corner_mm",
        label="Morph corner radius",
        unit="mm",
        summary="Corner radius of a rounded-rectangle morph target.",
        detail=("The radius is clamped against the target half-dimensions at run time. It "
                "is used only for a rounded-rectangle target. Ath calls the same control "
                "Morph.CornerRadius."),
        formula=None,
        physical="Rounds the corners of a rectangular morphed mouth.",
        code_ref=_PM + "_resolve_morph_half_dimensions",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_exponent": _make(
        "morph_exponent",
        label="Morph superellipse exponent",
        unit=None,
        summary="Superellipse exponent of a morph target 3 outline.",
        detail=("The mesher reads this only when morph_target is 3, then clamps it into "
                "the superellipse range before building the target outline. Ath's guide "
                "documents only targets 0-2; target 3 is a mesher extension."),
        formula=None,
        physical="Squares off or rounds a superellipse morphed mouth.",
        code_ref=_PM + "_morph_target_radius_at_angle",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_rate": _make(
        "morph_rate",
        label="Morph rate",
        unit=None,
        summary="Power-law rate of the morph blend from the fixed part to the mouth.",
        detail=("The factor is the remapped axial fraction raised to this power, so larger "
                "values delay the morph until nearer the mouth. It only matters when a "
                "morph target is active. Ath calls the same control Morph.Rate."),
        formula="factor = clamp((t - morph_fixed)/(1 - morph_fixed), 0, 1)^morph_rate",
        physical="Moves how quickly the outline changes along the horn.",
        code_ref=_PM + "_morph_factor",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_fixed": _make(
        "morph_fixed",
        label="Morph fixed part",
        unit=None,
        summary="Axial fraction where the morph begins; zero starts at the throat.",
        detail=("The fixed part holds the base section before the morph factor becomes "
                "nonzero. The remaining axial fraction is remapped before the rate power is "
                "applied. Ath calls the same control Morph.FixedPart."),
        formula="factor = 0 for t <= morph_fixed",
        physical="Delays the start of the outline change along the horn.",
        code_ref=_PM + "_morph_factor",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_allow_shrinkage": _make(
        "morph_allow_shrinkage",
        label="Allow morph shrinkage",
        unit=None,
        summary="0/1 flag that lets a morph target be smaller than the current mouth extent.",
        detail=("Without the flag the mesher refuses a target that would shrink the "
                "outline. With it the morph may pull the section inward. Ath calls the same "
                "control Morph.AllowShrinkage."),
        formula=None,
        physical="Allows or refuses a mouth outline that narrows toward the target.",
        code_ref=_PM + "_resolve_morph_half_dimensions",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    # ---------------------------------------------------------------- guiding curve
    "gcurve_type": _make(
        "gcurve_type",
        label="Guiding-curve type",
        unit=None,
        summary="Guiding-curve target: off, superellipse, or superformula.",
        detail=("When active, the mesher solves the OSSE coverage angle so the wall meets "
                "the target outline at the guiding-curve distance. Type one is a "
                "superellipse and type two a superformula; zero disables the solve. It is "
                "an OSSE-only mechanism in families.py."),
        formula="solve a such that r_OSSE(z_g, phi) = r_target(phi)",
        physical="Makes the coverage angle follow a target cross-section instead of one value.",
        code_ref=_PM + "_solve_coverage_from_guiding_curve",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_width_mm": _make(
        "gcurve_width_mm",
        label="Guiding-curve width",
        unit="mm",
        summary="Full width of the guiding-curve target section.",
        detail=("A non-positive width disables the guiding curve even when a type is set. "
                "It is a target width, not the horn's own mouth width. It works with the "
                "target aspect ratio and rotation."),
        formula="a = gcurve_width_mm / 2",
        physical="Scales the outline the coverage angle is solved to meet.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_aspect_ratio": _make(
        "gcurve_aspect_ratio",
        label="Guiding-curve aspect ratio",
        unit=None,
        summary="Width-to-height ratio of the guiding-curve target section.",
        detail=("The mesher requires the ratio positive. It changes the shape the coverage "
                "angle is solved to meet, not the coverage angle directly. A value of one "
                "gives a target as tall as it is wide."),
        formula="b = a * gcurve_aspect_ratio",
        physical="Stretches the target outline vertically or horizontally.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_dist": _make(
        "gcurve_dist",
        label="Guiding-curve distance",
        unit=None,
        summary="Axial placement of the guiding curve, as a fraction of the main length.",
        detail=("The mesher treats a value in the unit interval as a fraction of the main "
                "OSSE length and a larger value as an absolute axial station. The achieved "
                "radius is therefore a mouth radius only when the target sits at the mouth. "
                "The mesher reference notes that its schema default places the target "
                "mid-horn."),
        formula="z_target = gcurve_dist * L_main (when in the unit interval)",
        physical="Moves the axial station where the target outline is matched.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_rot_deg": _make(
        "gcurve_rot_deg",
        label="Guiding-curve rotation",
        unit="deg",
        summary="In-plane rotation of the guiding-curve target outline.",
        detail=("The mesher subtracts the rotation from the azimuth before evaluating the "
                "target, so the target axes can differ from the H/V axes. It does not "
                "rotate the horn itself. It is used only with an active guiding curve."),
        formula="phi_target = phi - radians(gcurve_rot_deg)",
        physical="Rotates the target outline around the horn axis.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_sf": _make(
        "gcurve_sf",
        label="Guiding-curve superformula",
        unit=None,
        summary="Superformula carried as a string, or a single zero meaning not given.",
        detail=("The schema stores this as a string. The mesher parses a six-value list "
                "(a, b, m, n1, n2, n3) when present and otherwise reads the individual "
                "gcurve_sf_* fields. A single zero means the per-field values are in force."),
        formula="r_norm = (|cos(m1 phi/4)/a|^n2 + |sin(m2 phi/4)/b|^n3)^(-1/n1)",
        physical="Defines the target outline when the guiding curve is a superformula.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_se_n": _make(
        "gcurve_se_n",
        label="Guiding-curve superellipse exponent",
        unit=None,
        summary="Superellipse exponent of a superellipse guiding-curve target.",
        detail=("The mesher clamps the exponent to its documented minimum for this target. "
                "Larger values square off the target outline. It is read only when the "
                "guiding-curve type is the superellipse."),
        formula="r = (|cos(phi)/a|^n + |sin(phi)/b|^n)^(-1/n)",
        physical="Squares off or rounds the target outline.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_sf_a": _make(
        "gcurve_sf_a",
        label="Superformula scale a",
        unit=None,
        summary="First Gielis superformula scale, dividing the cosine term.",
        detail=("It is the a in the cosine term of the superformula target. The mesher "
                "clamps its magnitude away from zero. It is used only when the guiding-curve "
                "type is the superformula and gcurve_sf is not supplying a value list."),
        formula="t1 = |cos(m1 phi/4) / a|^n2",
        physical="Sets the horizontal scale of the target outline.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_sf_b": _make(
        "gcurve_sf_b",
        label="Superformula scale b",
        unit=None,
        summary="Second Gielis superformula scale, dividing the sine term.",
        detail=("It is the b in the sine term of the superformula target. The mesher clamps "
                "its magnitude away from zero. It is used only when the guiding-curve type "
                "is the superformula and gcurve_sf is not supplying a value list."),
        formula="t2 = |sin(m2 phi/4) / b|^n3",
        physical="Sets the vertical scale of the target outline.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_sf_m1": _make(
        "gcurve_sf_m1",
        label="Superformula frequency m1",
        unit=None,
        summary="Angular frequency of the cosine term in the superformula target.",
        detail=("It sets the rotational symmetry of the cosine term. The mesher divides it "
                "by four inside the angle, following the Gielis form. It is used only when "
                "the guiding-curve type is the superformula."),
        formula="cos(m1 phi/4)",
        physical="Sets the target outline's azimuthal symmetry.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_sf_m2": _make(
        "gcurve_sf_m2",
        label="Superformula frequency m2",
        unit=None,
        summary="Angular frequency of the sine term; the mesher falls back to m1 when absent.",
        detail=("It allows the sine term's symmetry to differ from the cosine term's. When "
                "the field is absent the mesher uses m1 for both. It is used only when the "
                "guiding-curve type is the superformula."),
        formula="sin(m2 phi/4)",
        physical="Sets a second azimuthal symmetry for the target outline.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_sf_n1": _make(
        "gcurve_sf_n1",
        label="Superformula exponent n1",
        unit=None,
        summary="Overall superformula exponent applied to the summed terms.",
        detail=("It is the n1 in the reciprocal power of the Gielis formula. The mesher "
                "clamps its magnitude away from zero. It is used only when the "
                "guiding-curve type is the superformula."),
        formula="r_norm = (t1 + t2)^(-1/n1)",
        physical="Changes how the two superformula terms combine.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_sf_n2": _make(
        "gcurve_sf_n2",
        label="Superformula exponent n2",
        unit=None,
        summary="Exponent on the cosine term of the superformula target.",
        detail=("It controls how quickly the cosine term contributes away from its axis. "
                "It is not the superellipse exponent of the cross-section. It is used only "
                "when the guiding-curve type is the superformula."),
        formula="t1 = |cos(m1 phi/4) / a|^n2",
        physical="Shapes the target outline near the horizontal axis.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    "gcurve_sf_n3": _make(
        "gcurve_sf_n3",
        label="Superformula exponent n3",
        unit=None,
        summary="Exponent on the sine term of the superformula target.",
        detail=("It controls how quickly the sine term contributes away from its axis. It "
                "works together with n2 and the two frequencies. It is used only when the "
                "guiding-curve type is the superformula."),
        formula="t2 = |sin(m2 phi/4) / b|^n3",
        physical="Shapes the target outline near the vertical axis.",
        code_ref=_PM + "_guiding_curve_target_radius",
        doc_ref=(_MESHER, "### 6g. Guiding curve (OSSE)"),
    ),
    # ---------------------------------------------------------------- per-direction (CORE) law
    "az_a_sf_amp": _make(
        "az_a_sf_amp",
        label='Per-direction superformula amplitude',
        unit='deg',
        summary='Adds a superformula-shaped term to the wall angle, so the coverage differs in every direction.',
        detail="With a nonzero value the wall angle becomes a(p) = a_deg + amp * SF(p) + the cos term; a_deg is then the BASE the terms add to (Ath CORE: a_deg 5, amp 35). Diagonals that open wider than H and V fold the walls into Ath's creases.",
        formula='a(p) = a_deg + az_a_sf_amp * SF(p) + az_a_cos_amp * |cos p|^az_a_cos_pow',
        physical='How strongly the wall angle follows the superformula lobes.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    "az_sf_m": _make(
        "az_sf_m",
        label='Superformula lobes',
        unit=None,
        summary='Number of lobes of the superformula term (a multiple of 4).',
        detail='m/4 sets the angular frequency of the cos and sin terms; 4 gives one lobe per quadrant (CORE). Only multiples of 4 keep the quarter-model mirror symmetry, so others are refused.',
        formula='SF(p) = (|cos(m p/4)/a|^n2 + |sin(m p/4)/b|^n3)^(-1/n1)',
        physical='How many times the coverage pattern repeats around the horn.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    "az_sf_n1": _make(
        "az_sf_n1",
        label='Superformula n1',
        unit=None,
        summary='Overall sharpness of the superformula term.',
        detail='Large n1 flattens the lobes toward a constant; small n1 makes them pointed. CORE uses 12.',
        formula='SF(p) = (...)^(-1/n1)',
        physical='Pointed versus rounded per-direction pattern.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    "az_sf_n2": _make(
        "az_sf_n2",
        label='Superformula n2',
        unit=None,
        summary='Exponent on the cosine part of the superformula term.',
        detail='With n3 it sets how sharply the term changes between the axis and the diagonal. CORE uses 15.',
        formula='|cos(m p/4)/a|^n2',
        physical='Sharpness near the horizontal axis.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    "az_sf_n3": _make(
        "az_sf_n3",
        label='Superformula n3',
        unit=None,
        summary='Exponent on the sine part of the superformula term.',
        detail='With n2 it sets how sharply the term changes toward the vertical axis. CORE uses 16.',
        formula='|sin(m p/4)/b|^n3',
        physical='Sharpness near the vertical axis.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    "az_sf_a": _make(
        "az_sf_a",
        label='Superformula a',
        unit=None,
        summary='Scale of the cosine part of the superformula term.',
        detail='Values below 1 strengthen the horizontal side of the term. CORE uses 1.',
        formula='|cos(m p/4)/a|^n2',
        physical='Balances the horizontal side of the pattern.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    "az_sf_b": _make(
        "az_sf_b",
        label='Superformula b',
        unit=None,
        summary='Scale of the sine part of the superformula term.',
        detail='Values below 1 lower the term toward the vertical axis, narrowing V against H. CORE uses 0.618.',
        formula='|sin(m p/4)/b|^n3',
        physical='Balances the vertical side of the pattern.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    "az_a_cos_amp": _make(
        "az_a_cos_amp",
        label='Per-direction cos-power amplitude',
        unit='deg',
        summary='Adds amp * |cos p|^pow to the wall angle.',
        detail='A negative value trims the angle near the horizontal axis only, more sharply as the power grows (CORE: -15 at power 10).',
        formula='a(p) += az_a_cos_amp * |cos p|^az_a_cos_pow',
        physical='Trims or widens the horizontal coverage locally.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    "az_a_cos_pow": _make(
        "az_a_cos_pow",
        label='Per-direction cos power',
        unit=None,
        summary='Exponent of the |cos p| term on the wall angle.',
        detail='Higher powers confine the term to a narrow sector around the horizontal axis. CORE uses 10.',
        formula='|cos p|^az_a_cos_pow',
        physical='How narrow the trimmed sector is.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    "az_n_cos2_amp": _make(
        "az_n_cos2_amp",
        label='Per-direction termination n',
        unit=None,
        summary='Adds amp * cos^2 p to the OSSE termination shape n.',
        detail='The mouth termination becomes different in H and V (CORE: n 6 + 1.5 cos^2 p, i.e. 7.5 H / 6.0 V).',
        formula='n(p) = n + az_n_cos2_amp * cos^2 p',
        physical='Changes the mouth roll-off shape between H and V.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    "az_s_cos2_amp": _make(
        "az_s_cos2_amp",
        label='Per-direction termination s',
        unit=None,
        summary='Adds amp * cos^2 p to the OSSE termination strength s.',
        detail='The mouth termination strength becomes different in H and V (CORE: s 0.6 + 0.23 cos^2 p, i.e. 0.83 H / 0.60 V).',
        formula='s(p) = s + az_s_cos2_amp * cos^2 p',
        physical='Changes how strongly the mouth flares out between H and V.',
        code_ref=_FAM + "azlaw_expressions",
        doc_ref=("docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md",
                 "## 5b. Per-direction law (the exact CORE construction)"),
    ),
    # ---------------------------------------------------------------- OSSE-only
    "L_mm": _make(
        "L_mm",
        label="Axial length",
        unit="mm",
        summary="OSSE main-section length, or the ICW axial depth; the two are different targets.",
        detail=("In OSSE the composite meridian's total length may add a throat extension "
                "and a slot to this main-section length. In ICW it is the axial depth x(1) "
                "that the flat-baffle solve targets. The generator domain reuses the name "
                "for a shared meridian depth, which is a third context."),
        formula="OSSE: z spans [0, L]; ICW: x(1) = L",
        physical="Moves the mouth plane in or out along the axis.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
        contexts={
            "native": _ctx(
                "Native axial length",
                "OSSE main-section length or ICW axial depth; resolve the family first.",
                "Both are lengths in millimetres but they size different construction "
                "targets. The OSSE total may be longer than L_mm; the ICW value is the "
                "depth target itself.",
                physical="Moves the mouth plane along the axis.",
            ),
            "native:osse": _ctx(
                "OSSE main-section length",
                "Length of the main OSSE section; extension and slot may add to the total.",
                "The mesher requires it positive. In the total-length mode the section is "
                "carved differently, so the same value can mean a different total span.",
                formula="z_main in [0, L]",
                physical="Sets the depth of the flared OSSE body.",
            ),
            "native:icw": _ctx(
                "ICW axial depth",
                "Axial depth x(1) targeted by an ICW flat-baffle solve.",
                "It is a size target, not an arc length: the ICW solver finds the arc "
                "length and shape that reach this depth. Direct-coefficient mode uses "
                "icw_S for the arc length instead.",
                formula="x(1) = L",
                physical="Sets how deep the ICW meridian runs.",
            ),
        },
        flags=_OVL,
    ),
    "n": _make(
        "n",
        label="OSSE termination exponent",
        unit=None,
        summary="Superellipse termination exponent of the OSSE wall; active only while s is nonzero.",
        detail=("The termination term raises a normalised station to n, so n sharpens or "
                "softens the transition into the terminated cross-section. The mesher "
                "requires it positive whenever the termination amplitude s is nonzero. The "
                "generator's biradial type reuses the name for a flare exponent, which is a "
                "different law."),
        formula="term = (s L/q)(1 - (1 - z_norm^n)^(1/n))",
        physical="Sharpens or softens the mouth roll of an OSSE termination.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
        contexts={
            "native": _ctx(
                "OSSE termination exponent",
                "Superellipse exponent of the OSSE termination term.",
                "It is read only while the termination amplitude is nonzero. The biradial "
                "generator meaning of n is not asserted in this context.",
                formula="term = (s L/q)(1 - (1 - z_norm^n)^(1/n))",
                physical="Sharpens or softens the OSSE mouth roll.",
            ),
        },
        flags=_OVL,
    ),
    "s": _make(
        "s",
        label="Termination amplitude",
        unit=None,
        summary="OSSE superellipse termination amplitude; zero leaves the plain OS wall.",
        detail=("A nonzero amplitude turns on the superellipse termination and makes n and "
                "q active. A zero value leaves the plain OS wall. R-OSSE has no s; its "
                "rollback comes from the blended curves and tmax, not from this key."),
        formula="term is added to base only while s != 0",
        physical="Rolls the OSSE mouth toward a superellipse outline.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
    ),
    "rot_deg": _make(
        "rot_deg",
        label="Meridian rotation",
        unit="deg",
        summary="Rotates the OSSE meridian about the throat before the axial stretch.",
        detail=("The mesher rotates the radius/axial pair before throat stretch is applied. "
                "It is OSSE-only; R-OSSE and ICW refuse the key. Rotation combined with "
                "throat stretch and a prefix composition has extra mesher guards."),
        formula="x' = z cos(rot) - (r-r0) sin(rot); r' = r0 + z sin(rot) + (r-r0) cos(rot)",
        physical="Tilts the whole OSSE wall relative to the axis.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
    ),
    "h": _make(
        "h",
        label="Half-sine bulge",
        unit="mm",
        summary="Amplitude of a half-sine bulge added to the full OSSE composite profile.",
        detail=("The mesher adds h sin(pi t) over the normalised profile, so the bulge is "
                "zero at both endpoints and maximal in between. It is OSSE-only; R-OSSE "
                "refuses the key. It moves the wall without acting as a termination term."),
        formula="r(t) += h sin(pi t)",
        physical="Bulges the OSSE wall outward between throat and mouth.",
        code_ref=_PF + "calculate_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
    ),
    # ---------------------------------------------------------------- R-OSSE-only
    "R_mm": _make(
        "R_mm",
        label="Mouth / reference radius",
        unit="mm",
        summary="R-OSSE nominal mouth/reference radius, or the ICW mouth radius.",
        detail=("In R-OSSE it is the reference radius of the mouth-radius curve while the "
                "axial length is derived from the geometry. In ICW it is the mouth radius "
                "r(1) that a flat-baffle solve targets. Both are lengths, but only the ICW "
                "one is a direct size target."),
        formula="R-OSSE: mouth_r(t) = max(0, R + L(1 - sqrt(1 + c3(t-1)^2))); ICW: r(1) = R",
        physical="Sets the mouth size; in R-OSSE it also changes the derived length.",
        code_ref=_PF + "calculate_rosse",
        doc_ref=(_MESHER, "### 2b. R-OSSE parameters"),
        contexts={
            "native": _ctx(
                "Native mouth/reference radius",
                "R-OSSE nominal mouth radius or ICW mouth radius; resolve the family first.",
                "The R-OSSE value is a reference in a blended curve; the ICW value is a "
                "solved endpoint. They are not interchangeable size controls.",
                physical="Sets the mouth size.",
            ),
            "native:rosse": _ctx(
                "R-OSSE reference radius",
                "Nominal mouth/reference radius of the R-OSSE mouth-radius curve.",
                "R-OSSE derives its axial length instead of taking L_mm, which the family "
                "refuses. Changing R changes both the mouth and the derived length.",
                formula="mouth_r(t) = max(0, R + L(1 - sqrt(1 + c3(t-1)^2)))",
                physical="Sets the mouth radius and the derived axial length.",
            ),
            "native:icw": _ctx(
                "ICW mouth radius",
                "Mouth radius r(1) targeted by an ICW flat-baffle solve.",
                "It is a size target of the solve, not an integration constant. The ICW "
                "solver finds a curve that reaches it.",
                formula="r(1) = R",
                physical="Sets how wide the ICW mouth is solved to be.",
            ),
        },
        flags=_OVL,
    ),
    "tmax": _make(
        "tmax",
        label="R-OSSE truncation",
        unit=None,
        summary="Upper parameter value of the R-OSSE curve; smaller values truncate before the mouth.",
        detail=("The R-OSSE main curve is parameterised by t in [0, tmax]. A full value lets "
                "the wall reach the blended mouth and can carry it past vertical into a "
                "rollback. The mesher requires it positive."),
        formula="t in [0, tmax]",
        physical="Cuts the curve early or lets it run through the natural rollback.",
        code_ref=_PF + "calculate_rosse",
        doc_ref=(_MESHER, "### 2b. R-OSSE parameters"),
    ),
    "m": _make(
        "m",
        label="R-OSSE axial shape m",
        unit=None,
        summary="Shape parameter inside the hyperbolic axial map of R-OSSE.",
        detail=("The axial map carries sqrt(r^2 + m^2) and sqrt(r^2 + (t-m)^2), so m moves "
                "the map's shoulder along the parameter. It is dimensionless and does not "
                "change the radius curves directly. It is R-OSSE-only."),
        formula="x(t) = L(sqrt(r^2+m^2) - sqrt(r^2+(t-m)^2)) + b L(sqrt(r^2+(1-m)^2) - sqrt(r^2+m^2)) t^2",
        physical="Moves how axial distance accumulates along the R-OSSE curve.",
        code_ref=_PF + "calculate_rosse",
        doc_ref=(_MESHER, "### 2a. Mathematical formula"),
    ),
    "r": _make(
        "r",
        label="R-OSSE axial curve radius r",
        unit=None,
        summary="Rounding radius of the hyperbolic axial map of R-OSSE.",
        detail=("The parameter r appears under the square roots of the axial map. A larger "
                "value smooths the map and reduces the corner near the shoulder. It is "
                "dimensionless and is not a physical radius."),
        formula="sqrt(r^2 + m^2), sqrt(r^2 + (t-m)^2), sqrt(r^2 + (1-m)^2)",
        physical="Smooths or sharpens the axial spacing of the R-OSSE curve.",
        code_ref=_PF + "calculate_rosse",
        doc_ref=(_MESHER, "### 2a. Mathematical formula"),
    ),
    "b": _make(
        "b",
        label="R-OSSE secondary blend",
        unit=None,
        summary="Weight of the secondary quadratic axial term in the R-OSSE map.",
        detail=("The term multiplies t^2 and a difference of two square roots. A zero value "
                "removes the secondary term. It is dimensionless and is R-OSSE-only."),
        formula="x(t) += b L(sqrt(r^2+(1-m)^2) - sqrt(r^2+m^2)) t^2",
        physical="Bends the axial map toward or away from its secondary shape.",
        code_ref=_PF + "calculate_rosse",
        doc_ref=(_MESHER, "### 2a. Mathematical formula"),
    ),
    # ---------------------------------------------------------------- ICW
    "termination": _make(
        "termination",
        label="ICW termination mode",
        unit=None,
        summary="ICW mouth treatment: flat baffle or rollback.",
        detail=("flat_baffle uses the L/R/coverage/hold targets; rollback uses theta1 and "
                "aperture targets. The key is categorical, so it cannot carry a numeric "
                "bound. A seed route through icw_seed bypasses both target routes."),
        formula=None,
        physical="Chooses whether the wall stops flat or turns past vertical.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "coverage_angle_deg": _make(
        "coverage_angle_deg",
        label="Coverage plateau half-angle",
        unit="deg",
        summary="ICW wall half-angle held through the constant-angle coverage plateau.",
        detail=("The mesher requires it between the throat angle and vertical. The target "
                "block's coverage_*_deg is instead the total included angle. It enables "
                "coverage mode and changes the B-spline knot structure."),
        formula="theta(sigma) = coverage_angle_deg over [hold_start, hold_end]",
        physical="Sets the wall angle held through the coverage section.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "hold_start": _make(
        "hold_start",
        label="Coverage plateau start",
        unit=None,
        summary="Normalised arc-length fraction where the constant-angle plateau begins.",
        detail=("It is a fraction of the ICW arc length, not a length in millimetres. The "
                "mesher requires it below hold_end. It has an effect only in coverage mode."),
        formula="sigma_hold_start = hold_start",
        physical="Moves the start of the constant-angle wall section along the meridian.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "hold_end": _make(
        "hold_end",
        label="Coverage plateau end",
        unit=None,
        summary="Normalised arc-length fraction where the constant-angle plateau ends.",
        detail=("It is a fraction of the ICW arc length, not a length in millimetres. The "
                "mesher requires it above hold_start. It has an effect only in coverage mode."),
        formula="sigma_hold_end = hold_end",
        physical="Moves the end of the constant-angle wall section along the meridian.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "kappa0": _make(
        "kappa0",
        label="Throat curvature",
        unit="1/mm",
        summary="Meridional curvature at the throat of the ICW curve.",
        detail=("The ICW curve integrates curvature to get the tangent angle, so kappa0 sets "
                "the initial turn rate. It is a signed curvature in inverse millimetres. A "
                "zero value starts the curve locally straight."),
        formula="kappa(sigma) = sum_i a_i B_i(sigma); kappa(0) = kappa0",
        physical="Bends the wall immediately after the throat.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "theta1_deg": _make(
        "theta1_deg",
        label="Rollback terminal wall angle",
        unit="deg",
        summary="Terminal wall angle targeted by an ICW rollback solve.",
        detail=("It is a rollback target only; flat-baffle mode does not read it. Values "
                "past vertical carry the wall into the rollback. A config that carries the "
                "key while selecting flat_baffle is not using it as the termination."),
        formula="theta(1) = theta1_deg (rollback targets)",
        physical="Sets how far around the rollback the wall is aimed.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "n_coeff": _make(
        "n_coeff",
        label="ICW basis size",
        unit=None,
        summary="Number of curvature B-spline coefficients the ICW solver fits.",
        detail=("It is an integer count, not a length. Coverage mode uses a different count "
                "from the plain target set, per the mesher reference. It sets the size of "
                "the solver's coefficient vector."),
        formula=None,
        physical="Changes the ICW curve's available degrees of freedom.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "kappa_abs_max": _make(
        "kappa_abs_max",
        label="Curvature cap",
        unit="1/mm",
        summary="Cap on the sampled maximum absolute meridional curvature.",
        detail=("It is a soft barrier in the feasible-subspace solve, not a hard geometric "
                "clamp. It is in inverse millimetres like kappa0. If unset the solver has "
                "no curvature cap."),
        formula="max|kappa| <= kappa_abs_max",
        physical="Limits how tightly the ICW wall may bend.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "dkappa_ds_abs_max": _make(
        "dkappa_ds_abs_max",
        label="Curvature-slope cap",
        unit=None,
        summary="Cap on the sampled maximum absolute curvature derivative along normalised arc length.",
        detail=("The mesher describes the cap as max|dkappa/dsigma| and gives its own "
                "wording for the unit, which does not settle a single unit token. This layer "
                "therefore leaves the unit unset instead of inventing one. The ICW dossier "
                "records it as a solver cap beside kappa_abs_max."),
        formula="max|dkappa/dsigma| <= dkappa_ds_abs_max",
        physical="Limits how quickly the ICW wall's curvature may change.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3c. ICW solver logic (pkg/icw/solver.py)"),
    ),
    "theta_max_deg": _make(
        "theta_max_deg",
        label="Rollback wall-angle cap",
        unit="deg",
        summary="Rollback-only cap on the wall angle, above vertical and at most a half turn.",
        detail=("The mesher applies it to rollback solves only. It bounds how far around the "
                "turn the solve may go. Flat-baffle mode ignores it."),
        formula="max(theta) <= theta_max_deg (rollback only)",
        physical="Bounds how far the rollback may curl around.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "pin_mouth_radius": _make(
        "pin_mouth_radius",
        label="Pin mouth radius",
        unit=None,
        summary="Also pin the mouth radius when ICW coverage mode solves the plateau.",
        detail=("It is a boolean key. When coverage mode is active it also pins the mouth "
                "radius to the requested value. Without it the coverage solve may move the "
                "mouth."),
        formula=None,
        physical="Holds the ICW mouth radius fixed during a coverage solve.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "icw_seed": _make(
        "icw_seed",
        label="ICW seed profile",
        unit=None,
        summary="Nested OSSE or R-OSSE parameter mapping the ICW curve is fitted to.",
        detail=("The mesher samples the nested meridian and fits a curvature B-spline to it. "
                "Seed mode is an alternative to direct coefficients and to target mode. It "
                "is a mapping, not a scalar knob."),
        formula="fit_from_points(sample(seed_from_osse or seed_from_rosse))",
        physical="Starts the ICW curve from an existing OSSE/R-OSSE meridian.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "icw_coeffs": _make(
        "icw_coeffs",
        label="ICW curvature coefficients",
        unit="1/mm",
        summary="Direct list of curvature B-spline coefficients, each in inverse millimetres.",
        detail=("Direct mode needs this list together with icw_S. Each value is a curvature "
                "coefficient over normalised arc length. The solver integrates the spline to "
                "get the tangent angle and then the meridian."),
        formula="kappa(sigma) = sum_i icw_coeffs[i] B_i(sigma)",
        physical="Defines the ICW curvature law directly.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3b. ICW config parameters"),
    ),
    "icw_S": _make(
        "icw_S",
        label="ICW arc length",
        unit="mm",
        summary="Total arc length of the ICW meridian in direct-coefficient mode.",
        detail=("Curvature integrates over normalised sigma, so S converts the integral to a "
                "physical length. It is a length in millimetres, not a fraction. Direct mode "
                "needs it together with icw_coeffs."),
        formula="theta(s) = theta0 + S integral_0^sigma kappa dv",
        physical="Sets how long the direct-mode ICW meridian is.",
        code_ref=_PF + "build_icw_curve",
        doc_ref=(_MESHER, "### 3a. Description (from code)"),
    ),
    # ---------------------------------------------------------------- FREEFORM
    "profileH": _make(
        "profileH",
        label="Horizontal meridian profile",
        unit=None,
        summary="Horizontal meridian: anchor points plus optional throat and mouth tangent angles.",
        detail=("The mapping carries points plus optional throatAngleDeg and mouthAngleDeg. "
                "Each point is [z_mm, r_mm] or [z_mm, r_mm, angleDeg]; z must strictly "
                "increase, r must stay positive, and there are 2 to 64 anchors. The cubic "
                "Hermite spline uses chordal arc-length fraction as its knot parameter."),
        formula="cubic Hermite through the H anchors with endpoint tangent angles",
        physical="Shapes the wall in the horizontal plane.",
        code_ref=_FF,
        doc_ref=(_MESHER, "### 4b. Profile representation"),
        flags=_NOT_KNOB,
    ),
    "profileV": _make(
        "profileV",
        label="Vertical meridian profile",
        unit=None,
        summary="Vertical meridian: anchor points plus optional throat and mouth tangent angles.",
        detail=("It has the same structure as profileH, and its anchor count may differ. Its "
                "first and last z and its throat radius must match profileH. The pair "
                "together defines the FREEFORM surface."),
        formula="cubic Hermite through the V anchors with endpoint tangent angles",
        physical="Shapes the wall in the vertical plane.",
        code_ref=_FF,
        doc_ref=(_MESHER, "### 4b. Profile representation"),
        flags=_NOT_KNOB,
    ),
    "crossSections": _make(
        "crossSections",
        label="Cross-section schedule",
        unit=None,
        summary="Ordered cross-section stations that morph the outline along the horn.",
        detail=("Each station is a mapping with t and shape; the first station is at the "
                "throat and the last at the mouth. A superellipse station adds exponent, a "
                "rounded rectangle adds cornerRadiusMm, and 2 to 32 stations are allowed. "
                "The blend between stations is smootherstep."),
        formula="r_3D(t, phi) = r_meridian(t) * station_shape(phi)",
        physical="Changes the outline family along the horn without changing the meridians.",
        code_ref=_FF,
        doc_ref=(_MESHER, "### 4d. Cross-section stations (crossSections)"),
        flags=_NOT_KNOB,
    ),
    "inflectionPolicy": _make(
        "inflectionPolicy",
        label="Inflection policy",
        unit=None,
        summary="Whether a reverse-curvature span in a FREEFORM meridian warns or is rejected.",
        detail=("The legal values are warn and reject. warn reports the span and continues; "
                "reject refuses the design. It is a validation policy, not a shape knob."),
        formula=None,
        physical="Changes whether a rippled meridian is accepted, not its shape.",
        code_ref=_FF,
        doc_ref=(_MESHER, "### 4c. Freeform config keys"),
    ),
    # ---------------------------------------------------------------- MEH mid-ports (OSSE)
    "mid_ports": _make(
        "mid_ports",
        label="OSSE mid-port patches",
        unit=None,
        summary=("Opt-in L1 MEH mid-port recipe: walls, z_frac, across_frac, port_along_mm, "
                 "slide_mm — re-tags flush exits as tag 10."),
        detail=("Absent = byte-identical mesher config and mesh. When present the pinned "
                "mesher fork `hornlab-search/osse-midports` cuts flush rectangles on the "
                "named walls and tags them 10 for multi-source MEH solves. It is a mapping "
                "recipe, not a searchable scalar."),
        formula=None,
        physical="Opens flush mid-range exits on the OSSE walls for MEH multi-source drive.",
        code_ref=_FAM + "FAMILY_KEYS",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
        flags=_NOT_KNOB,
    ),
}


NATIVE_TYPOLOGY_NOTES: dict[str, dict[str, KnobContext]] = {
    "osse_baseline": {
        "a_deg": _ctx(
            "Half-angle in this config",
            "This config's a_deg is the mesher half-angle; the target coverage is the total angle.",
            "The target block scores the full included angle, so the two numbers differ by "
            "the same factor of two that the OSSE convention implies. Do not copy a target "
            "coverage value into a_deg without halving it.",
            physical="Sets the OSSE coverage half-angle.",
        ),
        "s": _ctx(
            "Termination enabled here",
            "This seed enables the OSSE termination, so n and q are live.",
            "The seed carries a nonzero termination amplitude. That is why n and q are not "
            "inert in this typology even though they are conditional keys.",
            physical="Turns the OSSE mouth termination on.",
        ),
        "exponent": _ctx(
            "Family-level cross-section exponent",
            "Here exponent is the OSSE-family cross-section key, not a FREEFORM station field.",
            "It pairs with aspect_ratio at the family level. The shipped seed uses the "
            "higher value that the prose/code mismatch records, so read the entry's "
            "doc_mismatch note before treating either value as canonical.",
            physical="Squares off the OSSE cross-section outline.",
        ),
    },
    "rosse_baseline": {
        "q": _ctx(
            "Blend exponent in this config",
            "In this R-OSSE config q is the throat-to-mouth blend exponent, not the OSSE saturation.",
            "The seed documents the R-OSSE default as the blend value. Reading q as a "
            "superellipse saturation here would describe the wrong equation.",
            physical="Moves the blend hand-over between throat and mouth curves.",
        ),
        "R_mm": _ctx(
            "Reference radius in this config",
            "R_mm is the nominal mouth/reference radius; this family derives its axial length.",
            "R-OSSE refuses an explicit L_mm, so R_mm plus the shape keys set both the "
            "mouth and the derived depth. Do not look for a separate length knob here.",
            physical="Sets the mouth size and the derived depth together.",
        ),
        "tmax": _ctx(
            "Full curve in this config",
            "tmax is left at its full value, so the wall reaches the blended mouth.",
            "At full truncation the wall can pass vertical and roll back naturally. A "
            "smaller tmax would stop it before the mouth.",
            physical="Lets the natural R-OSSE rollback run to the mouth.",
        ),
        "exponent": _ctx(
            "Family-level cross-section exponent",
            "Here exponent is the cross-section key, not a FREEFORM station field.",
            "It pairs with aspect_ratio at the family level. The shipped seed uses the "
            "higher value that the prose/code mismatch records.",
            physical="Squares off the R-OSSE cross-section outline.",
        ),
    },
    "icw_termination": {
        "termination": _ctx(
            "Flat baffle in this config",
            "termination selects flat_baffle, so the L/R/coverage/hold targets are active.",
            "This typology is the flat-baffle ICW route. The rollback keys are not the "
            "active termination controls here.",
            physical="Stops the wall at a flat mouth.",
        ),
        "theta1_deg": _ctx(
            "Present but not the active termination",
            "theta1_deg is a rollback target and is not read in this flat-baffle config.",
            "The seed carries a bounded theta1 value, but termination is flat_baffle, so "
            "the rollback terminal angle is not the law being applied. Do not describe it "
            "as this typology's mouth control.",
            physical="Would set a rollback terminal angle if rollback mode were selected.",
        ),
        "coverage_angle_deg": _ctx(
            "Half-angle in this config",
            "This is the ICW wall half-angle; the target coverage is the total included angle.",
            "The mesher requires it between the throat angle and vertical. The target block "
            "scores the full included angle, so the two are not numerically equal.",
            physical="Sets the wall angle held through the coverage plateau.",
        ),
        "hold_start": _ctx(
            "Coverage plateau start here",
            "Fraction of arc length where this config's constant-angle plateau begins.",
            "It is a fraction, not a length, and must stay below hold_end. It is active "
            "because this config uses coverage mode.",
            physical="Moves the plateau start along the meridian.",
        ),
        "hold_end": _ctx(
            "Coverage plateau end here",
            "Fraction of arc length where this config's constant-angle plateau ends.",
            "It is a fraction, not a length, and must stay above hold_start. It is active "
            "because this config uses coverage mode.",
            physical="Moves the plateau end along the meridian.",
        ),
    },
    "icw_rollback": {
        "icw_seed": _ctx(
            "Rollback comes from the seed",
            "This config fits an ICW curve to a rolled-back R-OSSE seed rather than solving targets.",
            "The nested seed carries a full R-OSSE curve whose wall turns past vertical, "
            "and the ICW B-spline inherits that rollback. The searched keys live inside the "
            "nested seed, not at the ICW top level.",
            physical="Starts the ICW curve from a naturally rolled-back meridian.",
        ),
        "termination": _ctx(
            "Not the rollback switch here",
            "This config does not set the categorical termination; the seed route supplies the rollback.",
            "Reading the default termination as this typology's mouth control would be "
            "wrong. The rollback is inherited from icw_seed.",
            physical="Would choose a target route if the seed route were not used.",
        ),
        "theta1_deg": _ctx(
            "Not used by this seed route",
            "theta1_deg is a rollback target key; it is absent from this seed-driven config.",
            "The terminal wall angle comes from the nested R-OSSE seed. Setting theta1 here "
            "would not change that inherited rollback.",
            physical="Would set a rollback target only in targets mode.",
        ),
        "tmax": _ctx(
            "Nested full-saturation control",
            "tmax belongs to the nested R-OSSE seed and controls how far its rollback runs.",
            "At full saturation the seed wall turns past vertical, which is what gives this "
            "typology its rollback. It is a seed key, reached as icw_seed.tmax.",
            physical="Lets the nested seed reach a full rollback.",
        ),
    },
    "freeform_sculpt": {
        "profileH": _ctx(
            "Control-point radii are the search dimensions",
            "The horizontal interior anchor radii are searched; z values and the throat are pinned.",
            "Only radius fields move, so z stays strictly increasing and the H/V span stays "
            "equal. That is why this config can sculpt the wall without breaking the "
            "FREEFORM guards.",
            physical="Moves the horizontal wall at the interior anchors.",
        ),
        "profileV": _ctx(
            "Control-point radii are the search dimensions",
            "The vertical interior anchor radii are searched; z values and the throat are pinned.",
            "Only radius fields move, so z stays strictly increasing and the H/V span stays "
            "equal. The H and V anchors share the same z schedule here.",
            physical="Moves the vertical wall at the interior anchors.",
        ),
        "crossSections": _ctx(
            "Circle-to-superellipse schedule",
            "This config runs a circular throat section to a superellipse mouth section.",
            "The schedule has a throat station and a mouth station, and the searched "
            "exponent lands in the superellipse station. The smootherstep blend between the "
            "two stations is the mesher's job.",
            physical="Morphs the outline from round at the throat to squared at the mouth.",
        ),
        "exponent": _ctx(
            "Alias into the superellipse station",
            "The searched exponent is the superellipse station's field, reached through the FREEFORM alias.",
            "families.py resolves a bare exponent for FREEFORM to the first superellipse "
            "station in crossSections. It is not a top-level family key in the config even "
            "though the YAML bounds it by that name.",
            physical="Squares off the mouth cross-section.",
        ),
    },
    "freeform_hv": {
        "profileH": _ctx(
            "Only the mouth angle is searched here",
            "The horizontal anchors are pinned; the config searches the horizontal mouth angle.",
            "Because the points do not move, this typology explores wall exit angle rather "
            "than control-point radii. The pinned throat keeps the driver match.",
            physical="Changes the horizontal wall angle at the mouth.",
        ),
        "profileV": _ctx(
            "Only the mouth angle is searched here",
            "The vertical anchors are pinned; the config searches the vertical mouth angle.",
            "Because the points do not move, this typology explores wall exit angle rather "
            "than control-point radii. The vertical bound differs from the horizontal one.",
            physical="Changes the vertical wall angle at the mouth.",
        ),
        "crossSections": _ctx(
            "Circle-to-superellipse schedule",
            "The schedule is fixed: a circular throat station and a superellipse mouth station.",
            "The schedule itself is not searched in this config; only its exponent is. The "
            "blend between stations is smootherstep.",
            physical="Morphs the outline from round to squared.",
        ),
        "exponent": _ctx(
            "Alias into the superellipse station",
            "The YAML bounds a bare exponent that resolves into the superellipse station.",
            "families.FREEFORM_ALIASES routes the name to the first superellipse station. "
            "The station's own field is what the mesher reads.",
            physical="Squares off the mouth cross-section.",
        ),
    },
    "throat_adapter": {
        "throat_ext_length_mm": _ctx(
            "Searched adapter length",
            "This config searches the prepended extension length.",
            "The extension is the typology's point: it moves the driver interface ahead of "
            "the main OSSE wall. A zero length removes it.",
            physical="Moves the start of the horn body away from the driver.",
        ),
        "throat_ext_angle_deg": _ctx(
            "Searched adapter taper",
            "This config searches the extension taper angle.",
            "The taper changes how the adapter radius meets the main throat radius. It is "
            "not the main horn's coverage angle.",
            physical="Narrows or widens the adapter toward the driver.",
        ),
        "slot_length_mm": _ctx(
            "Searched cylindrical spacer",
            "This config searches a straight slot between the extension and the main horn.",
            "The slot holds the throat radius constant over its length. A zero length "
            "removes it.",
            physical="Adds a cylindrical spacer in the throat region.",
        ),
        "exponent": _ctx(
            "Pinned circular section here",
            "The cross-section is pinned circular for this adapter.",
            "The adapter is meant to be axisymmetric, so the cross-section exponent is not "
            "a shape search here. It stays a fixed family key.",
            physical="Keeps the adapter's cross-section circular.",
        ),
    },
}

__all__ = ["DOMAIN", "NATIVE_KNOBS", "NATIVE_TYPOLOGY_NOTES"]
