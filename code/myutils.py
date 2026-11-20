import pandas as pd
import math
import json
import gurobipy as gb

class node:
    def __init__(self, i, x, y):
        self.i = i
        self.x = x
        self.y = y

def get_distance(i: node, j: node):
    return math.dist([i.x, i.y], [j.x, j.y])


class Instance:
    def __init__(self):
        self.name = 'myname'
        self.params = {}
        self.n = 1
        self.nodes = {} 
        self.LT = 1
        self.T = [1]
        self.m = 4
        self.LS = 1
        self.S = [1]
        self.C = 10
        self.p = 10
        self.st = {} # service time in minutes
        self.Tmax = 10e6
        self.Qmax = 10e6
        self.M = 10e6
        self.e = {}# (i,j) : distance or cost
        self.c = {} 
        self.t = {}
        self.etw = {} # t:e
        self.ltw = {} # t:l
        self.d = {} # i:d
        self.delta = {} # (j,t,s):delta
        self.delta_expected = {} # (j,t,1):delta_expected
        self.V = set()
        self.Vp = set()
        self.Vs = set()
        self.V1 = set()

    def fill_edges(self):
        for i in self.nodes.values():
            for j in self.nodes.values():
                dist = get_distance(i,j)
                self.c[i.i, j.i] = dist * self.params['D2C']
                self.t[i.i, j.i] = dist * self.params['D2T'] + self.st[j.i]
                self.e[i.i, j.i] = dist 


    def fillV(self):
        self.V = set(i for i in range(self.n+self.m+1))
        self.V1 = set(i for i in range(1, self.n + 1))
        self.Vp = set.difference(self.V, set(i for i in range(self.n+1, self.n+self.m+1))) #V'   {0, ... n}
        self.Vs =  set.difference(self.V, {0})                                             # V'' {1, ... n, n+1,,n+m}
        return
    
    def expandNetwork(self):
        # add edges 0->i for i in [n+1,m] with cost and time equal to 0
        ext_e = {}
        ext_c = {}
        ext_t = {}
        for i in range(self.n+1, self.n + self.m + 1):
            ext_e[0,i] = 0
            ext_c[0,i] = 0
            ext_t[0,i] = 0
        # add edge (i,j) for each i in {1,n} j in {n+1, n+m} add e[i,j] con costo c[e[i,j]]= c[i,0]
        for j in range(self.n +1, self.m  + self.n + 1):
            for i in range(1, self.n+1):
                ext_e[i,j] = self.e[i,0] 
                ext_c[i,j] = self.c[i,0] 
                ext_t[i,j] = self.t[i,0]  
        self.e.update(ext_e)
        self.c.update(ext_c)
        self.t.update(ext_t)
        return

    def to_string(self):
        s = ""
        s += 'name: ' + str(self.name ) + '\n'
        s += 'n: ' + str(self.n ) + '\n'
        s += 'LT: ' + str(self.LT) + '\n'
        s += 'T: ' + str(self.T) + '\n'
        s += 'm: ' + str(self.m) + '\n'
        s += 'LS: ' + str(self.LS) + '\n'
        s += 'S: ' + str(self.S) + '\n'
        s += 'C: ' + str(self.C) + '\n'
        s += 'p: ' + str(self.p) + '\n'
        s += 'Tmax: ' + str(self.Tmax) + '\n'
        s += 'Qmax: ' + str(self.Qmax) + '\n'
        s += 'M: ' + str(self.M) + '\n'
        #s += 'e: ' + str(self.e) + '\n'
        s += 'etw: ' + str(self.etw) + '\n'
        s += 'ltw: ' + str(self.ltw) + '\n'
        s += 'd: ' + str(self.d) + '\n'
        #s += 'delta: ' + str(self.delta)  + '\n'
        s += 'V: ' + str(self.V)  + '\n'
        s += 'Vp: ' + str(self.Vp)  + '\n'
        s += 'Vs: ' + str(self.Vs)  + '\n'
        s += 'V1: ' + str(self.V1)  + '\n'

        return s

