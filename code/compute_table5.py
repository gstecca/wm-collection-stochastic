"""
Recompute Table 5 of the paper (SM vs EEV, VSS by group n x C) from summary/sm_eev_results.csv.

Two conventions are printed:
  * 'original'  : the one used in the first submission (group VSS_a and gap_a averaged
                  over strictly positive values only, i.e. instances with VSS = 0 or gap = 0 were dropped);
  * 'revised'   : all averages taken over every instance with a feasible solution (VSS = 0 included).
It also prints the overall averages over the different instance populations.
"""
import os
import pandas as pd

here = os.path.dirname(os.path.abspath(__file__))
d = pd.read_csv(os.path.join(here, '..', 'summary', 'sm_eev_results.csv'))
s = d[d.solved == True].copy()
pos = lambda x: x[x > 0]                 # filter used in the first submission (raw values, round-off ~1e-13 kept)
s['VSS_pct'] = s['VSS_pct']              # raw values as produced by main.py
EPS = 1e-6                               # VSS below EPS (in %) is treated as zero

grp = s.groupby(['n', 'C'])
tab = pd.DataFrame({
    'feasible': grp.size(),
    'instances': d.groupby(['n', 'C']).size(),
    'VSS_a_original': grp.VSS_pct.apply(lambda x: pos(x).mean()),
    'VSS_a_revised': grp.VSS_pct.apply(lambda x: x.clip(lower=0).mean()),
    'n_VSS_pos': grp.VSS_pct.apply(lambda x: (x > EPS).sum()),
    'VSS_M': grp.VSS_pct.max(),
    'SM_time_a': grp.SM_runtime_s.mean(), 'SM_time_M': grp.SM_runtime_s.max(),
    'SM_gap_a_original': grp.SM_gap.apply(lambda x: pos(x).mean()).fillna(0),
    'SM_gap_a_revised': grp.SM_gap.mean(), 'SM_gap_M': grp.SM_gap.max(),
    'n_SM_gap_gt_0.1pct': grp.SM_gap.apply(lambda x: (x > 0.001).sum()),
    'EEV_time_a': grp.EEV_runtime_s.mean(), 'EEV_time_M': grp.EEV_runtime_s.max(),
    'EEV_gap_a_revised': grp.EEV_gap.mean(), 'EEV_gap_M': grp.EEV_gap.max(),
}).round(2)
pd.set_option('display.width', 250)
print(tab.to_string())
tab.to_csv(os.path.join(here, '..', 'summary', 'table5_recomputed.csv'))

cert = s[(s.SM_gap <= 0.001) & (s.EEV_gap <= 0.001)]
print()
print(f"instances generated                               : {len(d)}")
print(f"proven infeasible                                 : {(d.solved != True).sum()}")
print(f"feasible (SM and EEV solution available)          : {len(s)}")
print(f"mean VSS over all feasible instances              : {s.VSS_pct.mean():.2f}%  (median {s.VSS_pct.median():.2f}%)")
print(f"mean VSS over instances with SM gap <= 0.1%       : {s[s.SM_gap <= 0.001].VSS_pct.mean():.2f}%  (n={len(s[s.SM_gap <= 0.001])})")
print(f"mean VSS over instances with SM,EEV gap <= 0.1%   : {cert.VSS_pct.mean():.2f}%  (n={len(cert)})")
print(f"mean VSS over instances with SM gap > 0.1%        : {s[s.SM_gap > 0.001].VSS_pct.mean():.2f}%  (n={len(s[s.SM_gap > 0.001])})")
print(f"mean VSS over instances with VSS > 0 (raw filter) : {pos(s.VSS_pct).mean():.2f}%  (n={len(pos(s.VSS_pct))})")
print(f"mean VSS over instances with VSS > {EPS}          : {s.VSS_pct[s.VSS_pct > EPS].mean():.2f}%  (n={(s.VSS_pct > EPS).sum()})")
print(f"instances with VSS = 0 (|VSS| <= {EPS})           : {(s.VSS_pct.abs() <= EPS).sum()}")
w = (tab.VSS_a_original * tab.feasible).sum() / tab.feasible.sum()
print(f"group VSS_a(original) weighted by feasible counts : {w:.2f}%  (reviewer's 27.02%)")
