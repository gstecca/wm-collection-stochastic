import pandas as pd
import statistics as stats
import numpy as np

instances_list = "instances_list_N8_filtered.xlsx"
RUNTYPE='analysis' # 'analysis' or 'aggregate'

def aggregate():
    df = pd.read_excel(instances_list, index_col='name')

    #df_pol = pd.read_csv('log_table_policies.csv')
    df_polp = pd.read_csv('log_table_policies_p.csv',index_col='name')  


    #log_table_policies.csv -> fixed vs stocastico
    #log_table_policies_p.csv > policy vs fixed

    policies = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10', 'P11', 'P12']

    df_agg_policies = pd.DataFrame(columns=['name', 'P1', 'FixP1',  'P2', 'FixP2', 'P3', 'FixP3', 'P4', 'FixP4', 'P5', 'FixP5', 'P6', 'FixP6', 
                                                    'P7', 'FixP7',  'P8', 'FixP8', 'P9', 'FixP9', 'P10', 'FixP10', 'P11', 'FixP11', 'P12', 'FixP12', 
                                            'objValSt', 'EVV', 'VSS'])

    for id, row in df.iterrows():
        print(id)
        row_aggregated = [id]
        objValStoc = row['objVal']
        evv = row['EVV']
        vss = row['VSS']
        for p in policies:
            print(p)
            objVal_policy = df_polp.loc[(df_polp['type'] == p) & (df_polp.index == id), 'objval'].values[0]
            objVal_fix = df_polp.loc[(df_polp['type'] == p) & (df_polp.index == id), 'FixObjVal'].values[0]
            row_aggregated.append(float(f"{objVal_policy:.3f}"))
            row_aggregated.append(float(f"{objVal_fix:.3f}"))

        row_aggregated.append(float(f"{objValStoc:.3f}"))
        row_aggregated.append(float(f"{evv:.3f}"))
        row_aggregated.append(float(f"{vss:.2f}"))
        df_agg_policies.loc[len(df_agg_policies)] = row_aggregated
    df_agg_policies.to_csv(instances_list +'_agg_policies.csv', index=False)
    df_agg_policies.to_excel(instances_list +'_agg_policies.xlsx', index=False)

def make_table_analysis_policies():
    policies = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10', 'P11', 'P12']
    df = pd.read_excel(instances_list + '_agg_policies.xlsx', index_col='name')
    dftable = pd.DataFrame(columns= policies , 
                           index=['meanGapEVV', 'stdevGapEVV', 'nbest', 'nbestEVV'
                                  , 'meanGapST', 'stdevGapST'])
    #+ ['EVV', 'VSS']
    nbests = {p: 0 for p in policies}
    nbestsEVV = {p: 0 for p in policies}
    for index, row in df.iterrows():
        for p in policies:
            count = 0
            for pp in policies:
                if pp==p:
                    continue
                if row[f"Fix{p}"] <= row[f"Fix{pp}"]:
                    count += 1
            if count == len(policies)-1:
                nbests[p] = nbests.get(p, 0) + 1
            if row[f"Fix{p}"] <= row['EVV']:
                nbestsEVV[p] = nbestsEVV.get(p, 0) + 1
    for p in policies:
        print(p)
        meanGapEVV = ((df[f"Fix{p}"] - df['EVV'])/df['EVV']).mean()
        stdevGapEVV = ((df[f"Fix{p}"] - df['EVV'] )/df['EVV']).std()
        meanGapST = ((df[f"Fix{p}"] - df['objValSt'] )/df['objValSt']).mean()
        stdevGapST = ((df[f"Fix{p}"] - df['objValSt'] )/df['objValSt']).std()
        dftable.loc['meanGapEVV', p] = meanGapEVV
        dftable.loc['stdevGapEVV', p] = stdevGapEVV
        dftable.loc['nbest', p] = nbests[p]
        dftable.loc['nbestEVV', p] = nbestsEVV[p]
        dftable.loc['meanGapST', p] = meanGapST
        dftable.loc['stdevGapST', p] = stdevGapST
    dftable.to_excel(instances_list + '_agg_policies_analysis.xlsx')





if __name__ == '__main__':
    if RUNTYPE == 'analysis':
        make_table_analysis_policies()
    if RUNTYPE == 'aggregate':
        aggregate()



