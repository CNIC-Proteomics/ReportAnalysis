# -*- coding: utf-8 -*-

#
# Import Modules
#

import argparse
import logging
import numpy as np
import os
import pandas as pd
import openpyxl
import sys
import yaml
import re

import itertools

from scipy.stats import hypergeom

import multiprocessing


idx = pd.IndexSlice
#
# Local Functions
#

from BinomialSiteListMaker import main as BSLM

def getColumnNames(config, contrast, significance_value):
    return [tuple(i) for i in [
        config['pdmCol'], 
        config['qCol'],
        config['qDescCol'], 
        config['pdmFreq'],
        config['qFreq'], 
        [f"{config['sign'][0]}_{contrast}", config['sign'][1]], 
        [f"{config['signNM'][0]}_{contrast}", config['signNM'][1]],
        [f"{config['qvalue_dNM']}_{contrast}", significance_value],
        [f"{config['qvalue_NM']}_{contrast}", significance_value],
        ]
    ]

def getRepQFColumnNames(config, contrast, significance_value):
    return [ tuple(i) for i in [
        config['pCol'],
        config['qcCol'],
        config['qCol'],
        config['pFreq'],
        config['qcFreq'],
        [f"{config['qvalue_p']}_{contrast}", significance_value],
        [f"{config['qvalue_qc']}_{contrast}", significance_value],
        [f"{config['sign_p'][0]}_{contrast}", config['sign_p'][1]],
        [f"{config['sign_qc'][0]}_{contrast}", config['sign_qc'][1]],
        config['missing_cleavages']
        ]
    ]

def getRepQF(rep0, config, contrast, significance_value):
    
    pCol, qcCol, qCol, pFreq, qcFreq, FDRp, FDRqc, sign_p, sign_qc, mcCol = getRepQFColumnNames(config, contrast, significance_value)
    
    repQF = {
        'PSMs': {},
        'Peptides': {}
        }
    
    for i, iCol, iFreq, FDRi, sign_i in [('p', pCol, pFreq, FDRp, sign_p), ('qc', qcCol, qcFreq, FDRqc, sign_qc)]:
        if not all([j in rep0.columns for j in [iCol, iFreq, FDRi]]):
            repQF['PSMs'][i]=None
            repQF['Peptides'][i]=None
            continue
        
        if i == 'p':
            iRep = rep0.loc[:, [qCol, iCol, iFreq, FDRi, sign_i, mcCol]].drop_duplicates().copy()#.dropna()
        elif i == 'qc':
            iRep = rep0.loc[:, [qCol, iCol, iFreq, FDRi, sign_i]].drop_duplicates().copy()#.dropna()
            
        repQF['PSMs'][i] = iRep.copy()
        repQF['Peptides'][i] = iRep.copy()
        repQF['Peptides'][i][iFreq] = [ 0 if j==0 else 1 for j in repQF['Peptides'][i][iFreq]]
    
    repQF['PSMs']['DT'] = repQF['PSMs']['p'][repQF['PSMs']['p'][mcCol]==0]
    repQF['Peptides']['DT'] = repQF['Peptides']['p'][repQF['Peptides']['p'][mcCol]==0]
    repQF['PSMs']['DP'] = repQF['PSMs']['p'][repQF['PSMs']['p'][mcCol]>0]
    repQF['Peptides']['DP'] = repQF['Peptides']['p'][repQF['Peptides']['p'][mcCol]>0]
    
    return repQF

    

