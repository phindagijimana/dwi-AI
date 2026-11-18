# Connectomics

**Connectomics** is the project of mapping neural connections at a chosen scale (Sporns, Tononi & Kötter 2005[^sporns2005]; Lichtman & Sanes 2008 at microscale; Hagmann 2008 and Van Essen / Human Connectome Project at macroscale[^hagmann2008][^vanessen2013]).

This tool lives at **macroscale, in vivo, diffusion MRI**.

## How a structural connectome is made

1. Estimate fibre orientation distributions (CSD: Tournier 2007; MSMT-CSD: Jeurissen 2014[^jeurissen2014]).
2. Grow streamlines (probabilistic iFOD2 or deterministic FACT/SD_STREAM).
3. Optionally filter them (SIFT/SIFT2: Smith 2013, 2015[^smith2013][^smith2015]; COMMIT: Daducci 2015[^daducci2015]).
4. Count (weighted) streamlines between parcels (`tck2connectome`).

QSIPrep standardises step 0 (preprocessing)[^cieslak2021]; QSIRecon and MRtrix3 standardise 1–4[^tournier2019].

### Deterministic vs probabilistic

| | Deterministic | Probabilistic (iFOD2) |
|---|---|---|
| Algorithm | Follow the peak | Sample the FOD |
| Typical matrix | Sparser, weaker long-range | Denser, more false-positive long-range |
| Failure mode | Misses kissing/crossing | Hallucinated connections |

They are **different experiments**. A bitwise-identical Count matrix labelled “det” and “prob” is a packaging error, not a scientific replication. True deterministic Count on the same subjects is sparser and will move AUC.

Reviews of tractography limits: Jones, Knösche & Turner 2013[^jones2013]; Thomas et al. 2014[^thomas2014]; Maier-Hein et al. 2017[^maierhein2017]; Schilling et al. 2019[^schilling2019]; Yeh et al. 2021[^yeh2021].

## Edge weights are different graphs

On the same streamline set you can write:

| Weight | Interpretation | Use with strength? |
|---|---|---|
| Count / SIFT2 | Amount of reconstructed connection | Yes — this is the usual \(W\) |
| CountScaled | Count ÷ (volume or length) | Sometimes; know the divisor |
| Mean FA | Microstructure of the connecting bundle | Strength then mixes anatomy with FA |
| MD | Diffusivity along the bundle | Same caveat |
| Length | Mean streamline length | Strength becomes “total millimetres of track”, not wiring mass |

**Never** concatenate Count AI and MeanFA AI in one ROC without labelling the edge definition. Gong et al. 2009 and Hagmann 2008 discuss weighted vs binary cortical networks[^gong2009][^hagmann2008].

## Parcellations used here

**Desikan–Killiany** (Desikan 2006)[^desikan2006] — 34 cortical gyri per hemisphere plus FreeSurfer subcortical. MRtrix `fs_default` is 84 rows.

**Lausanne 2008 / Cammoun** (Hagmann 2008; Cammoun 2012)[^cammoun2012] — recursive splits of DK. Scales ~36 / 60 / 125 / 250. Hippocampus is **not** split; it stays one node per side. Row order comes from GraphML, not `FreeSurferColorLUT.txt`.

**THOMAS** thalamic nuclei (Su 2019)[^su2019] — used with cortex in Piper et al. 2026[^piper2026].

Other atlases you will meet: AAL (Tzourio-Mazoyer 2002), Harvard-Oxford, Schaefer 2018[^schaefer2018], Glasser 2016 MMP[^glasser2016], Brainnetome (Fan 2016). Changing atlas changes every graph metric (Zalesky 2010[^zalesky2010]).

## Functional connectomics (not computed here)

Resting-state edges are typically Pearson or partial correlations of ROI time series (Biswal 1995; Smith 2011[^smith2011]; Power 2011 on motion[^power2011]). Graph measures can then be applied to that matrix — but the null model and thresholding are a literature of their own (van Wijk, Stam & Daffertshofer 2010[^vanwijk2010]). Do not run `strengths_und` on a Fisher-z correlation matrix and interpret it as streamline strength.

## Epilepsy and the connectome

