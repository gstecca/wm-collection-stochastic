"""
Instance generator for the WCRP-TVSD benchmark (720 synthetic instances).

This is a standalone, cleaned-up copy of the generation cell of the notebook
`scenario_generator.ipynb` used to build the instances of the paper
"The waste collection routing problem with time-varying stochastic demand:
A machine learning based approach" (Mancini, Sclafani, Stecca, Vocaturo).

It reproduces the instance files bit-for-bit in content (same random calls in the
same order, Python's `random` module, Mersenne Twister) for every combination of
    n in {5,6,7,8}, m in {3,4}, Tmax in {15,30,45}, C in {150,200,250},
    depot in {Central, LowerLeft}, seed in {0,...,4}.

Usage:
    python generate_instances.py --out instances_regenerated [--features features.csv]
"""
import argparse
import itertools
import math
import os
import random

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- constants
LT = 3            # number of time slots |T|
LS = 5            # number of scenarios |S|
P_PENALTY = 10    # unit penalty p for uncollected waste
QMAX = 10000      # big constant Qmax in constraints (17)-(18)
BIG_M = 10000     # big constant M in constraints (10)-(13)
SERVICE_TIME = 0
D = 20            # baseline initial demand: d_j ~ round(U[0.5*D, 1.5*D]) = U[10,30]

# demand increment ranges (integer after rounding)
DELTA_RANGE = {'low': (0, 25), 'average': (25, 50), 'high': (50, 75)}
DELTA_EXPECTED = {k: lo + (hi - lo) / 2 for k, (lo, hi) in DELTA_RANGE.items()}  # 12.5, 37.5, 62.5

# collection-point types and their increment pattern over the 3 time slots
# (1: school-like, 2: home-like, 3: restaurant-like)
PATTERNS = {
    1: ['high', 'low', 'low'],
    2: ['average', 'high', 'low'],
    3: ['low', 'low', 'average'],
}

