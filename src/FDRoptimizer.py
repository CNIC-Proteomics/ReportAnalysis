# -*- coding: utf-8 -*-

#
# Import Modules
#

import argparse
import logging
import numpy as np
import os
import pandas as pd
import sys
import yaml
import re

from statsmodels.stats.multitest import multipletests
from plotly.subplots import make_subplots
import plotly.graph_objects as go

#
# Local Functions
#


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
        rep = pd.read_csv(args.infile, sep='\t', low_memory=False, header=[0,1])
        
    # prepare workspace for graphs
    outdir_gh = os.path.join(outdir, 'FDRoptimizer')
    logging.info(f"Preparing workspace for graphs: {outdir_gh}")
    if not os.path.exists(outdir_gh):
        os.makedirs(outdir_gh, exist_ok=False)


    for thr in config['FDR_Thr']:
        
        logging.info(f'FDR Threshold: {thr}')
    
        for group in config['groups']:
            t = '-'.join(group)

            logging.info(f'Group: {t}')
    
            #fig = make_subplots(rows=1, cols=len(config['FDR_integration']), subplot_titles=config['FDR_integration'])
            fig = make_subplots(rows=1, cols=len(config['ColumnNames']), subplot_titles=list(zip(*config['ColumnNames']))[-1])

            for i, (lvCol, scCol, integration) in enumerate(config['ColumnNames']):
            #for i, (integration, freqCol) in enumerate(zip(config['FDR_integration'], config['LevelFreqs'])):
                
                logging.info(f'Get FDR for integration "{integration}"')
                
                lvCol = tuple(lvCol)
                scCol = tuple(scCol)
                #lvCol = (re.search(r'^Z_([a-zA-Z]+)2', integration).groups()[0], 'LEVEL')
                #scCol = (freqCol, 'REL')
                
                if len(integration.split('-'))==2:
                    pvCol, myFilt = integration.split('-')
                    myField, myCol = re.search(r'([^\]]+)\(([^\]]+)\)', myFilt).groups()
                    myCol = tuple([i.strip() for i in myCol.split('&')])
                    rep[(f'{pvCol}_{myField}_ONLY_{t}', 'pvalue')] = [
                        j if i else np.nan
                        for i,j in 
                        zip(rep[myCol]==myField, rep.loc[:, (f'{pvCol}_{t}', 'pvalue')])
                    ]
                    pvCol = (f'{pvCol}_{myField}_ONLY_{t}', 'pvalue')
                
                else:
                    pvCol = (f'{integration}_{t}', 'pvalue')
                    
                    
                logging.info(f'Level column: {lvCol}')
                logging.info(f'Scan Frequency column: {scCol}')
                logging.info(f'Stat column: {pvCol}')
                
    
                tmp = rep.loc[:, [lvCol, pvCol, scCol]].dropna().drop_duplicates()
    
                x, y = zip(*[
                    (
                        s+1, 
                        sum(multipletests(tmp.loc[tmp.loc[:, scCol]>=s+1, pvCol], method='fdr_bh')[1]<=thr) 
                        if len(tmp.loc[tmp.loc[:, scCol]>=s+1, pvCol])>0 else 0
                        ) 
                    for s in range(*config['Window'])
                ])
                
                ymax = max(y)
                xmax = np.argmax(y)+1
                
                logging.info(f'Maximum number of significant elements {ymax} at scan frequency {xmax}')
                
                if config['AddFDR'] and thr==max(config['FDR_Thr']):
                    
                    boolean = tmp.loc[:, scCol]>=xmax
                    
                    tmp = tmp.join(
                        pd.DataFrame({
                            #(f'{pvCol[0]}', f'qvalue_{thr}'): multipletests(tmp.loc[boolean, pvCol], method='fdr_bh')[1]
                            (f'{pvCol[0]}', f'qvalue'): multipletests(tmp.loc[boolean, pvCol], method='fdr_bh')[1] if len(tmp.loc[boolean, pvCol])>0 else 1
                        }, index=tmp.index[boolean]), how='left'                        
                    )
                    
                    rep = pd.merge(
                        rep,
                        tmp,
                        how = 'left',
                        on = [lvCol, pvCol, scCol]
                    )
                        
                fig.add_trace(go.Scatter(
                    x=x, y=y,
                    mode='lines+markers', showlegend=False
                ), row=1, col=i+1)
    
                fig.update_xaxes(title=f'Minimum {scCol[0]}', row=1, col=i+1)
    
            fig.update_yaxes(title=f'N. of significative elems', row=1, col=1)
            fig.update_layout(title=f'{t}')
    
            # fig.show()
    
            with open(os.path.join(outdir_gh, f'FDR_{thr}.html'), 'a') as f:
                f.write(fig.to_html(full_html=False, include_plotlyjs='cdn', default_height='50%', default_width='95%'))
        
    if config['AddFDR'] and not file:
        rep.to_csv(args.outfile, sep='\t', index=False)
        

    return rep


if __name__ == '__main__':
    

    parser = argparse.ArgumentParser(
        description='''
        FDRoptimizer - Optimize spectral count thresholds for maximum statistical significance

        A script to optimize spectral count thresholds for maximum statistical significance across integration levels using Benjamini-Hochberg correction.
        It analyzes iSanXoT/limma-style reports to identify the best threshold per group and contrast.

        Example usage:
            python FDRoptimizer.py -i limma_report.tsv -o optimized_report.tsv -c FDRoptimizer.yaml
        ''',
        epilog='''Developed for PTM-Analyzer quantitative proteomics workflows''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    default_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'params.yml')
    parser.add_argument('-i', '--infile',  required=True, help='Path to report with the Limma comparisons')
    parser.add_argument('-o', '--outfile', required=True, help='Path to output where FDR values will be saved')
    parser.add_argument('-c', '--config',  default=default_config_path, type=str, help='Path to YAML config file (default: config/params.yml)')

    args = parser.parse_args()


    with open(args.config) as file:
        full_config = yaml.load(file, Loader=yaml.FullLoader)
        # merge 'General' and 'FDRoptimizer' into a single config
        config = {**full_config.get('General', {}), **full_config.get('FDRoptimizer', {})}
        

    # prepare workspace
    outdir = os.path.dirname(args.outfile)
    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=False)
    

    logging.basicConfig(level=logging.INFO,
                        format='FDRoptimizer.py - '+str(os.getpid())+' - %(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        handlers=[logging.FileHandler(
                            os.path.join(outdir, 'FDRoptimizer.log')
                            ),
                            logging.StreamHandler()])

    logging.info('Start script: '+"{0}".format(" ".join([x for x in sys.argv])))
    main(config)
    logging.info(f'End script')