def generateFreqTable(config, sign_i, fdr_i, rep, contrast, significance_value):
    '''
    Parameters
    ----------
    sign_i : TYPE
        DESCRIPTION.
    fdr_i : TYPE
        DESCRIPTION.

    Returns
    -------
    ptm : TYPE
        DESCRIPTION.
    '''
    pdmCol, qCol, qdCol, pdmFreq, qFreq, sign, signNM, FDRdNM, FDRNM = getColumnNames(config, contrast, significance_value)
    
    boolean = np.logical_and.reduce([
        rep[FDRdNM] < fdr_i,
        rep[sign] > 0 if sign_i == 'up' else rep[sign] < 0,
        ])
    
    rep_i = rep[boolean]
    
    rep_i = rep_i[[
        pdmCol, pdmFreq,tuple(config['pCol']),tuple(config['gCol']), tuple(config['aCol']), tuple(config['mCol'])
        ]].droplevel(1, axis=1)
    
    # If no pdm is filtered return empty list
    if rep_i.shape[0] == 0:
        return []
    
    
    bi, biPivot = BSLM({
        'infile': rep_i,
        'outfile': None,
        'peptidoform_column': pdmCol[0],
        'peptide_column': config['pCol'][0],
        'modifcation_column': config['gCol'][0],
        'modified_residue_column': config['aCol'][0],
        'modified_position_column': config['mCol'][0],
        'show_unassigned': False,
        'x': config['x'],
        'peakorph_column': None,
        'scanfreq_column': pdmFreq[0],
        'binom': config['binom'],
        'q_thr': config['q_thr'],
        'values_pivot': config['values_pivot']
        })

    
    outFolder = os.path.join(args.outdir, 'FreqTables', contrast, f"{significance_value}-{fdr_i}")
    if not os.path.exists(outFolder):
        os.makedirs(outFolder, exist_ok=True)
    
    with pd.ExcelWriter(os.path.join(outFolder, f'freqTable_{sign_i}_{fdr_i}.xlsx')) as writer:
        bi.to_excel(writer, sheet_name='Raw', index=False)
        biPivot.to_excel(writer, sheet_name=f'PIVOT-{config["binom"]}-{config["q_thr"]}-{config["values_pivot"]}')
    
    ptm = bi[bi[config['binom']]<config['q_thr']]
    ptm = ptm.rename(columns={config['aCol'][0]:'a', config['gCol'][0]:'d'})
    ptm = list(zip(ptm.a, ptm.d))
    return ptm



def qReportPivot(config, fdr_i, sign_i, rep, ptmCol, contrast, significance_value):
    '''

    Parameters
    ----------
    fdr_i : TYPE
        DESCRIPTION.
    sign_i : TYPE
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.

    '''
    
    pdmCol, qCol, qdCol, pdmFreq, qFreq, sign, signNM, FDRdNM, FDRNM = getColumnNames(config, contrast, significance_value)
    
    # Generate PTM Freq Table
    biptm = generateFreqTable(config, sign_i, fdr_i, rep, contrast, significance_value)
    
    repD = rep[np.logical_and.reduce([
        rep[FDRdNM] < fdr_i,
        rep[sign] > 0 if sign_i == 'up' else rep[sign] < 0,
        np.isin(rep[ptmCol], pd.Series(biptm, dtype='object')),
        ])].sort_values([qCol])
    
    if repD.shape[0] == 0:
        logging.info(f'No PTMs found at FDR = {fdr_i} and Sign = {sign_i}')
        return None
    
    qTableD = pd.pivot_table(
        repD,
        index=[qCol, pdmCol],
        columns=[ptmCol],
        values=[pdmFreq])\
        .droplevel(1, axis=1).fillna(0)
        
    qTableD = {
        'PSMs': qTableD,
        'Peptides': qTableD.map(lambda x: 0 if x==0 else 1)
        }
    
    return qTableD
        