Focal epilepsy is a network disease as much as a lesion disease (Spencer 2002; Richardson 2012; Bernhardt, Bonilha & Gross 2015[^bernhardt2015]; Tavakol 2019). Hippocampal sclerosis studies often report **laterality** of hippocampal connectivity or volume (see [Asymmetry](asymmetry.md)). Piper et al. 2026 measured **thalamocortical** strength in children with focal epilepsy[^piper2026]. The IDEAS cohort analyses in this repository apply the same strength+AI idea to **hippocampus** at Lausanne scales.

[^sporns2005]: Sporns O, Tononi G, Kötter R. *PLoS Comput Biol*. 2005;1:e42.
[^hagmann2008]: Hagmann P et al. *PLoS Biol*. 2008;6:e159.
[^vanessen2013]: Van Essen DC et al. The WU-Minn Human Connectome Project. *NeuroImage*. 2013;80:62–79.
[^jeurissen2014]: Jeurissen B et al. *NeuroImage*. 2014;103:411–426.
[^smith2013]: Smith RE et al. SIFT: Spherical-deconvolution informed filtering of tractograms. *NeuroImage*. 2013;67:298–312.
[^smith2015]: Smith RE et al. SIFT2. *NeuroImage*. 2015;119:338–351.
[^daducci2015]: Daducci A et al. COMMIT: Convex optimization modeling for microstructure informed tractography. *IEEE TMI*. 2015;34:246–261.
[^cieslak2021]: Cieslak M et al. *Nat Methods*. 2021;18:775–778.
[^tournier2019]: Tournier J-D et al. *NeuroImage*. 2019;202:116137.
[^jones2013]: Jones DK, Knösche TR, Turner R. White matter integrity, fiber count, and other fallacies. *NeuroImage*. 2013;73:239–254.
[^thomas2014]: Thomas C et al. Anatomical accuracy of brain connections derived from diffusion MRI tractography is inherently limited. *PNAS*. 2014;111:16574–16579.
[^maierhein2017]: Maier-Hein KH et al. The challenge of mapping the human connectome based on diffusion tractography. *Nat Commun*. 2017;8:1349.
[^schilling2019]: Schilling KG et al. Limits to anatomical accuracy of diffusion tractography using modern approaches. *NeuroImage*. 2019;185:1–11.
[^yeh2021]: Yeh C-H et al. *J Magn Reson Imaging*. 2021;53:1666–1682.
[^gong2009]: Gong G et al. Mapping anatomical connectivity patterns of human cerebral cortex using in vivo diffusion tensor imaging tractography. *Cereb Cortex*. 2009;19:524–536.
[^desikan2006]: Desikan RS et al. *NeuroImage*. 2006;31:968–980.
[^cammoun2012]: Cammoun L et al. *J Neurosci Methods*. 2012;203:386–397.
[^su2019]: Su JH et al. Thalamus Optimized Multi Atlas Segmentation (THOMAS). *NeuroImage*. 2019.
[^piper2026]: Piper RJ et al. *Epilepsia*. 2026;67:1901–1915.
[^schaefer2018]: Schaefer A et al. Local-global parcellation of the human cerebral cortex from intrinsic functional connectivity MRI. *Cereb Cortex*. 2018;28:3095–3114.
[^glasser2016]: Glasser MF et al. A multi-modal parcellation of human cerebral cortex. *Nature*. 2016;536:171–178.
[^zalesky2010]: Zalesky A et al. *NeuroImage*. 2010;50:970–983.
[^smith2011]: Smith SM et al. Network modelling methods for FMRI. *NeuroImage*. 2011;54:875–891.
[^power2011]: Power JD et al. Spurious but systematic correlations in functional connectivity MRI networks arise from subject motion. *NeuroImage*. 2012;59:2142–2154.
[^vanwijk2010]: van Wijk BCM, Stam CJ, Daffertshofer A. Comparing brain networks of different size and connectivity density using graph theory. *PLoS One*. 2010;5:e13701.
[^bernhardt2015]: Bernhardt BC, Bonilha L, Gross DW. Network analysis for a network disorder: the emerging role of connectomics in epilepsy. *Epilepsia*. 2015;56:1837–1846.
