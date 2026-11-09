from myutils import *
import gurobipy as gb
from gurobipy import GRB
import sys
import math
import os



def build_model(inst : Instance):
    xfix = inst.params['XFIX']
    policy = inst.params['POLICY']
    if policy not in ['P0','P7', 'P8', 'P11', 'P12'] :
        return build_model_vrp(inst)  # policies based on VRP model
    mym = mymodel()  # stochastic model or polices based on EVV model
    mm = gb.Model('FSG')
    if inst.params['LOWER_BOUND']:
        #inst.p = 0
        #inst.delta ={k:0 for k in inst.delta}
        pass
    S = inst.S
    LS = inst.LS
    delta = inst.delta
    C = inst.C
    capResize = 0.1
    capResizeP5 = 0.15
    if policy in ['P11', 'P12']:
        capResize = 0.20
        capResizeP5 = 0.30
    if policy in ['P7', 'P8', 'P11', 'P12']:  # P7 and P8 are based on P4, and P5, while P11 and P12 are based on P9 and P10
        delta = inst.delta_expected
        S = [1]
        LS = 1
    
    
    if policy == 'P7' or policy == 'P11':  # just like 'P4' but with the expected value of delta
        C = C*(1-capResize)


    x = {(i,j) : mm.addVar(vtype = GRB.BINARY, name='x_{}_{}'.format(i,j)) for i in inst.Vp for j in inst.Vs if i != j }
    U = {(j,t) : mm.addVar(vtype = GRB.BINARY, name='U_{}_{}'.format(j,t)) for j in inst.Vs for t in inst.T}
    TBar = {i : mm.addVar(vtype = GRB.CONTINUOUS, lb = 0, name = 'TBar_{}'.format(i)) for i in inst.V}
    y = {(i,j,s) :mm.addVar(vtype = GRB.BINARY, name = 'y_{}_{}_{}'.format(i,j,s)) for i in inst.Vp for j in inst.Vs for s in S if j!=i }
    Q = {(j,s) : mm.addVar(vtype=  GRB.CONTINUOUS, lb = 0, name = 'Q_{}_{}'.format(j,s)) for j in inst.V for s in S}
    R = {(j,s) : mm.addVar(vtype=  GRB.CONTINUOUS, lb = 0, name = 'R_{}_{}'.format(j,s)) for j in range(inst.n+1, inst.n+inst.m+1) for s in S}
    L = {(j,s) : mm.addVar(vtype=  GRB.CONTINUOUS, lb = 0, name = 'L_{}_{}'.format(j,s)) for j in range(1, inst.n + 1) for s in S}
    rho = {(j,s) : mm.addVar(vtype=  GRB.BINARY,  name = 'rho_{}_{}'.format(j,s)) for j in range(1, inst.n + 1) for s in S}
    lambd = {(j,s) : mm.addVar(vtype=  GRB.BINARY,  name = 'lambd_{}_{}'.format(j,s)) for j in range(1, inst.n + 1) for s in S}
    alpha = {(j,s) : mm.addVar(vtype=  GRB.BINARY,  name = 'alpha_{}_{}'.format(j,s)) for j in range(1, inst.n + 1) for s in S}

    mm.update()

    ZOB1 = gb.quicksum(inst.c[i,j] * x[i,j] for i in inst.Vp for j in inst.Vs if j != i) 
    ZOB2 = (1/LS) * gb.quicksum(inst.c[i,j] * y[i,j,s] for s in S for i in range(1, inst.n+1) for j in inst.Vs if j != i)
    ZOB3 = (1/LS) * gb.quicksum(inst.c[j,0] * alpha[j,s] for s in S for j in inst.V1)
    ZOB4 = (1/LS) * gb.quicksum(inst.p * R[j,s] for s in S for j in range(inst.n + 1, inst.n + inst.m + 1) )
    ZOB5 = (1/LS) * gb.quicksum(inst.p * L[j,s] for s in S for j in inst.V1)
    ZOB = ZOB1 - ZOB2 + ZOB3 + ZOB4 + ZOB5

    # if LOWER_BOUND:
    #    for i in inst.Vp:
    #     for j in inst.Vs:
    #         for s in inst.S:
    #             if j!=i:
    #                 y[i,j,s].ub = 0

    if len(xfix) > 0:
        for a in xfix:   # dictionary of x to be set equal to (i,j): value
            if xfix[a] < 0.9:
                x[a[0], a[1]].ub = 0
            else:
                x[a[0], a[1]].lb = 1
    if inst.params['FIX_SOLUTION']:  # used to calculate the EVV
        dfxres = pd.read_excel('results/' + inst.name + "_mean_res.xlsx", sheet_name='x')
        for index, row in dfxres.iterrows():
            if row['x'] < 0.99:
                x[row['i'], row['j']].ub = 0
            else:
                x[row['i'], row['j']].lb = 1
    if inst.params['INIT_SOL']:
        dfxres = pd.read_excel('results/' + inst.name + "_res.xlsx", sheet_name='x')
        for index, row in dfxres.iterrows():
            if row['x'] < 0.99:
                x[row['i'], row['j']].Start = 0
            else:
                x[row['i'], row['j']].Start = 1
    

    mm.setObjective(ZOB, GRB.MINIMIZE)
    mm.update()

    mm.addConstrs((gb.quicksum(x[i,j] for j in inst.Vs if j!=i) - gb.quicksum(U[i,t] for t in inst.T) == 0 for i in inst.V1  ), name='ct02.1')
    mm.addConstrs((gb.quicksum(x[j,i] for j in inst.Vp if j!=i) - gb.quicksum(U[i,t] for t in inst.T) == 0 for i in inst.V1  ), name='ct02.2')
    mm.addConstr( gb.quicksum(x[0,j] for j in inst.Vs)  == inst.m , name = 'ct03' )
    mm.addConstrs( (gb.quicksum(x[j,i] for j in inst.Vp) == 1 for i in range (inst.n+1, inst.n + inst.m + 1) ), name='ct04'  )

    mm.addConstrs((gb.quicksum(U[j,t] for t in inst.T) == 1 for j in inst.Vs), name = 'ct05')
    mm.addConstr(TBar[0] == 0, name='ct06')
    mm.addConstrs(( TBar[j] - TBar[i] - inst.t[i,j] + inst.Tmax * (1 - x[i,j]) >=0 for i in inst.Vp for j in inst.Vs if j != i ), name='ct07' )
    mm.addConstrs(( inst.etw[t] - inst.Tmax * (1 - U[j,t]) - TBar[j]  <= 0 for j in inst.Vs for t in inst.T), name = 'ct08.1')
    mm.addConstrs(( TBar[j]  - inst.ltw[t] - inst.Tmax * (1 - U[j,t]) <= 0 for j in inst.Vs for t in inst.T), name = 'ct08.2')

    mm.addConstrs((Q[0,s] == 0  for s in S), name = 'ct09')
    mm.addConstrs((Q[j,s] - Q[i,s] + inst.M * (1 - x[i,j]) - inst.d[j] - gb.quicksum( delta[j,tau,s] * U[j,t] for t in inst.T for tau in range(1, t+1 ))  >= 0
                   for s in S for i in inst.Vp for j in range(1, inst.n + 1) if j != i), name = 'ct10')
    mm.addConstrs((Q[j,s] - Q[i,s] - inst.M * (1 - x[i,j]) - inst.d[j] - gb.quicksum( delta[j,tau,s] * U[j,t] for t in inst.T for tau in range(1, t+1 ))  <= 0
                   for s in S for i in inst.Vp for j in range(1, inst.n + 1) if j != i), name = 'ct10_new')
    mm.addConstrs((Q[j,s] - Q[i,s] + inst.M * (1 - x[i,j]) >= 0 for s in S for i in inst.Vp for j in range(inst.n + 1, inst.n + inst.m + 1)), name = 'ct11')
    mm.addConstrs((Q[j,s] - Q[i,s] - inst.M * (1 - x[i,j]) <= 0 for s in S for i in inst.Vp for j in range(inst.n + 1, inst.n + inst.m + 1)), name = 'ct11_new')
    mm.addConstrs((R[j,s] - Q[j,s] + C >= 0 for s in S for j in range(inst.n + 1, inst.n + inst.m + 1)), name = 'ct12') 
    #mm.addConstrs((R[j,s]  >= 0 for s in inst.S for j in range(inst.n + 1, inst.n + inst.m + 1)), name = 'ct13') already considered in variable definition
    
    mm.addConstrs((L[j,s] - gb.quicksum( delta[j,tau,s] * U[j,t] for t in inst.T for tau in range(t+1, inst.LT + 1)) == 0 for s in S for j in inst.V1), name = 'ct14')

    if policy == 'P8' or policy == 'P12':
        f = {j : capResizeP5 if j%2 == 0 else -capResizeP5 for j in inst.V}
        mm.addConstrs((rho[j,s] - ((1/inst.Qmax)*(Q[j,s] - C*(1+f[j]))) >= 0 for s in S for j in inst.V1), name = 'ct15')
        mm.addConstrs((rho[j,s] + ((1/inst.Qmax)*(C*(1+f[j]) - Q[j,s] )) <= 1 for s in S for j in inst.V1), name = 'ct16')
    else:
        mm.addConstrs((rho[j,s] - ((1/inst.Qmax)*(Q[j,s] - C)) >= 0 for s in S for j in inst.V1), name = 'ct15')
        mm.addConstrs((rho[j,s] + ((1/inst.Qmax)*(C - Q[j,s] )) <= 1 for s in S for j in inst.V1), name = 'ct16') 

    #mm.addConstrs((rho[j,s] + inst.Qmax*R[j,s] >= 1 for s in inst.S for j in range(1, inst.n + 1)) , name = 'ct_rho_new')

    mm.addConstrs((y[i,j,s] - 0.5 * (x[i,j] + rho[i,s]) <= 0 for s in S for i in inst.V1 for j in inst.Vs if j != i), name = 'ct17')

    mm.addConstrs( (y[0,j,s] == 0 for s in S for j in inst.Vs), name='cty0')
    mm.addConstrs(( alpha[j,s] == gb.quicksum(y[j,i,s] for i in inst.Vs if j!=i) - gb.quicksum(y[i,j,s] for i in range(1, inst.n+1) if j!=i)  for s in S for j in range(1, inst.n + 1)), name = 'ctyalpha')

    if inst.params['VALID_INEQUALITIES']:
        mm.addConstr(  gb.quicksum(x[i,j] for i in inst.Vp for j in inst.Vs  if i != j  ) <= len(inst.V1) + inst.m, name="vi1.1" )
        mm.addConstr(  gb.quicksum(x[i,j] for i in inst.Vp for j in inst.Vs  if i != j ) >= len(inst.V1) , name="vi1.2" )
        mm.addConstrs( ( gb.quicksum( y[i,j,s] for i in inst.Vp for j in inst.Vs if j!=i ) -  gb.quicksum(rho[j,s] for j in range(1, inst.n + 1)  ) <= 0 for s in S), name="vi2" )
    
    """
    mm.addConstr(x[0,1]==1)
    mm.addConstr(x[1,2]==1)
    mm.addConstr(x[2,3]==1)
    mm.addConstr(x[3,4]==1)
    mm.addConstr(x[4,5]==1)
    mm.addConstr(x[5,11]==1)
    mm.addConstr(x[0,10]==1)
    mm.addConstr(x[10,9]==1)
    mm.addConstr(x[9,8]==1)
    mm.addConstr(x[8,7]==1)
    mm.addConstr(x[7,6]==1)
    mm.addConstr(x[6,12]==1)
    """
    
    mm.update()
    if (inst.params['WRITE_LP']):
        mm.write('results/model_'+inst.name+'.lp')

    mym.set(mm, x, U, TBar, y, Q, R, L, rho, lambd, alpha, ZOB1, ZOB2, ZOB3, ZOB4, ZOB5)
    return mym

