# Asymmetry indices

The brain is not symmetric. Structural and functional laterality have a long literature (Geschwind & Galaburda 1985[^geschwind1985]; Toga & Thompson 2003[^toga2003]; Kong et al. 2018 ENIGMA laterality of cortical thickness[^kong2018]; Guadalupe / ENIGMA laterality working group). In epilepsy, **which hippocampus is smaller or less connected** is often the clinical question.

This package turns a pair of homologous node strengths (or volumes) into laterality indices. Graph theory stops at \(s_L\) and \(s_R\); everything below is a contrast on that pair.

## Why laterality rather than \(s_L\) and \(s_R\) separately?

Raw strength is confounded by global reconstruction, brain size, and streamline count. A **within-subject** left-versus-right ratio cancels a large class of those confounds (any factor that multiplies both hemispheres). It does **not** cancel hemisphere-specific reconstruction bias (known gyral biases, B0 distortion that differs by side) — QC still matters.

Toga & Thompson (2003) review petalia, planum temporale, and volumetric asymmetries. Kong et al. (2018) show that cortical thickness laterality is reproducible at scale. Hippocampal **volumetric** asymmetry is a standard HS biomarker (Jack and subsequent epilepsy-MRI reviews). Connectivity AI is the same algebraic form on a different measurement.

## Side AI

For homologous values \(x_L, x_R\) (strength or volume):

\[
\mathrm{AI} = \frac{x_L - x_R}{x_L + x_R} \in [-1, 1]
\]

Positive = left-dominant under this sign convention. When \(x_L+x_R=0\), AI is **undefined (NaN)**, not 0 — a zero would look like perfect symmetry of two missing nodes.

Properties:

- Scale-free: multiplying both sides by \(c>0\) does not change AI. That is why global streamline-count differences drop out.
- Bounded: useful for mixed models and ROC.
- Nonlinear near zero: a 10 vs 0 pair is \(\mathrm{AI}=1\), same as 10 000 vs 0.

A **log-ratio**

\[
\log\mathrm{AI} = \ln(x_L / x_R)
\]

is unbounded and more sensitive when one side is near 0. We store `log_ai` alongside `side_ai`. It is undefined for non-positive values; those rows stay NaN.

Some papers use \((R-L)/(R+L)\) (right-minus-left). **Always state the numerator.** This CLI uses left-minus-right for `side_ai`.

## SOZ-aligned AI

If the seizure-onset zone side is known:

\[
\mathrm{AI_{SOZ}} = \sigma_{\mathrm{SOZ}} \cdot \mathrm{AI}
\]

with a documented \(\sigma_{\mathrm{SOZ}}\) so that **positive means ipsilateral stronger than contralateral** (or the inverse — the CSV header / `manifest.json` is the contract). Bilateral or unknown SOZ cannot be aligned; those rows stay as side AI.

Piper et al. 2026[^piper2026] treat SOZ as a **between-subject factor** in a mixed GLM (nucleus × side × group/SOZ) rather than only a sign flip. Both are valid:

| Approach | Question |
|---|---|
| Sign-flip AI | “Is the SOZ side the weak side?” as one number per subject |
| Mixed GLM with side × SOZ | “Does the L/R pattern depend on which side is epileptic?” |

`--participants` with a `soz_side` column enables the first; `nodestrength analyze --within nucleus side --between group` is the second.

## Volume AI

Same formulae on parcel volume in mm³. In HS, volume AI is the classical imaging biomarker; connectivity AI is complementary. `dkt-ai-cohort --with-volume-ai` writes both and a compare table. Volume typically comes from `dk_nodes.mif` on the tractography grid (not always identical to FreeSurfer `aseg` volumes — another named choice).

## Intrahemispheric AI