class mymodel:
    def __init__(self):
        self.m : gb.Model = None
        self.x = {}
        self.U = {}
        self.TBar = {}
        self.y = {}
        self.Q = {}
        self.R = {}
        self.L = {}
        self.rho = {}
        self.lambd = {}
        self.alpha = {}
        self.Z1 = None
        self.Z2 = None
        self.Z3 = None
        self.Z4 = None
        self.Z5 = None
    def set(self, m, x, U, TBar, y, Q, R, L, rho, lambd, alpha, Z1, Z2, Z3, Z4, Z5):
        self.m = m
        self.x = x
        self.U = U
        self.TBar =TBar
        self.y = y
        self.Q = Q
        self.R = R
        self.L = L
        self.rho = rho
        self.lambd = lambd
        self.alpha = alpha
        self.Z1 = Z1
        self.Z2 = Z2
        self.Z3 = Z3
        self.Z4 = Z4
        self.Z5 = Z5

    def to_excel(self, inst: Instance):
        policy = inst.params['POLICY']
        if policy == 'P0':
            filename = 'results/' + inst.name + "_res" 
        else: 
            filename = 'results/' + inst.name + "_" + policy + "_res"
        filename += '_fix.xlsx' if inst.params['FIX_SOLUTION']==True  else '.xlsx'
        filename = filename[0:-5] +'_lb.xlsx' if  inst.params['LOWER_BOUND']==True  else filename[0:-5] +'.xlsx'
        # create a excel writer object
        df_gen = pd.DataFrame(columns=['param', 'value'])
        df_gen.loc[len(df_gen)] = ['Inst name', inst.name]
        df_gen.loc[len(df_gen)] = ['objValue', self.m.ObjVal]
        df_gen.loc[len(df_gen)] = ['runtime', self.m.Runtime]
        df_gen.loc[len(df_gen)] = ['gap', self.m.MIPGap]
        df_gen.loc[len(df_gen)] = ['Z1', self.Z1.getValue()]
        df_gen.loc[len(df_gen)] = ['Z2', self.Z2.getValue()]
        df_gen.loc[len(df_gen)] = ['Z3', self.Z3.getValue()]
        df_gen.loc[len(df_gen)] = ['Z4', self.Z4.getValue()]
        df_gen.loc[len(df_gen)] = ['Z5', self.Z5.getValue()]

        df_x = pd.DataFrame()
        df_x['i'] = [k[0] for k in self.x.keys() ]
        df_x['j'] = [k[1] for k in self.x.keys() ]
        df_x['x'] = [v.X for v in self.x.values() ]
        df_x = df_x[df_x['x'] > 1e-4]

        df_U = pd.DataFrame()
        df_U['j'] = [k[0] for k in self.U.keys() ]
        df_U['t'] = [k[1] for k in self.U.keys() ]
        df_U['U'] = [v.X for v in self.U.values() ]
        df_U = df_U[df_U['U'] > 1e-4]

        df_TBar = pd.DataFrame()
        df_TBar['i'] = [k for k in self.TBar.keys() ]
        df_TBar['TBar'] = [v.X for v in self.TBar.values() ]

        df_y = pd.DataFrame()
        df_y['i'] = [k[0] for k in self.y.keys() ]
        df_y['j'] = [k[1] for k in self.y.keys() ]
        df_y['s'] = [k[2] for k in self.y.keys() ]
        df_y['y'] = [v.X for v in self.y.values() ]
        df_y = df_y[df_y['y'] > 1e-4]

        df_Q = pd.DataFrame()
        df_Q['j'] = [k[0] for k in self.Q.keys() ]
        df_Q['s'] = [k[1] for k in self.Q.keys() ]
        df_Q['Q'] = [v.X for v in self.Q.values() ]

        df_R = pd.DataFrame()
        df_R['j'] = [k[0] for k in self.R.keys() ]
        df_R['s'] = [k[1] for k in self.R.keys() ]
        df_R['R'] = [v.X for v in self.R.values() ]
 
        df_L = pd.DataFrame()
        df_L['j'] = [k[0] for k in self.L.keys() ]
        df_L['s'] = [k[1] for k in self.L.keys() ]
        df_L['L'] = [v.X for v in self.L.values() ]

        df_rho = pd.DataFrame()
        df_rho['j'] = [k[0] for k in self.rho.keys() ]
        df_rho['s'] = [k[1] for k in self.rho.keys() ]
        df_rho['rho'] = [v.X for v in self.rho.values() ]
        df_rho = df_rho[df_rho['rho'] > 1e-4]

        #df_lambd = pd.DataFrame()
        #df_lambd['j'] = [k[0] for k in self.lambd.keys() ]
        #df_lambd['s'] = [k[1] for k in self.lambd.keys() ]
        #df_lambd['lambda'] = [v.X for v in self.lambd.values() ]

        df_alpha = pd.DataFrame()
        df_alpha['j'] = [k[0] for k in self.alpha.keys() ]
        df_alpha['s'] = [k[1] for k in self.alpha.keys() ]
        df_alpha['alpha'] = [v.X for v in self.alpha.values() ]
        df_alpha = df_alpha[df_alpha['alpha'] > 1e-4]

        with pd.ExcelWriter(filename) as writer:
            df_gen.to_excel(writer, sheet_name="general", index=False)
            df_x.to_excel(writer, sheet_name="x", index=False)
            df_U.to_excel(writer, sheet_name="U", index=False)
            df_TBar.to_excel(writer, sheet_name="TBar", index=False)
            df_y.to_excel(writer, sheet_name="y", index=False)
            df_Q.to_excel(writer, sheet_name="Q", index=False)
            df_R.to_excel(writer, sheet_name="R", index=False)
            df_L.to_excel(writer, sheet_name="L", index=False)
            df_rho.to_excel(writer, sheet_name="rho", index=False)
            #df_lambd.to_excel(writer, sheet_name="lambda", index=False)
            df_alpha.to_excel(writer, sheet_name="alpha", index=False)     

