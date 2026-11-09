# wm-collection-stochastic

Benchmark instances, detailed results and code for the paper

> S. Mancini, A. Sclafani, G. Stecca, F. Vocaturo.
> **The waste collection routing problem with time-varying stochastic demand: A machine learning based approach.**
> *Computers & Industrial Engineering* (under review, manuscript CAIE-D-26-05414).

The repository contains:

* the **720 synthetic instances** of the Waste Collection Routing Problem with Time-Varying Stochastic Demand (WCRP-TVSD) used in Section 5, each with its **expected-value counterpart**;
* the **instance generator**, which regenerates all 720 instances exactly from the random seeds;
* the **per-instance solutions** of the scenario-based model (SM), the expected-value model (EM), the EM routes evaluated on the scenarios (EEV), and the 12 deterministic policies;
* **summary tables** (CSV) from which Tables 5–7 of the paper can be recomputed, together with the ML dataset;
* the **optimisation code** (Python + Gurobi) used to produce the results.

Contact: Giuseppe Stecca (IASI-CNR), giuseppe.stecca@iasi.cnr.it

---

## 1. Repository layout

```
wm-collection-stochastic/
├── instances/                 1440 .xlsx files: 720 instances (5 scenarios) + 720 expected-value versions (*_mean.xlsx)
├── results/
│   ├── sm/                    597 SM solutions                    <instance>_res.xlsx
│   ├── eev/                   597 EM routes evaluated in the SM   <instance>_res_fix.xlsx
│   ├── em/                    597 EM solutions                    <instance>_mean_res.xlsx
│   └── policies/              2136 policy solutions (178 x 12)    <instance>_P<k>_res.xlsx
├── summary/
│   ├── sm_eev_results.csv     one row per instance (720): SM, EEV, VSS, run times, gaps
│   ├── policy_results.csv     one row per (instance, policy) (2136): policy model and its SM evaluation
│   ├── ml_dataset.csv         178 rows: 11 features + objective value of the 12 policies (ML training/test data)
│   ├── instance_features.csv  720 rows: the 11 ML features of every instance (Table 3 of the paper)
│   ├── collection_point_types.csv  type (demand pattern) of each collection point of each instance
│   └── table5_recomputed.csv  Table 5 recomputed by code/compute_table5.py
└── code/
    ├── generate_instances.py  instance generator (reproduces instances/ exactly)
    ├── main.py, myutils.py    SM / EM / EEV / policy models (gurobipy), research code as used for the paper
    ├── params.json            run parameters (time limit, model type, ...)
    ├── Instances_list.xlsx, instances_list_N8_filtered.xlsx   instance lists read by main.py
    ├── compute_table5.py      recomputes Table 5 and the overall VSS statistics
    └── aggregate_policy_results.py   aggregation used for Table 6
```

## 2. Instance naming

```
I3_N<n>_M<m>_T<Tmax>_C<C>_Dep<depot>_s<seed>[ _mean ].xlsx
```

| field | meaning | values |
|---|---|---|
| `N` | number of collection points *n* | 5, 6, 7, 8 |
| `M` | number of vehicles *m* | 3, 4 |
| `T` | length of the day *T*max (3 equal time slots) | 15, 30, 45 |
| `C` | vehicle capacity *C* | 150, 200, 250 |
| `Dep` | depot position | `Central` = (5,5), `LowerLeft` = (0,0) |
| `s` | random seed | 0, 1, 2, 3, 4 |
| `_mean` | expected-value instance (one scenario with expected increments) | |

4 × 2 × 3 × 3 × 2 × 5 = **720 instances**.

## 3. File format

Every instance is an Excel workbook with the following sheets.

| sheet | columns | content |
|---|---|---|
| `params` | `param`, `value` | `name`; `n`; `LT` = \|T\| = 3 time slots; `m`; `LS` = \|S\| = 5 scenarios (1 in `_mean` files); `C`; `p` = 10 (unit penalty for uncollected waste); `Tmax`; `Qmax` = 10000 and `M` = 10000 (big constants of the model, see §6); `service_time` = 0; `D` = 20 (baseline demand); `Depot`; `seed` |
| `nodes` | `i`, `x`, `y`, `service_time` | node 0 is the depot, nodes 1..n the collection points; coordinates in the square [0,10]×[0,10] |
| `edges` | `i`, `j`, `c`, `t` | **placeholder, not used**: travel costs and times are the Euclidean distances between nodes, computed when the instance is loaded (`D2C = D2T = 1` in `params.json`) |
| `time_windows` | `t`, `e`, `l` | start *e*ₜ and end ℓₜ of each time slot (three equal slots of length Tmax/3) |
| `demand` | `j`, `d` | initial demand *d*ⱼ, known at the start of the day |
| `delta` | `j`, `t`, `s`, `delta` | demand increment δʲₜˢ of collection point *j*, appearing at the beginning of slot *t*, in scenario *s* (in `_mean` files: the expected increment, `s = 1`) |
| `delta_expected` | `j`, `t`, `s`, `delta` | expected increment δ̄ⱼₜ (`s = 1`) |