def build_model_vrp(inst : Instance):
    mym = mymodel()
    mm = gb.Model('FSG')
    policy = inst.params['POLICY']
    capResize = 0.1
    capResizeP5 = 0.15
    if policy == 'P9' or policy == 'P10':
        capResize = 0.20
        capResizeP5 = 0.30

    d = {k:v for k,v in inst.d.items()}
    C = inst.C

    if policy == 'P1':
        pass
    if policy == 'P2' or policy == 'P4' or policy == 'P5' or policy == 'P6' or policy == 'P9' or policy == 'P10':
        #@DONE:
        # per ogni cliente sommare il delta sui timeslot.
        # prendere il valore atteso e non la media degli scenari

        for j in range(1, inst.n + 1):
            mean = 0
            for t in inst.T:
                mean += inst.delta_expected[j,t,1]
            d[j] = inst.d[j] + mean

    if policy == 'P3':
        NT = math.ceil(inst.LT/2)
        for j in range(1, inst.n + 1):
            mean = 0 
            for t in range(1, NT+1):
                mean += inst.delta_expected[j,t,1]
            #mean = mean/(LS*NT)
            d[j] = d[j] + mean
        
    if policy == 'P4' or policy == 'P9':
        C = C*(1-capResize)
    if policy == 'P5':
        pass
    if policy == 'P6':
        pass

    
    
    if inst.params['LOWER_BOUND']:
        #inst.p = 0
        #inst.delta ={k:0 for k in inst.delta}
        pass

    x = {(i,j) : mm.addVar(vtype = GRB.BINARY, name='x_{}_{}'.format(i,j)) for i in inst.Vp for j in inst.Vs if i != j }
    

    U = {(j,t) : mm.addVar(vtype = GRB.BINARY, name='U_{}_{}'.format(j,t)) for j in inst.Vs for t in inst.T}
    TBar = {i : mm.addVar(vtype = GRB.CONTINUOUS, lb = 0, name = 'TBar_{}'.format(i)) for i in inst.V}
    Q = {j : mm.addVar(vtype=  GRB.CONTINUOUS, lb = 0, name = 'Q_{}'.format(j)) for j in inst.V}
    mu = {j : mm.addVar(vtype = GRB.CONTINUOUS, lb=0, name='mu_{}'.format(j)) for j in inst.V}
    u = {}
    if policy == 'P6':
        u = {j : mm.addVar(vtype=GRB.INTEGER, lb=0, name = 'u_{}'.format(j)) for j in inst.V }
    
    # add a variable zero in order to get rid of no value for the z3,z4,z5 components of the obj f
    zero = mm.addVar(vtype=GRB.CONTINUOUS, name='zero')
    Z_Zero = 1*zero
    mm.addConstr(zero == 0, name='ctzero')
    


    mm.update()

    K = 1000000
    ZOB = None

    if policy == 'P6':
        ZOB = gb.quicksum((1/inst.t[0,j])*u[j] for j in inst.V1 )
    else:
        ZOB1 = gb.quicksum(inst.c[i,j] * x[i,j] for i in inst.Vp for j in inst.Vs if j != i) 
        ZOB2 = K * gb.quicksum(mu[j] for j in inst.V)
        ZOB = ZOB1  + ZOB2 

    # if LOWER_BOUND:
    #    for i in inst.Vp:
    #     for j in inst.Vs:
    #         for s in inst.S:
    #             if j!=i:
    #                 y[i,j,s].ub = 0


    mm.setObjective(ZOB, GRB.MINIMIZE)
    mm.update()

    mm.addConstrs((gb.quicksum(x[i,j] for j in inst.Vs if j!=i) - gb.quicksum(U[i,t] for t in inst.T) == 0 for i in inst.V1  ), name='ct02.1')
    mm.addConstrs((gb.quicksum(x[j,i] for j in inst.Vp if j!=i) - gb.quicksum(U[i,t] for t in inst.T) == 0 for i in inst.V1  ), name='ct02.2')
    mm.addConstr( gb.quicksum(x[0,j] for j in inst.Vs)  == inst.m , name = 'ct03' )
    mm.addConstrs( (gb.quicksum(x[j,i] for j in inst.Vp) == 1 for i in range (inst.n+1, inst.n + inst.m + 1) ), name='ct04'  )

    mm.addConstrs((gb.quicksum(U[j,t] for t in inst.T) == 1 for j in inst.Vs), name = 'ct05')
    mm.addConstr(TBar[0] == 0, name='ct06')
    mm.addConstrs(( TBar[j] - TBar[i] - inst.t[i,j] + inst.Tmax * (1 - x[i,j]) >=0 for i in inst.Vp for j in inst.Vs if j != i ), name='ct07' )
    mm.addConstrs(( inst.etw[t] - inst.Tmax * (1 - U[j,t]) - TBar[j]  <= 0 for j in inst.Vs for t in inst.T), name = 'ct08.1')
    mm.addConstrs(( TBar[j]  - inst.ltw[t] - inst.Tmax * (1 - U[j,t]) <= 0 for j in inst.Vs for t in inst.T), name = 'ct08.2')

    mm.addConstrs((Q[0] == 0  for s in inst.S), name = 'ct09')
    mm.addConstrs((Q[j] - Q[i] + inst.M * (1 - x[i,j]) - d[j]   >= 0   for i in inst.Vp for j in range(1, inst.n + 1) if j != i), name = 'ct10')
    #mm.addConstrs((Q[j] - Q[i] - inst.M * (1 - x[i,j]) - inst.d[j] for t in inst.T for tau in range(1, t+1 )  <= 0   for i in inst.Vp for j in range(1, inst.n + 1) if j != i), name = 'ct10_new')
    mm.addConstrs((Q[j] - Q[i] + inst.M * (1 - x[i,j]) >= 0 for i in inst.Vp for j in range(inst.n + 1, inst.n + inst.m + 1)), name = 'ct11')
    #mm.addConstrs((Q[j] - Q[i] - inst.M * (1 - x[i,j]) <= 0 for i in inst.Vp for j in range(inst.n + 1, inst.n + inst.m + 1)), name = 'ct11_new')
    
    if policy == 'P5' or policy == 'P10':
        f = {j : capResizeP5 if j%2 == 0 else -capResizeP5 for j in inst.V}
        mm.addConstrs((Q[j] <= C*(1 + f[j]) + mu[j] for j in inst.V), name = 'ctcap')
    else:
        mm.addConstrs((Q[j] <= C + mu[j] for j in inst.V), name = 'ctcap')
    
    if policy == 'P6':
        mm.addConstrs((u[j] - u[i] - 1 + (len(inst.Vp) - 1)*(1 - x[i,j]) >=0  for j in inst.Vs for i in inst.Vp if i != j), name = 'ctu')


    if inst.params['VALID_INEQUALITIES']:
        pass
 
    """
    mm.addConstr(x[0,1]==1)
    mm.addConstr(x[1,2]==1)
    mm.addConstr(x[2,3]==1)
    mm.addConstr(x[3,4]==1)
    mm.addConstr(x[4,5]==1)
    mm.addConstr(x[5,11]==1)
    mm.addConstr(x[0,10]==1)
    mm.addConstr(x[10,9]==1)
    mm.addConstr(x[9,8]==1)
    mm.addConstr(x[8,7]==1)
    mm.addConstr(x[7,6]==1)
    mm.addConstr(x[6,12]==1)
    """
    
    mm.update()
    if (inst.params['WRITE_LP']):
        mm.write('results/model_'+inst.name+'_'+ policy +'.lp')
    if policy != 'P6':
        mym.set(mm, x, U, TBar, None, Q, None, None, None, None, None, ZOB1, Z_Zero, Z_Zero, Z_Zero, Z_Zero)
    else:
        mym.set(mm, x, U, TBar, None, Q, None, None, None, None, None, ZOB, Z_Zero, Z_Zero, Z_Zero, Z_Zero)
    return mym