def toJson(mym : mymodel, inst : Instance):
    sol = {}
    #jsol = json.load(sol)
    filename = 'results/' + inst.name + '.json'
    with open (filename, 'w') as jsf:
        json.dump(sol, jsf, indent=4)

    return sol

def load_instance( params : dict):
    inst_name = params['inst_name']
    filename = 'instances/'+inst_name+'.xlsx'

    #this will load instances
    dfp = pd.read_excel(filename, sheet_name='params', index_col='param')
    dfn = pd.read_excel(filename, sheet_name='nodes', index_col='i')
    dfe = pd.read_excel(filename, sheet_name='edges', dtype={'i':int, 'j':int, 'c':float, 't':float})
    dftw = pd.read_excel(filename, sheet_name='time_windows')
    dfd = pd.read_excel(filename, sheet_name='demand')
    dfdelta = pd.read_excel(filename, sheet_name='delta')
    df_delta_expected = pd.read_excel(filename, sheet_name='delta_expected')
    if params['INSTANCE_MEAN']:
        dfdelta = df_delta_expected.copy()

    # if not params['INSTANCE_MEAN']:
    #     df_delta_expected = pd.read_excel(filename, sheet_name='delta_expected')
    # else:
    #     df_delta_expected = dfdelta.copy()
       
    inst = Instance()
    inst.params = params
    inst.name = inst_name
    #inst.name = dfp.loc['name','value']
    inst.n = dfp.loc['n','value']
    inst.LT = dfp.loc['LT','value']
    inst.T = [t for t in range(1, inst.LT+1)]
    inst.m = dfp.loc['m','value']
    inst.LS = dfp.loc['LS','value']
    if params['INSTANCE_MEAN']:
        inst.LS = 1
    inst.S = [s for s in range(1, inst.LS + 1)]
    inst.C = dfp.loc['C','value']
    inst.p = dfp.loc['p','value']
    inst.Tmax = dfp.loc['Tmax','value']
    inst.Qmax = dfp.loc['Qmax','value']
    inst.M = dfp.loc['M','value']


    for index, row in dfn.iterrows():
            inst.nodes[ index ] = node(index, row["x"], row["y"])
            try:
                inst.st[index] = row['service_time']
            except KeyError  as e:
                inst.st[index] = 0

    if not inst.params['LOAD_EDGES']:
        inst.fill_edges() 
    if inst.params['LOAD_EDGES']:
        for index, row in dfe.iterrows():
            inst.e[ (row["i"], row["j"]) ] = row["d"]
            inst.c[ (row["i"], row["j"]) ] = row["c"]
            inst.t[ (row["i"], row["j"]) ] = row["t"] + inst.st[row['i']] #TODO check if use j and not i

    for index, row in dftw.iterrows():
        inst.etw[ row['t']] =  row['e']
        inst.ltw[ row['t']] =  row['l']
    
    for index, row in dfd.iterrows():
        inst.d[ row['j']] =  row['d']

    for index, row in dfdelta.iterrows():
        inst.delta[ (row['j'], row['t'], row['s']) ] = row['delta']
    
    for index, row in df_delta_expected.iterrows():
        inst.delta_expected[ (row['j'], row['t'], row['s']) ] = row['delta']

    inst.fillV()
    inst.expandNetwork()
    if inst.params['WRITE_EDGES']:
        df = pd.DataFrame(columns = ['i', 'j', 'c','t'])
        df['i'] = [k[0] for k, v in inst.e.items()]
        df['j'] = [k[1] for k, v in inst.e.items()]
        df['c'] = [v for k, v in inst.c.items()]
        df['t'] = [v for k, v in inst.t.items()] 
        df.to_excel(filename[0:-4] + '_edges.xlsx', sheet_name='edges', index=None)

    return inst