**Units.** All quantities are dimensionless. Distance, travel time and travel cost coincide (1 distance unit = 1 time unit = 1 cost unit). Demands, increments and capacities are expressed in the same volume unit; the penalty *p* = 10 is in cost units per volume unit.

## 4. Instance generation procedure

`code/generate_instances.py` is the exact procedure used for the paper (extracted from the original notebook). Running

```bash
cd code
python generate_instances.py --out ../instances_regenerated \
       --features ../summary/instance_features.csv --types ../summary/collection_point_types.csv
```

regenerates all 1440 files; we checked that the content of every sheet (`params`, `nodes`, `time_windows`, `demand`, `delta`, `delta_expected`, also in the `_mean` files) is identical to the files in `instances/`, and that the features coincide with those used to train the ML models. The regenerated workbooks additionally contain a `types` sheet with the type of every collection point.

For each instance, `random.seed(seed)` (Python standard library, Mersenne Twister) is called and the following draws are performed **in this order**:

1. **Locations.** *n* y-coordinates, then *n* x-coordinates, each `round(U[0,10], 2)`. The depot is at (5,5) (`Central`) or (0,0) (`LowerLeft`).
2. **Increments, pre-drawn per class.** For each of the three classes, *n*·|T|·|S| integers `round(U[a,b])`:
   * low: U[0, 25], expected value 12.5
   * average: U[25, 50], expected value 37.5
   * high: U[50, 75], expected value 62.5
3. **Initial demand.** *d*ⱼ = `round(U[10, 30])` for every collection point (the same distribution for all types).
4. **Type of each collection point.** `randint(1,3)`, equiprobable. The type fixes the class of the increment in each of the three time slots:

   | type | interpretation | slot 1 | slot 2 | slot 3 |
   |---|---|---|---|---|
   | 1 | school-like | high | low | low |
   | 2 | home-like | average | high | low |
   | 3 | restaurant-like | low | low | average |

   The increment of point *j* in slot *t* and scenario *s* is taken from the pre-drawn list of the corresponding class.

**Dependence structure.** Increments are independent across collection points, time slots and scenarios, conditionally on the type of the collection point; time dependence enters only through the type-specific pattern. The five scenarios are equiprobable.

**Seeds.** The seed is reset before generating each instance and the number of random draws depends only on *n*. Hence, for a given (*n*, seed), the coordinates of the collection points, the initial demands, the increments and the types are **the same** for all the 36 combinations of (*m*, Tmax, *C*, depot); these combinations differ in fleet, capacity, time horizon and depot location. The benchmark therefore contains 20 distinct (*n*, seed) sets of collection points and demands, each solved under 36 operating settings.

**Expected-value instance.** `_mean` files are identical to the stochastic ones except that `LS = 1` and the `delta` sheet contains the expected increments δ̄ⱼₜ (12.5, 37.5 or 62.5 according to the class).

## 5. Results

### Per-instance solution files (`results/`)

All result workbooks share the same sheets:

| sheet | content |
|---|---|
| `general` | `objValue`, `runtime` (s), `gap` (Gurobi relative MIP gap, as a fraction), and the five components of the objective: `Z1` routing cost of the planned routes, `Z2` average cost of skipped arcs, `Z3` average cost of the returns from skipping points, `Z4` average penalty for waste exceeding capacity (*p*·Σ R), `Z5` average penalty for waste accumulated after the visit (*p*·Σ L). Objective = Z1 − Z2 + Z3 + Z4 + Z5 |
| `x` | arcs (i, j) of the planned routes |
| `U` | period *t* in which each node is visited |
| `TBar` | arrival time at each node |
| `y` | skipped arcs (i, j) in scenario s |
| `Q` | theoretical cumulative load at each node in each scenario (may exceed *C*) |
| `R` | waste exceeding capacity at the end of each route, per scenario |
| `L` | waste accumulated at each collection point after its visit, per scenario |
| `rho` | collection points where the vehicle is saturated, per scenario |
| `alpha` | skipping points, per scenario |