def qReportAddData(config, fdr_i, sign_i, quan, qTableD, repNM, repPQF, rep, contrast, significance_value):
    '''
    
    Parameters
    ----------
    fdr_i : TYPE
        DESCRIPTION.
    sign_i : TYPE
        DESCRIPTION.
    quan : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    '''
    
    pdmCol, qCol, qdCol, pdmFreq, qFreq, sign, signNM, FDRdNM, FDRNM = getColumnNames(config, contrast, significance_value)
    pCol, qcCol, qCol, pFreq, qcFreq, FDRp, FDRqc, sign_p, sign_qc, mcCol = getRepQFColumnNames(config, contrast, significance_value)
    
    # Collapse PTMs of the same protein
    qTableD = qTableD.reset_index().drop(pdmCol, axis=1).groupby([qCol]).agg("sum")
    
    # Add missing proteins
    missQ = rep[qCol].drop_duplicates()
    missQ = missQ[~np.isin(missQ, qTableD.index)]
    qTableD = pd.concat([
        qTableD,
        pd.DataFrame(None, index=missQ, columns=qTableD.columns).fillna(0)        
        ]).copy()
    
    # Get all PTMs inside each protein 
    qTableD[(quan, 'PTMs')] = qTableD.sum(axis=1)
        
    # Add qFreq and qDesc
    qTableD = qTableD.join(
        rep[[qCol, qFreq, qdCol]]\
            .drop_duplicates().set_index(qCol),
        how='left'
        )
        
    # Add NM freq considering all pdm
    qTableD = qTableD.join(
        repNM[[qCol, pdmFreq]].groupby(qCol).agg("sum").fillna(0)\
            .rename(columns={pdmFreq[0]: quan, pdmFreq[1]: 'NM'}),
        how='left'
        )
    
    # Add NM freq of significative pdm changing in the opposite direction
    qTableD = qTableD.join(
        repNM.loc[
            np.logical_and.reduce([
                repNM[signNM]<0 if sign_i=='up' else repNM[signNM]>0,
                repNM[FDRNM]<fdr_i
                ]),
            [qCol, pdmFreq]
            ].groupby(qCol).agg("sum")\
            .rename(columns={pdmFreq[0]: quan, pdmFreq[1]: 'NMsig'}),
        how='left'
        ).fillna(0)
        
    #for i, iFreq, FDRi in [('p', pFreq, FDRp), ('qc', qcFreq, FDRqc)]:
    for i, iFreq, FDRi, sign_ii in [
            ('DT', pFreq, FDRp, sign_p), 
            ('DP', pFreq, FDRp, sign_p), 
            ('qc', qcFreq, FDRqc, sign_qc)
            ]:
        
        if type(repPQF[i]) == type(None): continue
    
        iRep = repPQF[i].loc[:, [qCol, iFreq, FDRi, sign_ii]]
        qTableD = qTableD.join(
            iRep.loc[:, [qCol, iFreq]].groupby(qCol).agg('sum')\
                .rename(columns={iFreq[0]:quan, iFreq[1]:i}),
            how='left'
            )
        
        qTableD = qTableD.join(
        iRep.loc[
            np.logical_and.reduce([
                iRep[FDRi]<fdr_i,
                iRep[sign_ii]>0 if sign_i=='up' else iRep[sign_ii]<0,
            ]), 
            [qCol, iFreq]
        ].groupby(qCol).agg('sum')\
        .rename(columns={iFreq[0]: quan, iFreq[1]: i+'sig'}),
        how='left'
        )


    def getHypergeom(qTableD, c1, c2):
        qTableD[('Hypergeom', c1+'based')] = [
        1-hypergeom.cdf(
            x-1, # x
            qTableD[(quan,c1)].sum(), # M overall population
            qTableD[(quan,c2)].sum(), # n Defect population
            N # N test population
        )
        for x,N in zip(qTableD[(quan,c2)], qTableD[(quan,c1)])
        ]
        return qTableD
        
    #for c1, c2 in [('NM', 'NMsig'), ('p', 'psig'), ('qc', 'qcsig')]:
    for c1, c2 in [('NM', 'NMsig'), ('DT', 'DTsig'), ('DP', 'DPsig'), ('qc', 'qcsig')]:
        qTableD = getHypergeom(qTableD, c1, c2)
        

    qTableD[('Hypergeom', 'PTMbased')] = [
        1-hypergeom.cdf(
            x-1, # x
            qTableD[qFreq].sum()-qTableD[(quan,'NM')].sum(), # M overall population
            qTableD[(quan, 'PTMs')].sum(), # n Defect population
            N # N test population
        ) 
        for x,N in zip(
                qTableD[(quan, 'PTMs')], 
                qTableD[qFreq]-qTableD[(quan,'NM')]
                )
        ]
    
    return qTableD