Compute \(s_L, s_R\) from the intrahemispheric mask ([Node strength](strength.md#intrahemispheric-and-interhemispheric-strength)), then AI. This is the IDEAS hippocampus default: contralateral projections (fornix/commissural reconstructions, callosal false positives) should not cancel a unilateral deficit.

`dkt-ai-cohort` always writes `side_ai` on whole-brain, intra, and inter strengths so you can see whether a laterality effect is driven by within-hemisphere wiring.

## Homologous pairing

AI is only defined for **paired** nodes: `Left-Hippocampus` with `Right-Hippocampus`, `lh.superiortemporal` with `rh.superiortemporal`, THOMAS `AV_L` with `AV_R`. Midline structures (brainstem, some vermis labels) have no pair; they belong in a strength table, not an AI table. A LUT that orders left cortex then right cortex with a different split count will silently pair the wrong regions — the most dangerous bug in this analysis. Independent GraphML extraction is how this project checks Lausanne LUTs.

## ROC, sensitivity, specificity

To ask “does hippocampal AI separate left-HS from controls?” treat AI (or \(-AI\)) as a scalar classifier:

1. ROC curve; **AUC** (Hanley & McNeil 1982). Correlated AUCs: DeLong et al. 1988[^delong1988].
2. Pick an **operating point** → sensitivity, specificity, PPV, NPV.

**Threshold choice changes sensitivity/specificity even when AUC is identical.**

| Rule | Typical origin | Notes |
|---|---|---|
| Closest point to \((0,1)\) in ROC space | common Python | Euclidean in ROC coordinates, which are not equally scaled clinically |
| Youden \(J=\mathrm{sens}+\mathrm{spec}-1\) | Youden 1950[^youden1950] | Maximises vertical distance from diagonal |
| MATLAB `perfcurve` `optrocpt` | Statistics Toolbox | **Not** always closest-to-(0,1) |
| `pos_label` inverted | codebook | Maps \(\mathrm{AUC}\mapsto 1-\mathrm{AUC}\) |

If a MATLAB table used `pos_label=0` for “Left HS”, sklearn with `pos_label=1` inverts the curve. That is a **label convention**, not a different AI formula. Matching AUC to \(10^{-15}\) and still missing sens/spec almost always means a different operating point (`optrocpt` vs closest-to-corner). If you need MATLAB’s point, call MATLAB; do not “fix” the strength formula.

Prevalence matters for PPV/NPV; AUC does not know the clinic’s base rate.

## Pitfalls

- Mixing det and prob Count in one ROC.
- Mixing scales (L60 vs L250 hippocampus is the same biological structure but a different neighbourhood in \(W\)).
- Treating MeanFA AI as Count AI.
- Pairing unpaired nodes (brainstem) or the wrong LUT order.
- Coding bilateral SOZ as left.
- Reporting sensitivity without the threshold rule.

## Further reading

- Toga & Thompson 2003 — mapping brain asymmetry[^toga2003]
- Geschwind & Galaburda 1985 — classical laterality[^geschwind1985]
- Kong et al. 2018 — ENIGMA cortical laterality[^kong2018]
- Bernhardt, Bonilha & Gross 2015 — connectomics in epilepsy[^bernhardt2015]
- Piper et al. 2026 — thalamocortical strength, mixed GLM, SOZ[^piper2026]
- Jack / Woermann / hippocampal sclerosis MRI reviews — volumetric AI as the ancestor of this formula

[^geschwind1985]: Geschwind N, Galaburda AM. Cerebral lateralization. *Arch Neurol*. 1985;42:428–459.
[^toga2003]: Toga AW, Thompson PM. Mapping brain asymmetry. *Nat Rev Neurosci*. 2003;4:37–48. [doi:10.1038/nrn1009](https://doi.org/10.1038/nrn1009)
[^kong2018]: Kong X-Z et al. Mapping cortical brain asymmetry in 17,141 healthy individuals worldwide via the ENIGMA Consortium. *PNAS*. 2018;115:E5154–E5163.
[^piper2026]: Piper RJ et al. *Epilepsia*. 2026;67:1901–1915.
[^delong1988]: DeLong ER, DeLong DM, Clarke-Pearson DL. Comparing the areas under two or more correlated ROC curves. *Biometrics*. 1988;44:837–845.
[^youden1950]: Youden WJ. Index for rating diagnostic tests. *Cancer*. 1950;3:32–35.
[^bernhardt2015]: Bernhardt BC, Bonilha L, Gross DW. *Epilepsia*. 2015;56:1837–1846.