* `results/sm/*_res.xlsx` — scenario-based model (SM), 5 scenarios, objective = SMobj.
* `results/em/*_mean_res.xlsx` — expected-value model (EM), one scenario with expected increments.
* `results/eev/*_res_fix.xlsx` — SM with routes and visit periods fixed to the EM solution, objective = EMobj (EEV) used in the VSS.
* `results/policies/*_P<k>_res.xlsx` — routes and visit periods of policy P*k* evaluated in the SM, objective = P_obj(k), for the 178 instances of Section 5.3.

### Summary tables (`summary/`)

* `sm_eev_results.csv`: `name, n, m, Tmax, C, depot, seed, solved`, then `SM_obj, SM_runtime_s, SM_gap, SM_Z1..SM_Z5`, `EEV_obj, EEV_runtime_s, EEV_gap, EEV_Z1..EEV_Z5`, `VSS_pct` = 100·(EEV_obj − SM_obj)/SM_obj, `in_policy_subset` (one of the 178 instances used for policies and ML). Values are empty for instances without a feasible solution.
* `policy_results.csv`: `name, policy`, `policy_model_obj, policy_runtime_s, policy_gap, policy_Z1..Z5` (the deterministic model solved by the policy) and `P_obj, P_obj_gap, FixZ1..FixZ5` (its routes evaluated in the SM).
* `ml_dataset.csv`: `ID`, the 11 features of Table 3 and columns `P1..P12` with P_obj(k).

**Infeasible instances.** For 123 of the 720 instances Gurobi proves the SM infeasible, so `solved = False`. For 120 of them (all with depot `LowerLeft` and Tmax = 15) the round trip from the depot to the farthest collection point is longer than Tmax. The other 3 are `I3_N6_M3_T15_C{150,200,250}_DepCentral_s1`, where the 6 points cannot be covered by 3 routes within Tmax = 15. For all the remaining 597 instances a feasible solution of both SM and EEV was found within the time limit of 3600 s.

**Recomputing Table 5.** `python code/compute_table5.py` prints Table 5 together with the overall VSS statistics: 597 feasible instances, mean VSS 19.65%; 548 instances solved with a gap ≤ 0.1%, mean VSS 21.33%.

## 6. Model constants

With the instance data above, the following values are valid for the big constants of the SM (constraint numbers as in the paper):

* (7): Tmax is a valid big-M because Euclidean times satisfy the triangle inequality and service times are zero.
* (10)–(13): M ≥ Q̄ = maxₛ Σⱼ (dⱼ + Σₜ δʲₜˢ). Across the 720 instances, Q̄ ≤ 1024, and in general Q̄ ≤ 255·n.
* (17)–(18): Qmax ≥ max{C, Q̄ − C}. Across the 720 instances, this is ≤ 874.

The files use M = Qmax = 10⁴. All data are integers (multiples of 0.5 in EM and in the capacity-adjusted policies), so |Q − C|/Qmax ≥ 5·10⁻⁵ whenever Q ≠ C, which is above Gurobi's default integrality tolerance (10⁻⁵).

## 7. Running the optimisation code

Requirements: Python ≥ 3.9, `pandas`, `numpy`, `openpyxl`, `gurobipy` (results were obtained with Gurobi 12, a Windows PC with an Intel Core i7-1260P and 32 GB RAM).

`main.py` is the research code used for the paper. It expects `instances/` and `results/` folders and an instance list in the working directory:

```bash
cd code
ln -s ../instances instances && mkdir -p results
# params.json: "MODEL_TYPE": "STOCHASTIC" -> SM, EM and EEV for every instance listed in Instances_list.xlsx
#              "MODEL_TYPE": "POLICY"     -> policies P1..P12 for the instances in instances_list_N8_filtered.xlsx
python main.py                     # all instances of the list
python main.py I3_N5_M3_T15_C150_DepCentral_s0   # a single instance
```

## 8. How to cite

If you use these instances, please cite the paper above (full reference will be added upon publication).

## License

Released under the Apache License 2.0 (see `LICENSE`).