def qReportDesign(config, quan, qTableD, contrast, significance_value):
    '''
    Parameters
    ----------
    config : TYPE
        DESCRIPTION.
    qTableD : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    '''
    
    pdmCol, qCol, qdCol, pdmFreq, qFreq, sign, signNM, FDRdNM, FDRNM = getColumnNames(config, contrast, significance_value)
    
    # Sort columns
    infoCols = [qdCol,qFreq,(quan,'NM'),(quan,'NMsig'),(quan,'DT'),(quan,'DTsig'),(quan,'DP'),(quan,'DPsig'),(quan,'qc'),(quan,'qcsig'),\
                ('Hypergeom','NMbased'),('Hypergeom','DTbased'),('Hypergeom','DPbased'),('Hypergeom','qcbased'),('Hypergeom','PTMbased'), (quan, 'PTMs')]
    infoCols = [i for i in infoCols if i in qTableD.columns]
    i = qTableD.loc[:, infoCols]
    qTableD = i.join(qTableD.loc[:, [pdmFreq[0]]].replace(0, np.nan)).sort_values((quan, 'PTMs'), ascending=False)


    # Add summ row
    sumRow = []
    for column in qTableD.columns:
        if qTableD[column].dtype == 'object':
            sumRow.append('')
            continue
        elif column[0] == 'Hypergeom':
            sumRow.append(np.nan)
            continue
        else:
            sumRow.append(qTableD[column].sum())
            continue

    qTableD = pd.concat([
        pd.DataFrame([sumRow], columns=qTableD.columns, index=['Sum']),
        qTableD
        ])

    # Sort PTMs by total number
    qTableD = qTableD[infoCols].join(
        qTableD[    
            qTableD.loc['Sum', [pdmFreq[0]]].sort_values(ascending=False).index
        ]
    ).reset_index(names=[qCol])

    alphabet = pd.Series([j[0] for i,j in qTableD.columns if i == pdmFreq[0]]).drop_duplicates().values.tolist()
    ptmSort = [(i, j) for i,j in qTableD.columns if i == pdmFreq[0]]
    ptmSort = sorted(ptmSort, key=lambda col: alphabet.index(col[1][0]))
    ptmSort = [(i,j) for i,j in qTableD.columns if i!=pdmFreq[0]]+ptmSort
    qTableD = qTableD[ptmSort]
    
    
    qTableD.columns = pd.MultiIndex.from_tuples([
        (quan,j[0], j[1]) if i==pdmFreq[0] else (i,j,'') 
        for i,j in qTableD.columns
        ])
    
    # Add info contained in q2info
    if args.q2info and os.path.isfile(args.q2info):
        q2info = pd.read_csv(args.q2info, sep='\t')
        q2info.columns = pd.MultiIndex.from_tuples([qTableD.columns[0] if n==0 else (i,'','') for n,i in enumerate(q2info.columns)])
        qTableD = pd.merge(q2info, qTableD, how='right', on=[qTableD.columns[0]])
    
    if args.outdir:
        ptmMapPath = os.path.join(args.outdir, config.get("path_plots_Without_threshold"), contrast)
        ptmMapPathFDR = os.path.join(args.outdir, config.get("path_plots_with_threshold"), contrast)
        ptmMapPathExcel = os.path.join('../../../', os.path.join(config.get("path_plots_Without_threshold"), contrast))
        ptmMapPathFDRExcel = os.path.join('../../../', os.path.join(config.get("path_plots_with_threshold"), contrast))
        
        if os.path.isdir(ptmMapPath):
            plotted_q = [os.path.splitext(i)[0] for i in os.listdir(ptmMapPath)]
            qTableD = qTableD[[qTableD.columns[0]]].rename(columns={'':'NoFilt'}).join(qTableD)
            qTableD[qTableD.columns[0]] = \
                [f"=HYPERLINK(\"{os.path.join(ptmMapPathExcel, i)}.html\", \"{i}\")" if i in plotted_q else '' if i=='Sum' else i for i in qTableD.iloc[:, 0]]
            
        if os.path.isdir(ptmMapPathFDR):
            plotted_q = [os.path.splitext(i)[0] for i in os.listdir(ptmMapPathFDR)]                
            qTableD = qTableD[[qTableD.columns[1]]].rename(columns={'':'Filt'}).join(qTableD)
            qTableD[qTableD.columns[0]] = \
                [f"=HYPERLINK(\"{os.path.join(ptmMapPathFDRExcel, i)}.html\", \"{i}\")" if i in plotted_q else '' if i=='Sum' else i for i in qTableD.iloc[:, 0]]
        
    # Remove Hypergeom columns from PSMs table
    if quan == 'PSMs':
        qTableD = qTableD.drop(
            [(i,j,k) for i,j,k in qTableD.columns if i == 'Hypergeom' and j in ['NMbased', 'DPbased', 'DTbased', 'qcbased', 'PTMbased']],
            axis=1
        ).copy()

    return qTableD