SQUARE = (0, 10)  # collection points are uniform on [0,10]x[0,10]
DEPOT_POS = {'Central': (5, 5), 'LowerLeft': (0, 0)}
TIME_WINDOWS = {Tmax: [(t * Tmax // 3, (t + 1) * Tmax // 3) for t in range(3)] for Tmax in (15, 30, 45)}


def generate(n, m, Tmax, C, depot, seed):
    random.seed(seed)
    name = f'I3_N{n}_M{m}_T{Tmax}_C{C}_Dep{depot}_s{seed}'

    # --- locations (y first, then x: order of random calls matters)
    lo, hi = SQUARE
    ys = [round(random.random() * (hi - lo) + lo, 2) for _ in range(n)]
    xs = [round(random.random() * (hi - lo) + lo, 2) for _ in range(n)]
    dx, dy = DEPOT_POS[depot]
    xs, ys = [dx] + xs, [dy] + ys

    # --- pre-draw increments for every (j,t,s) in the three classes, then initial demand
    rnd = {}
    for k in ('low', 'average', 'high'):
        a, b = DELTA_RANGE[k]
        rnd[k] = [round(random.random() * (b - a) + a) for _ in range(LS * LT * n)]
    # NB: generation order in the original notebook is low, average, high
    d = [round(random.random() * (1.5 * D - 0.5 * D) + 0.5 * D) for _ in range(n)]

    # --- assign a type to each collection point and pick the increments
    delta, delta_exp, types = [], [], []
    i_d = 0
    for j in range(n):
        typ = random.randint(1, len(PATTERNS))
        types.append(typ)
        for t in range(LT):
            cls = PATTERNS[typ][t]
            for s in range(LS):
                delta.append(rnd[cls][i_d])
                i_d += 1
            delta_exp.append(DELTA_EXPECTED[cls])

    idx = list(itertools.product(range(1, n + 1), range(1, LT + 1), range(1, LS + 1)))
    idx_e = list(itertools.product(range(1, n + 1), range(1, LT + 1), [1]))
    tw = TIME_WINDOWS[Tmax]
    sheets = {
        'params': pd.DataFrame({'param': ['name', 'n', 'LT', 'm', 'LS', 'C', 'p', 'Tmax', 'Qmax', 'M',
                                          'service_time', 'D', 'Depot', 'seed'],
                                'value': [name, n, LT, m, LS, C, P_PENALTY, Tmax, QMAX, BIG_M,
                                          SERVICE_TIME, D, depot, seed]}),
        'nodes': pd.DataFrame({'i': range(n + 1), 'x': xs, 'y': ys, 'service_time': [SERVICE_TIME] * (n + 1)}),
        'time_windows': pd.DataFrame({'t': [1, 2, 3], 'e': [a for a, _ in tw], 'l': [b for _, b in tw]}),
        'demand': pd.DataFrame({'j': range(1, n + 1), 'd': d}),
        'delta': pd.DataFrame({'j': [a for a, _, _ in idx], 't': [b for _, b, _ in idx],
                               's': [c for _, _, c in idx], 'delta': delta}),
        'delta_expected': pd.DataFrame({'j': [a for a, _, _ in idx_e], 't': [b for _, b, _ in idx_e],
                                        's': 1, 'delta': delta_exp}),
        'types': pd.DataFrame({'j': range(1, n + 1), 'type': types}),
    }

    # --- instance features used by the ML policy selector (Table 3 of the paper)
    dist_depot = [math.dist([x, y], [xs[0], ys[0]]) for x, y in zip(xs[1:], ys[1:])]
    gx, gy = sum(xs[1:]) / n, sum(ys[1:]) / n
    dist_g = [math.dist([x, y], [gx, gy]) for x, y in zip(xs[1:], ys[1:])]
    feats = dict(ID=name, n_customers=n, n_vehicles=m, depot_location=depot,
                 dispersion_distance_depot=np.std(dist_depot), dispersion_customers=np.std(dist_g),
                 perc_pattern_school=types.count(1) / n, perc_pattern_home=types.count(2) / n,
                 perc_pattern_restaurant=types.count(3) / n,
                 expected_demand_on_tot_capacity=(sum(d) + sum(delta_exp)) / (C * m),
                 initial_demand_on_tot_capacity=sum(d) / (C * m), time_slot_size=Tmax)
    return name, sheets, feats


def write(name, sheets, out):
    os.makedirs(out, exist_ok=True)
    # 'edges' is an empty placeholder: arc costs/times are Euclidean distances computed by the solver code
    sheets['edges'] = pd.DataFrame(columns=['i', 'j', 'c', 't'])
    order = ['params', 'nodes', 'edges', 'time_windows', 'demand', 'delta', 'delta_expected', 'types']
    with pd.ExcelWriter(os.path.join(out, name + '.xlsx')) as w:
        for k in order:
            sheets[k].to_excel(w, sheet_name=k, index=False)
    # expected-value instance (single scenario with expected increments), used by EM / policies
    pm = sheets['params'].copy()
    pm.loc[pm.param == 'name', 'value'] = name + '_mean'
    pm.loc[pm.param == 'LS', 'value'] = 1
    with pd.ExcelWriter(os.path.join(out, name + '_mean.xlsx')) as w:
        pm.to_excel(w, sheet_name='params', index=False)
        for k in ['nodes', 'edges', 'time_windows', 'demand']:
            sheets[k].to_excel(w, sheet_name=k, index=False)
        sheets['delta_expected'].to_excel(w, sheet_name='delta', index=False)
        sheets['types'].to_excel(w, sheet_name='types', index=False)


def all_configs():
    for n in [5, 6, 7, 8]:
        for m in [3, 4]:
            for Tmax in [15, 30, 45]:
                for C in [150, 200, 250]:
                    for depot in ['Central', 'LowerLeft']:
                        for seed in [0, 1, 2, 3, 4]:
                            yield n, m, Tmax, C, depot, seed


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='instances_regenerated')
    ap.add_argument('--features', default=None, help='optional CSV with the ML features of every instance')
    ap.add_argument('--types', default=None, help='optional CSV with the type (1,2,3) of every collection point')
    a = ap.parse_args()
    feats, types = [], []
    for cfg in all_configs():
        name, sh, f = generate(*cfg)
        write(name, sh, a.out)
        feats.append(f)
        types.append(sh['types'].assign(instance=name)[['instance', 'j', 'type']])
    if a.types:
        pd.concat(types).to_csv(a.types, index=False)
    if a.features:
        pd.DataFrame(feats).to_csv(a.features, index=False)
    print(f'{len(feats)} instances written to {a.out}')
