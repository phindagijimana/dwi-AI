# Asymmetry indices

The brain is not symmetric. Structural and functional laterality are old topics (Geschwind & Galaburda 1985[^geschwind1985]; Toga & Thompson 2003[^toga2003]; Kong et al. 2018 ENIGMA laterality[^kong2018]). In epilepsy, **which hippocampus is smaller / less connected** is often the clinical question.

## Side AI

For homologous strengths \(s_L, s_R\):

\[
\mathrm{AI} = \frac{s_L - s_R}{s_L + s_R} \in [-1, 1]
\]

Positive = left-dominant. This is the same form used for volumetric hippocampal asymmetry for decades (e.g. variants in Jack et al.; see also the epilepsy MRI literature on HS). When \(s_L+s_R=0\), AI is undefined (NaN), not 0.

A **log-ratio** \(\log(s_L / s_R)\) is unbounded and more sensitive near 0; we store it alongside AI.

## SOZ-aligned AI

If the seizure-onset zone is known:

\[
\mathrm{AI_{SOZ}} = \mathrm{sign}(\text{SOZ}) \cdot \mathrm{AI}
\]

with the sign convention **positive = ipsilateral stronger than contralateral** (or the inverse — the CSV header documents the convention used in a given run). Bilateral SOZ cannot be aligned; those rows stay as side AI.

Piper et al. 2026 use SOZ as a between-subject factor in a mixed GLM rather than only a sign flip; both are valid, they answer slightly different questions[^piper2026].

## Volume AI

Same formula on parcel volume (mm³). In hippocampal sclerosis, volume AI is the classical biomarker; connectivity AI asks whether the remaining tissue is also under-wired.

## Intrahemispheric AI

Compute \(s_L, s_R\) from the intrahemispheric mask ([Node strength](strength.md)), then AI. This is the IDEAS hippocampus default: we do not want contralateral projections to cancel a unilateral deficit.

## ROC, sensitivity, specificity

To ask “does hippocampal AI separate left-HS from controls?”:

1. Score \(\mathrm{AI}\) (or \(1-\mathrm{AI}\)) as a classifier.
2. ROC curve; AUC.

**Threshold choice changes sensitivity/specificity even when AUC is identical.**

| Rule | Typical origin | Effect |
|---|---|---|
| Closest point to \((0,1)\) in ROC space | common Python | One operating point |
| Youden \(J = \mathrm{sens}+\mathrm{spec}-1\) | Youden 1950[^youden1950] | Often similar |
| MATLAB `perfcurve` `optrocpt` | Statistics Toolbox | **Not** always closest-to-(0,1) |
| `pos_label` inverted | easy off-by-one | AUC becomes \(1-\mathrm{AUC}\) |

If a MATLAB table used `pos_label=0` for “Left HS”, Python `sklearn` with `pos_label=1` will invert the curve. That is a **label convention**, not a different AI formula. Matching Mahi’s AUC to \(10^{-15}\) and still missing sens/spec almost always means a different operating point (`optrocpt` vs closest-to-corner).

## Pitfalls

- Mixing det and prob Count in one ROC.
- Mixing scales (L60 vs L250 hippocampus is the same biological structure but different neighbourhoods).
- Treating AI of MeanFA as AI of Count.
- Using unpaired nodes (brainstem) in a laterality table.

## Further reading

- Toga & Thompson 2003 — mapping brain asymmetry[^toga2003]
- Kong et al. 2018 — large-scale cortical thickness laterality[^kong2018]
- Guadalupe et al. / ENIGMA laterality working group
- Jokeit, Schacher, and hippocampal sclerosis imaging reviews
- Bernhardt, Bonilha & Gross 2015 — connectomics in epilepsy[^bernhardt2015]
- Piper et al. 2026 — thalamocortical strength, mixed GLM, SOZ[^piper2026]

[^geschwind1985]: Geschwind N, Galaburda AM. Cerebral lateralization. *Arch Neurol*. 1985;42:428–459.
[^toga2003]: Toga AW, Thompson PM. Mapping brain asymmetry. *Nat Rev Neurosci*. 2003;4:37–48. [doi:10.1038/nrn1009](https://doi.org/10.1038/nrn1009)
[^kong2018]: Kong X-Z et al. Mapping cortical brain asymmetry in 17,141 healthy individuals worldwide via the ENIGMA Consortium. *PNAS*. 2018;115:E5154–E5163.
[^piper2026]: Piper RJ et al. *Epilepsia*. 2026;67:1901–1915.
[^youden1950]: Youden WJ. Index for rating diagnostic tests. *Cancer*. 1950;3:32–35.
[^bernhardt2015]: Bernhardt BC, Bonilha L, Gross DW. *Epilepsia*. 2015;56:1837–1846.