def sortPeptidesTables(qReportList, config):
    # qReportList elem --> (fdr_i, sign_i, quan, qReportDesign(*i))
    
    # Create dict (fdr_i, sign_i) -> PTMs columns sorted
    
    
    myPTMsort = {
     (fdr_i, sign_i): [('Peptides', col[1], col[2]) for col in qReportDesigned.columns if col[0]=='PSMs' and col[2]!=''] 
     for fdr_i, sign_i, quan, qReportDesigned in qReportList if quan == 'PSMs'
     }
    
    myqCol = (config['qCol'][0], config['qCol'][1], '')
    myProteinSort = {
        (fdr_i, sign_i): qReportDesigned[myqCol].tolist()
        for fdr_i, sign_i, quan, qReportDesigned in qReportList if quan == 'PSMs'
        }
    
    qReportList2 = []
    for qReportList_i in qReportList:
        fdr_i, sign_i, quan, qReportDesigned = qReportList_i
        
        if quan == 'PSMs':
            qReportList2.append(qReportList_i)
            continue
        
        # elif quan == 'Peptides'
        newCols = [i for i in qReportDesigned.columns if i[0] != 'Peptides' or i[2]==''] +\
            myPTMsort[(fdr_i, sign_i)]        
        qReportDesigned2 = qReportDesigned.loc[:, newCols]
        
        # Sort proteins (row)
        qReportDesigned2 = qReportDesigned2.iloc[
            [qReportDesigned2[myqCol].tolist().index(i) for i in myProteinSort[(fdr_i, sign_i)]], :
        ]
        
        qReportList2.append((fdr_i, sign_i, quan, qReportDesigned2))

    
    return qReportList2
    # 


def qReportMergeUpDown(params, config):
    md = {}
    
    for i in params:
        fdr, sign, quan, df = i[1], i[2], i[3], i[4]
        if fdr not in md.keys():
            md[fdr] = {}
        
        if quan not in md[fdr].keys():
            md[fdr][quan] = {}
        
        if sign not in md[fdr][quan].keys():
            md[fdr][quan][sign] = df
            md[fdr][quan]['params'] = i
        
    params2 = []
    for fdr in md:
        for quan in md[fdr]:
            if 'up' not in md[fdr][quan] or 'down' not in md[fdr][quan]: continue
            dfup = md[fdr][quan]['up']
            dfdo = md[fdr][quan]['down']
            params_i = list(md[fdr][quan]['params'])
    
            dfup = dfup.sort_values(dfup.columns[0])
            dfdo = dfdo.sort_values(dfdo.columns[0])
            
            dfup.index = np.arange(0,dfup.shape[0])
            dfdo.index = np.arange(0,dfdo.shape[0])
            
            _i = [n for n,i in enumerate(dfup.columns) if i == (quan, 'PTMs', '')][0]
            dfup_ptm = dfup.iloc[:, _i:]
            dfup_wo = dfup.iloc[:, :_i]
            
            _i = [n for n,i in enumerate(dfdo.columns) if i == (quan, 'PTMs', '')][0]
            dfdo_ptm = dfdo.iloc[:, _i:]
            dfdo_wo = dfdo.iloc[:, :_i]
            
            dfup_ptm.columns = pd.MultiIndex.from_tuples([('up', *i) for i in dfup_ptm.columns])
            dfdo_ptm.columns = pd.MultiIndex.from_tuples([('down', *i) for i in dfdo_ptm.columns])
            
            df_ptm = dfup_ptm.join(dfdo_ptm)
            
            df_out = pd.DataFrame()
            for col in dfup_wo.columns:
                if 'sig' in col[1]:
                    if col[1] == 'NMsig':
                        df_out[('up (NM decreased)', *col)] = dfup_wo[col]
                        df_out[('down (NM increased)', *col)] = dfdo_wo[col]
                    else:
                        df_out[('up', *col)] = dfup_wo[col]
                        df_out[('down', *col)] = dfdo_wo[col]
                elif 'Hypergeom' in col[0]:
                    df_out[('up', *col)] = dfup_wo[col]
                    df_out[('down', *col)] = dfdo_wo[col]
                else:
                    df_out[('', *col)] = dfup_wo[col]
            
            df_out.columns = pd.MultiIndex.from_tuples(df_out.columns)
            df_out = df_out.join(df_ptm)
              
            # Row with Sum in the first position
            mySumIndex = df_out.index.tolist()[df_out[('', config['qCol'][0],config['qCol'][1], '')].tolist().index('Sum')]
            df_out = df_out.loc[[mySumIndex] + [i for i in df_out.index.tolist() if i!=mySumIndex]]        
            
            params_i[2] = 'up&down'
            params_i[4] = df_out
            params2.append(tuple(params_i))

    return params2


