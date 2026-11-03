# UMAP — Solana OSSE+SF MEH CMA-1000

Interactive UMAP of OK designs from run `20261103T053926Z-screen-8b32a1`
(`solana_osse_meh_sf` budget 1000). Color by **parameter unit-box quartiles**
or **total J** thresholds. The parameter dropdown lists all **18 searchable**
knobs; click a point to show the full physical + unit param table for that design.

## Open the map

GitHub’s file viewer shows source only. Use one of:

1. **HTML preview** (no Pages setup):
   [open interactive map](https://htmlpreview.github.io/?https://github.com/jamescollinharky/Hornfab/blob/feat/solana-sawmod-wg-bench/docs/evidence/UMAP_SOLANA_OSSE_MEH_SF_CMA1000.html)
2. Or download / open `UMAP_SOLANA_OSSE_MEH_SF_CMA1000.html` locally in a browser
   (needs network once for the D3 CDN).

If the preview 404s, the branch name in the URL may have changed — retarget the
blob path to the commit that added this file.

## Method

- Embedding: UMAP on searchable knobs in the unit box `[0,1]^18`
  (`n_neighbors=15`, `min_dist=0.1`, `metric=euclidean`, `seed=42`)
- Points: subsample of OK evals (best 40 + stride + worst 10)
- Parameter colors: unit quartiles `[0,0.25)`, `[0.25,0.5)`, `[0.5,0.75)`, `[0.75,1]`
  mapped to physical bounds from the run `config.yaml`
- J colors: `<9`, `9–12`, `12–16`, `≥16`

This is a **geometry / search-cloud** view, not a per-term loss decomposition.