def run_model(inst : Instance, mym : mymodel):
    mm = mym.m
    mm.Params.TimeLimit = inst.params['max_runtime']
    #mm.Params.IntFeasTol = 1e-7
    mm.optimize()
    print('Optimization ended with status (2=optimal, 3=infeasible, 5=inf_or_unbounded, 9=timlimit, 11=interrupted)', mm.Status)

def run(pms : dict):
    inst = load_instance(pms)
    print ("loaded instance with ", inst.n, ' nodes' )
    print (inst.to_string())

    print("building model")
    mym = build_model(inst)

    print("run model")
    run_model(inst, mym)

    print("save solution to excel (if a solution has been found)")
    if mym.m.Status in [2,9,11]:
        print('object value: ', mym.m.ObjVal)
        print(mym.Z1.getValue())
        print(mym.Z2.getValue())
        print(mym.Z3.getValue())
        print(mym.Z4.getValue())
        print(mym.Z5.getValue())
        fsolname = 'results/out_'+inst.name
        fsolname += '_fix.sol' if inst.params['FIX_SOLUTION']==True  else '.sol'
        #mym.m.write(fsolname)
        mym.to_excel(inst)
    return mym


if __name__ == "__main__":

    #inst_names = ['I2_N7_T100_C140_0', 'I2_N7_T100_C210_0', 'I2_N7_T100_C280_0']
    #inst_names = ['I2_N10_T30_C250_0', 'I2_N10_T30_C275_0', 'I2_N10_T30_C325_0','I2_N10_T100_C275_0', 'I2_N10_T100_C325_0' ]
    # inst_names = ['I2_N7_T30_C280_0', 'I2_N7_T30_C210_0', 'I2_N7_T30_C140_0', 'I2_N7_T100_C280_0', 'I2_N7_T100_C210_0', 'I2_N7_T100_C140_0', 
    #                'I2_N5_T30_C200_0', 'I2_N5_T30_C150_0', 'I2_N5_T30_C100_0', 'I2_N5_T100_C200_0', 'I2_N5_T100_C150_0', 'I2_N5_T100_C100_0', 
    #                'I2_N10_T30_C400_0', 'I2_N10_T30_C350_0', 'I2_N10_T30_C325_0', 'I2_N10_T30_C300_0', 'I2_N10_T30_C275_0', 'I2_N10_T100_C400_0', 
    #                'I2_N10_T100_C350_0', 'I2_N10_T100_C325_0', 'I2_N10_T100_C300_0', 'I2_N10_T100_C275_0']
    # inst_names = ['I1_RTSL']
    # inst_names = ['I1_R2']
    # inst_names = ['I2_N7_T30_C100_0', 'I2_N7_T30_C120_0']
    # inst_names = ['I2_N7_T100_C100_0', 'I2_N7_T100_C120_0', 'I2_N7_T100_C120_0']
    # inst_names = ['I2_N10_T100_C400_0']
    counter = 0
    fp = open('params.json')
    pms = json.load(fp)

    instance_list_filename = 'instances_list_N8_filtered.xlsx'
    if pms['MODEL_TYPE'] == "BESTPOLICY":
        instance_list_filename = 'instances_list_548.xlsx' 
    dfi = pd.read_excel(instance_list_filename, index_col='name')
    inst_names = list(dfi.index)

    if pms['OVERWRITE_LOG']:
        if os.path.isfile('log_table.csv'):
            os.remove('log_table.csv')
        if os.path.isfile('log_table_policies.csv'):
            os.remove('log_table_policies.csv')
        if os.path.isfile('log_table_policies_p.csv'):
            os.remove('log_table_policies_p.csv')
    if not os.path.isfile('log_table_policies.csv'):
        with open('log_table_policies.csv', 'a') as mylog:
                        mylog.write('name,solved,type,objval,runtime,gap,Z1,Z2,Z3,Z4,Z5,SObjVal,SZ1,SZ2,SZ3,SZ4,SZ5\n')
    if not os.path.isfile('log_table_policies_p.csv'):
        with open('log_table_policies_p.csv', 'a') as mylog:
                        mylog.write('name,solved,type,objval,runtime_p,gap_p,Z1_p,Z2_p,Z3_p,Z4_p,Z5_p,FixObjVal,FixGAP,FixZ1,FixZ2,FixZ3,FixZ4,FixZ5\n')
    dfpolicies = pd.read_csv('log_table_policies.csv', index_col=['name', 'type'])
    for inst_name in inst_names: # ['I3_N5_M2_T15_C100_DepLowerLeft_s0']:  #'I2_S1_0_C100' inst_names
        if len(sys.argv) > 1:
            inst_name = sys.argv[1]
        print(f'*********************************SOLVING INSTANCE {inst_name}******************\n***************************************************')


        if pms['MODEL_TYPE'] == "POLICY" or pms['MODEL_TYPE'] == "BESTPOLICY":
            ssolved = dfi.loc[inst_name, 'solved']
            if not ssolved:
                with open('log_table_policies.csv', 'a') as mylog:
                    mylog.write(f'{inst_name},{ssolved},,,,,,,,,,,,,,,\n')
                    continue

            #policies = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']

            # P7 and P8 are based on P4, and P5 solved with EVV, 
            # P9 and P10 are based on P4 but with augmented percentage of capacity reduction
            # P11 and P12 are based on P9 and P10 but with EVV
            policies = ['P7', 'P8', 'P9', 'P10', 'P11', 'P12']
            if pms['MODEL_TYPE'] == "BESTPOLICY":
                # salta le istanze con gap > 0.0001
                if dfi.loc[inst_name, 'FILTRO'] == 0:
                    continue
                # considera solo la migliore policy
                policies = []
                p = dfi.loc[inst_name, 'bestpolicy']
                policies.append(p)
            pms['inst_name'] = inst_name
            pms['FIX_SOLUTION'] = False
            pms['INSTANCE_MEAN'] = False
            inst = load_instance(pms)
            print ("loaded instance with ", inst.n, ' nodes' )
            print (inst.to_string())

            
            for p in policies:

                ###
                # Run POLICY if not already in log_table_polices
                ###

                if (inst_name, p) in dfpolicies.index:
                    continue
                #dfpolicies.loc[name, 'P1']['solved']     
                
                print("###### Processing Instance named: ", inst_name, '   #############')
                print("######  POLICY:             ", p, '#################')
                print("building model")
                pms['POLICY'] = p
                mymp = build_model(inst)  # modello policy

                print(f"run model with policy {p}")
                run_model(inst, mymp)
                # take the x solution
                xfix = {(k[0],k[1]): v.X for k,v in mymp.x.items()}
                # set the stochastic model with fix x
                pms['POLICY'] = 'P0'
                pms['XFIX'] = xfix
                # build the stochastic model with P0 and x fix
                print("INNEST X SOLUTION OF " + p + " POLICY INTO STOCHASTIC MODEL AND SOLVE IT")
                mym = build_model(inst) # modello fixed
                print(f"run model with policy {p}")
                run_model(inst, mym)

                print("save solution to excel (if a solution has been found)")
                if mym.m.Status in [2,9,11]:
                    print('object value: ', mym.m.ObjVal)
                    print(mym.Z1.getValue())
                    print(mym.Z2.getValue())
                    print(mym.Z3.getValue())
                    print(mym.Z4.getValue())
                    print(mym.Z5.getValue())
                    #fsolname = 'results/out_'+inst.name
                    #fsolname += '_fix.sol' if inst.params['FIX_SOLUTION']==True  else '.sol'
                    #mym.m.write(fsolname)
                    # reset the current policy in order to write it to disk as filename
                    pms['POLICY'] = p
                    mym.to_excel(inst)

                    # save the solution of the best policy in the instance list
                    if pms['MODEL_TYPE'] == "BESTPOLICY":
                        dfi.loc[inst_name, 'policyvalue'] = mym.m.ObjVal

                    #
                    # WRITE AGGREGATED RESULT APPENDED ON INSTANCE LIST FILES
                    #
                    # name,solved,type,objval,runtime,gap,Z1,Z2,Z3,Z4,Z5,SObjVal,SZ1,SZ2,SZ3,SZ4,SZ5
                    row = f"{inst_name},{True},{p},{mym.m.ObjVal},{mym.m.Runtime},{mym.m.MIPGap},{mym.Z1.getValue()},{mym.Z2.getValue()},{mym.Z3.getValue()},{mym.Z4.getValue()},{mym.Z5.getValue()},{dfi.loc[inst_name, 'objVal']},{dfi.loc[inst_name,'Z1']},{dfi.loc[inst_name,'Z2']},{dfi.loc[inst_name,'Z3']},{dfi.loc[inst_name,'Z4']},{dfi.loc[inst_name,'Z5']}"
                    # name,solved,type,objval,runtime_p,gap_p,Z1_p,Z2_p,Z3_p,Z4_p,Z5_p,FixObjVal,FixGAP,FixZ1,FixZ2,FixZ3,FixZ4,FixZ5
                    rowp = f"{inst_name},{True},{p},{mymp.m.ObjVal},{mymp.m.Runtime},{mymp.m.MIPGap},{mymp.Z1.getValue()},{mymp.Z2.getValue()},{mymp.Z3.getValue()},{mymp.Z4.getValue()},{mymp.Z5.getValue()},{mym.m.ObjVal},{mym.m.MIPGap},{mym.Z1.getValue()},{mym.Z2.getValue()},{mym.Z3.getValue()},{mym.Z4.getValue()},{mym.Z5.getValue()}"

                    with open('log_table_policies.csv', 'a') as mylog:
                        mylog.write(row + '\n')
                    with open('log_table_policies_p.csv', 'a') as mylog:
                        mylog.write(rowp + '\n')

                # reset x solution in order to pass to the next policy
                pms['XFIX'] = {}
            # save the modified dataframe with the best policy values
            if pms['MODEL_TYPE'] == "BESTPOLICY":
                dfi.to_excel(instance_list_filename)

        
        else:
            ssolved = dfi.loc[inst_name, 'solved']
            if ssolved and not pms['OVERWRITE_LOG']:
                continue
            ###
            # Run stochastic model
            ###    

            pms['inst_name'] = inst_name
            pms['FIX_SOLUTION'] = False
            pms['INSTANCE_MEAN'] = False
            print("###### Processing Instance named: ", inst_name, '   #############')
            print("######  FIX SOLUTION:             ", pms['FIX_SOLUTION'], '#################')
            myms = run(pms)

            if myms.m.Status not in [2,9,11]:
                with open('log_table.csv', 'a') as mylog:
                    mylog.write(inst_name +',True,INFEASIBLE\n ')



            ###
            # Run average model
            ### 
            inst_name_mean = inst_name + '_mean'
            pms['inst_name'] = inst_name_mean
            pms['FIX_SOLUTION'] = False
            pms['INSTANCE_MEAN'] = True
            print("###### Processing Instance named: ", inst_name_mean, '   #############')
            print("######  FIX SOLUTION:             ", pms['FIX_SOLUTION'], '#################')
            myma = run(pms)

            ########
            # Run FIXED MODEL  (EEV)
            ########
            pms['inst_name'] = inst_name
            pms['FIX_SOLUTION'] = True
            pms['INSTANCE_MEAN'] = False
            print("###### Processing Instance named: ", inst_name, '   #############')
            print("######  FIX SOLUTION:             ", pms['FIX_SOLUTION'], '#################')
            if myma.m.Status in [2,9,11]:    
                mymf = run(pms)
            else:
                continue
            dfi.loc[inst_name, 'solved'] = True
            dfi.loc[inst_name, 'objVal'] = myms.m.ObjVal #
            dfi.loc[inst_name, 'runTime'] = myms.m.Runtime
            dfi.loc[inst_name,'gap']= myms.m.MIPGap
            dfi.loc[inst_name,'Z1'] =  myms.Z1.getValue()
            dfi.loc[inst_name,'Z2'] =  myms.Z2.getValue()
            dfi.loc[inst_name,'Z3'] =  myms.Z3.getValue()
            dfi.loc[inst_name,'Z4'] =  myms.Z4.getValue()
            dfi.loc[inst_name,'Z5'] =  myms.Z5.getValue()
            dfi.loc[inst_name,'EVV']=  mymf.m.ObjVal
            dfi.loc[inst_name,'EVVgap']=  mymf.m.MIPGap
            dfi.loc[inst_name,'EVVrunTime']=  mymf.m.Runtime
            dfi.loc[inst_name,'EZ1'] =  mymf.Z1.getValue()
            dfi.loc[inst_name,'EZ2'] =  mymf.Z2.getValue()
            dfi.loc[inst_name,'EZ3'] =  mymf.Z3.getValue()
            dfi.loc[inst_name,'EZ4'] =  mymf.Z4.getValue()
            dfi.loc[inst_name,'EZ5'] =  mymf.Z5.getValue()
            dfi.loc[inst_name,'VSS']=  100*((mymf.m.ObjVal - myms.m.ObjVal)/myms.m.ObjVal)

            dfi.to_excel(instance_list_filename)
            with open('log_table.csv', 'a') as mylog:
                mylog.write(inst_name +',')
                for c in dfi.columns:
                    mylog.write(str(dfi.loc[inst_name][c]))
                    mylog.write(',')
                mylog.write('\n')
    
    