def qReportWrite(config, fdr_i, sign_i, quan, qTableD, contrast, significance_value):
    
    outFolder = os.path.join(args.outdir, config['outDirName'], contrast, f'{significance_value}-{fdr_i}')
    if not os.path.exists(outFolder):
        os.makedirs(outFolder, exist_ok=True)
    
    qReportPath = os.path.join(outFolder, f'qReports-{fdr_i}_{sign_i}_{quan}.xlsx')
    
    header = list(zip(*qTableD.columns.tolist()))
    qTableD.columns = np.arange(0, qTableD.shape[1])
    
    qTableD = pd.concat([pd.DataFrame(header), qTableD])
    
    qTableD.to_excel(
        qReportPath,
        header=False,
        index=False#, sep='\t'
        )
    
    toFormat = [n+1 for n,i in enumerate(qTableD.iloc[:, 0]) if 'HYPERLINK' in i]
    toFormat2 = [n+1 for n,i in enumerate(qTableD.iloc[:, 1]) if 'HYPERLINK' in i]
    
    book = openpyxl.load_workbook(qReportPath)
    sheet = book['Sheet1']
    # sheet.delete_rows(4, 1)
    # sheet.delete_cols(1, 1)
    
    for i in toFormat:
        sheet[f'A{i}'].font = openpyxl.styles.Font(color='0000FF', underline='single')
    
    for i in toFormat2:
        sheet[f'B{i}'].font = openpyxl.styles.Font(color='0000FF', underline='single')
    
    book.save(qReportPath)
    
    

def qReportContrast(rep0, config, contrast, significance_value):
    '''
    Parameters
    ----------
    config : TYPE
        DESCRIPTION.
    contrast : TYPE
        DESCRIPTION.

    Returns
    -------
    None.
    '''
    logging.info(f"*** {contrast} ***")

    # get the n_cpu from config file. Otherwise, get the 75% of total cpu's
    n_cpu_total = multiprocessing.cpu_count()
    n_cpu = config.get('n_cpu', (n_cpu_total * 75) // 100)
    n_cpu = max(1, n_cpu)  # ensure at least one process

    pdmCol, qCol, qdCol, pdmFreq, qFreq, sign, signNM, FDRdNM, FDRNM = getColumnNames(config, contrast, significance_value)
    ptmCol = ('PTM', 'REL')
    
    # Get required report fraction
    rep = rep0.loc[:, list(set([
        pdmCol, qCol, pdmFreq, qFreq, sign, signNM, FDRdNM, FDRNM, qdCol, ptmCol, 
        tuple(config['pCol']),tuple(config['gCol']), tuple(config['aCol']), tuple(config['mCol'])]))].drop_duplicates()
    
    
    # Extract NM elements from report
    repNM = rep.loc[[i==(None, None) for i in rep[ptmCol]], [qCol, pdmCol, pdmFreq, FDRNM, signNM]]
    repNM = {
        'PSMs': repNM.copy(),
        'Peptides': repNM.copy()
        }
    repNM['Peptides'][pdmFreq] = [0 if i==0 else 1 for i in repNM['Peptides'][pdmFreq]]
    

    repPQF = getRepQF(rep0, config, contrast, significance_value)
    
    # Create folder with output files
    # if not os.path.exists(os.path.join(args.outdir, 'FreqTables', contrast)):
    #     os.makedirs(os.path.join(args.outdir, 'FreqTables', contrast), exist_ok=True)
    
    
    # All combinations FDR x Sign
    fdrxsign = list(itertools.product(config['qvThr'], ['up', 'down']))
    
    params = [(config, fdr_i, sign_i, rep, ptmCol, contrast, significance_value) for fdr_i, sign_i in fdrxsign]
    qReportList = [(i[1], i[2], qReportPivot(*i)) for i in params]
    
    params = [
     (config, fdr_i, sign_i, quan, qTableD[quan], repNM[quan], repPQF[quan], rep, contrast, significance_value) 
     for fdr_i, sign_i, qTableD in qReportList if qTableD 
     for quan in qTableD
     ]

    # # Single core
    # logging.info("Pivot Report to obtain pre-qReport...")
    # qReportList = [(i[1], i[2], i[3], qReportAddData(*i)) for i in params]

    # Multicore
    logging.info(f"Pivot Report to obtain pre-qReport (ncpu: {n_cpu})...")
    pool = multiprocessing.Pool(processes=n_cpu)
    qReportList = pool.starmap(qReportAddData, params)
    pool.close()
    pool.join()
    qReportList = [(i[1], i[2], i[3], j) for i,j in zip(params, qReportList)]
    
    
    logging.info('Adding data to qReport')
    params = [
     [(config, quan, qTableD, contrast, significance_value), (fdr_i, sign_i, quan)]
     for fdr_i, sign_i, quan, qTableD in qReportList
     ]
    qReportList = [(fdr_i, sign_i, quan, qReportDesign(*i)) for i, (fdr_i, sign_i, quan) in params]
    
    # Sort PTMs of Peptides table as PSMs table
    qReportList = sortPeptidesTables(qReportList, config)
    
    logging.info('Adapting qReport format')
    params = [
     (config, fdr_i, sign_i, quan, qTableD, contrast, significance_value)
     for fdr_i, sign_i, quan, qTableD in qReportList
     ]
    
    params = params + qReportMergeUpDown(params, config)
    

    if args.outdir:
        # # single core
        # logging.info("Writing output...")
        # _ = [qReportWrite(*i) for i in params]

        # multi core
        logging.info(f"Writing output (n_cpu: {n_cpu})...")
        with multiprocessing.Pool(processes=n_cpu) as pool:
            pool.starmap(qReportWrite, params)

    else:
        return qReportList
    

def getPTMCol(rep, config):
    # Add column with pair (aminoacid, deltamass)
    pdmCol = tuple(config['pdmCol'])
    if config['pdmColFormat']==2:
        logging.info('Formatting pdm from ; to []')
        mypgm = [i.split(';') for i in rep[pdmCol]]
        rep[pdmCol] = [
            f'{i[0]}_{i[1]}' if len(i)==2 or i[2]=='' else f'{i[0][:int(i[2])]}[{i[1]}]{i[0][int(i[2]):]}'
            for i in mypgm
        ]
    
    # Get PTM from input report
    logging.info('Get PTMs from input report')
    
    myptm = [re.search(r'(.)\[([^]]+)\]', pdm_i) for pdm_i in rep[pdmCol]]
    myptm = [i.groups() if i else (None, None) for i in myptm]
    return myptm


def getBasalQReport(rep, qCol, qDescCol, pdmFreq, ptmCol):
    df = rep.loc[:, [qCol, qDescCol, pdmFreq, ptmCol]].copy()
    df[ptmCol] = [('NM', 'NM') if i==None and j==None else (i,j) for i,j in df[ptmCol]]

    df[('np', 'REL')] = 1
    df = df.groupby([qCol, qDescCol, ptmCol]).agg("sum").reset_index().droplevel(1, axis=1)
    
    basal = {}
    for freqType, name in [(pdmFreq[0], 'PSMs'), ('np', 'Peptides')]: 
    
        basal[freqType] = df.pivot(columns=ptmCol[0], index=[qCol[0], qDescCol[0]], values=[freqType]) 
    
        basal[freqType].columns = pd.MultiIndex.from_tuples([j for i,j in basal[freqType].columns])
        basal[freqType] = basal[freqType].fillna(0)
        
        basal[freqType] = pd.concat([
            pd.DataFrame(basal[freqType].sum(axis=0), columns=[('','Total')]).T, 
            basal[freqType]
        ]).sort_values(('', 'Total'), axis=1, ascending=False)
        
        basal[freqType].columns = pd.MultiIndex.from_tuples([
            (i[0], i[1], j) for i,j in zip(basal[freqType].columns, basal[freqType].iloc[0,:].values)
            ])
        
        basal[freqType].sum(axis=0)
        
        i = basal[freqType].columns.tolist()
        basal[freqType][('', '', 'Total')] = basal[freqType].sum(axis=1)
        basal[freqType] = basal[freqType].loc[:, [('','','Total'), *i]]
        
        basal[freqType] = basal[freqType].sort_values(('','','Total'), axis=0, ascending=False)
        basal[freqType] = basal[freqType].replace(0, np.nan)
        basal[freqType].index = pd.MultiIndex.from_tuples(basal[freqType].index)
        basal[freqType] = basal[freqType].iloc[1:, :]
        
        outFolder = os.path.join(args.outdir, config['outDirName'], "Basal")
        if not os.path.exists(outFolder):
            os.makedirs(outFolder, exist_ok=True)
        basal[freqType].to_csv(os.path.join(outFolder, f'Basal_{name}.tsv'), sep='\t')
    
    return


#
# Main
# 


def main(config, file=None):
    '''
    main
    '''
    
    # Get pandas report from file or read it from config
    if file:
        rep = file.copy()
    else:
        logging.info(f"Reading Report: {args.infile}")
        rep = pd.read_csv(
            args.infile, 
            sep='\t', 
            low_memory=False, 
            header=[0,1],
            keep_default_na=True,
            na_values='#DIV/0!'
            )
    

    logging.info(f"Pre-processing data...")
    ptmCol = ('PTM', 'REL')
    rep[ptmCol] = [
        #(None, None) if np.isnan(k) else (i,j) 
        (None, None) if j == config['NMgroup'] else (i,j) 
        for i,j, k in zip(rep[tuple(config['aCol'])], rep[tuple(config['gCol'])], rep[tuple(config['mCol'])])
        ]
    pdmCol = tuple(config['pdmCol'])
    #rep[ptmCol] = getPTMCol(rep, config)
    rep = rep[~rep[pdmCol].duplicated()]
    
    # extract the significance value: p-value or q-value
    significance_value = config['significance_value']


    logging.info(f"Getting Basal qReport...")
    _ = getBasalQReport(rep, tuple(config['qCol']), tuple(config['qDescCol']), tuple(config['pdmFreq']), ptmCol)
    
    logging.info(f"Getting qReport by groups...")
    return [qReportContrast(rep, config, '-'.join(group), significance_value) for group in config['groups']]
    



if __name__ == '__main__':
    

    parser = argparse.ArgumentParser(
        description='''
        qReportMaker - Module designed for peptide-centric quantitative proteomics workflows.

        This module enables a detailed exploration of significant changes at the protein level in a peptide-centric workflow.
        It generates an output table summarizing the number of modified and non-modified peptidoforms with significant increases or decreases, along with details on digestion status and qc clusters.

        Example:
            python qReportMaker.py -i path/to/diffexpr_report.tsv -c config/qReportMaker.yaml -o results/qReports/ -q path/to/q2info.tsv  -p path/to/PTMMapPlots/
        ''',
        epilog='''Developed for PTM-Analyzer quantitative proteomics workflows''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    default_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'params.yml')
    parser.add_argument('-i', '--infile', required=True, help='Path to report with peptide-level differential expression results and annotations')
    parser.add_argument('-q', '--q2info', help='Path to report with protein information')
    parser.add_argument('-p', '--ptmmap', help='Path to PTMMap plots')
    parser.add_argument('-o', '--outdir', required=True, help='Path to the folder where output files will be saved')
    parser.add_argument('-c', '--config', default=default_config_path, type=str, help='Path to YAML configuration file defining column mappings, thresholds, and output options (default: config/params.yml)')

    args = parser.parse_args()


    with open(args.config) as file:
        full_config = yaml.load(file, Loader=yaml.FullLoader)
        # merge 'General' and 'qReportMaker' into a single config
        config = {**full_config.get('General', {}), **full_config.get('qReportMaker', {})}

    # prepare workspace
    if not os.path.exists(args.outdir):
        os.makedirs(args.outdir, exist_ok=False)
        

    logging.basicConfig(level=logging.INFO,
                        format='qReportMaker.py - '+str(os.getpid())+' - %(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        handlers=[logging.FileHandler(
                            os.path.join(args.outdir, 'qReportMaker.log')
                            ),
                            logging.StreamHandler()])

    logging.info('Start script: '+"{0}".format(" ".join([x for x in sys.argv])))
    main(config)
    logging.info('End script')

