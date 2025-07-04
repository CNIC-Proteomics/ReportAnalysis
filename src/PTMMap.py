#!/usr/bin/env python
# coding: utf-8

# Module metadata variables
__author__ = "Cristina Amparo Devesa Arbiol"
__credits__ = ["Cristina Amparo Devesa Arbiol", "Jose Rodriguez", "Jesus Vazquez"]
__license__ = "Creative Commons Attribution-NonCommercial-NoDerivs 4.0 Unported License https://creativecommons.org/licenses/by-nc-nd/4.0/"
__version__ = "0.0.1"
__maintainer__ = "Jose Rodriguez"
__email__ = "cristinaamparo.devesa@cnic.es;jmrodriguezc@cnic.es"
__status__ = "Development"


# Imports
import pandas as pd
import numpy as np
import plotly
import plotly.express as px
import plotly.graph_objects as go
import argparse
import logging
import os
import sys
import yaml
import multiprocessing
import warnings
warnings.filterwarnings("ignore")



###################
# Local functions #
###################
def readInfile(infile, pgm):
    '''    
    Read input file to dataframe.
    '''
    df = pd.read_csv(infile,sep="\t", encoding='latin',header=[0,1], low_memory=False)
    df.columns = df.columns.map('_'.join)

    df = df.replace('#NUM!',np.nan)
    df = df.drop_duplicates(subset=[pgm])

    return df

def applyStructure(row,New_FDR,g,NM,a,first_b,New_LPS,LPS_pgm2p,LPS_pgm2p_NM,n,FDR_pgm,p,e,d,a_g_d,pgmFreq,dicc_FDRNM,pgmFreqThreshold):

    row[e] = float(str(row[e]).split(";")[0])
    row[n] = float(str(row[n]).split(";")[0])
    if row[p] in dicc_FDRNM[New_FDR].keys(): 
        row[New_FDR] = dicc_FDRNM[New_FDR][row[p]] 
    if np.isnan(row[New_FDR]) == True: 
        row[New_FDR] = 1
    if np.isnan(row[FDR_pgm]) ==True: 
        row[FDR_pgm] = 1

    if np.isnan(row[New_FDR]) ==True and np.isnan(row[FDR_pgm]) ==True: 
        row[New_FDR] = np.nan
    elif row[New_FDR]< row[FDR_pgm]: 
        row[New_FDR] = row[New_FDR]
    elif row[New_FDR]> row[FDR_pgm]: 
        row[New_FDR] = row[FDR_pgm]    
    if row[g] ==NM: 
        row[a] = "U"
        if str(row[g])!= "nan": 
            dm = "|" +str(row[g])
        else:
            dm = str(row[d])
            dm ="|" + dm[:dm.find(".")+3]
        row[n] = (float(row[first_b])+float(row[e]))/2 # NM will be represented at the average position between first_b and first_e
        row[New_LPS] = row[LPS_pgm2p] 
            
        if row[p] in dicc_FDRNM[New_FDR].keys(): 
            row[New_FDR] = dicc_FDRNM[New_FDR][row[p]]  
    else:  
        row[New_LPS] = row[LPS_pgm2p_NM]
        if str(row[g])!= "nan": 
            dm = "|" +str(row[g])
        else:
            dm = str(row[d])
            dm ="|" + dm[:dm.find(".")+3]
        if row[a] == "U":
            row[n] = (float(row[first_b])+float(row[e]))/2 # NM will be represented at the average position between first_b and first_e
            

    if row[pgmFreq]>= pgmFreqThreshold: 
        row[a_g_d]= row[a]+dm
    else: 
        row[a_g_d] = row[a]
    return row

def obtaindf (df,New_FDR, g,a,n,first_b,LPS_pgm2p,LPS_pgm2p_NM,FDR_NM,FDR_pgm,FDR_p2qc,FDR_qc2q,Missing_Cleavages,LPS_p2qc,LPS_qc2q,e,description, p,q,qc,pFreq,pgmFreq, qcFreq,d,NM,threshold_pgm2p,pgmFreqThreshold):

    df = df.loc[:,[g, a,n,first_b,LPS_pgm2p,LPS_pgm2p_NM, FDR_NM, FDR_pgm,FDR_p2qc, FDR_qc2q,Missing_Cleavages,LPS_p2qc, LPS_qc2q, e , description,p, q, qc, pFreq, qcFreq, pgmFreq,d]]

    df = df.rename(columns={New_FDR:"New_FDR",FDR_pgm:"FDR_pgm",g:"g", a: "a",n:"n",first_b : "first_b", LPS_pgm2p: "LPS_pgm2p",
                        LPS_pgm2p_NM: "LPS_pgm2p_NM", FDR_NM: "FDR_NM",FDR_p2qc : "FDR_p2qc", FDR_qc2q:"FDR_qc2q",
                      Missing_Cleavages: "Missing_Cleavages",LPS_p2qc:"LPS_p2qc", LPS_qc2q:"LPS_qc2q", e : "e", description: "description",
                       p :"p", q:"q", qc:"qc", pFreq:"pFreq", qcFreq: "qcFreq", pgmFreq: "pgmFreq",d :"d"})
    df = df.astype({'FDR_NM': 'float64', 'FDR_pgm': 'float64','LPS_pgm2p_NM': 'float64','LPS_pgm2p': 'float64','FDR_p2qc': 'float64',
                'FDR_qc2q': 'float64','LPS_p2qc': 'float64','LPS_qc2q': 'float64','pgmFreq': 'float64','pFreq': 'float64','qcFreq': 'float64',
                'Missing_Cleavages': 'float64', "first_b": 'float64'})
    
    df =df[df['first_b'].notnull()] # if an incomplete input it will discard using this parameter

    dfpeptide= df[df.g.eq(NM)]
    dfpeptide_FDR= dfpeptide[dfpeptide.FDR_NM.le(threshold_pgm2p)]
    dfpeptide_FDR = dfpeptide_FDR[['p','FDR_NM']].rename(columns={"FDR_NM":"New_FDR"})
    dicc_FDRNM = dfpeptide_FDR.set_index('p').to_dict()
    dicc_FDRNM["New_FDR"].keys()
 
    df["New_LPS"] = np.nan
    df["New_FDR"] = np.nan
    df["a_g_d"] = ""

    
    df_final = df.apply(lambda y: applyStructure(y,"New_FDR","g",NM,"a","first_b","New_LPS","LPS_pgm2p","LPS_pgm2p_NM","n","FDR_pgm","p","e","d","a_g_d","pgmFreq",dicc_FDRNM,pgmFreqThreshold), axis = 1)
    
    return df_final

def p2qcMaker(dfp, listproteins, threshold_p2qc):
    dfp_proteins = dfp[dfp['q'].isin(listproteins)].drop_duplicates(subset=['p'])
    rows = []
    for _, row in dfp_proteins.iterrows():
        int_b = int(row["first_b"])
        int_e = int(row["e"])

        for i in range(int_b, int_e + 1):
            rows.append({
                "p": row["p"],
                "pFreq": row["pFreq"],
                "q": row["q"],
                "Missing_Cleavages": row["Missing_Cleavages"],
                "LPS_p2qc": row["LPS_p2qc"],
                "position": i,
                "description": row["description"],
                "FDR_p2qc": row["FDR_p2qc"],
            })

    df_p2qc = pd.DataFrame(rows)
    df_p2qc_filtered = df_p2qc[df_p2qc["FDR_p2qc"] <= threshold_p2qc].reset_index(drop=True)

    return df_p2qc, df_p2qc_filtered

def qc2qMaker(dfqc, listproteins, threshold_qc2q):
    dfqc_proteins = dfqc[dfqc['q'].isin(listproteins)].drop_duplicates(subset=['qc'])
    rows = []
    for _, row in dfqc_proteins.iterrows():
        # preprocess the 'qc' field once
        qc_str = row["qc"].replace("-", "_").split(";")[0].split(":")[1]
        W, V = map(int, qc_str.split("_"))

        for i in range(W, V + 1):
            rows.append({
                "qc": row["qc"],
                "q": row["q"],
                "qcFreq": row["qcFreq"],
                "LPS_qc2q": row["LPS_qc2q"],
                "position": i,
                "description": row["description"],
                "FDR_qc2q": row["FDR_qc2q"],
            })

    dfqc_2 = pd.DataFrame(rows)
    dfqc_2_filtered = dfqc_2[dfqc_2["FDR_qc2q"] <= threshold_qc2q].reset_index(drop=True)

    return dfqc_2, dfqc_2_filtered

def TablesMaker (df_final,threshold_p2qc,NM,New_LPS,New_FDR,threshold_pgm2p,FDR_qc2q,threshold_qc2q):
    # p2qc Table
    df_final["Missing_Cleavages"] = df_final["Missing_Cleavages"].replace(0,"DT").replace(1,"DP").replace(2,"DP").replace(3,"DP").replace(4,"DP")
    df_final["first_b"] = df_final["first_b"].astype(int)
    dfp =df_final[df_final["LPS_p2qc"].notnull()] 
    dfp_filtered= dfp[dfp.FDR_p2qc.le(threshold_p2qc)].reset_index()
     
    # pgm2p Table
    dfpgm = df_final[df_final[New_LPS].notnull()]
    dfpgm.loc[dfpgm["g"] !=NM, "g"] = 'Mod'
    dfpgm_filtered= dfpgm[dfpgm.New_FDR.le(threshold_pgm2p)].reset_index()
    
    #qc2q Table
    dfqc = df_final[df_final["LPS_qc2q"].notnull()]
    dfqc_filtered= dfqc[dfqc.FDR_qc2q.le(threshold_qc2q)].reset_index()
    
    # Proteins thar passs the filters 
    listproteins = list(set((list(dfp_filtered["q"])+list(dfpgm_filtered["q"])+list(dfqc_filtered["q"]))))
    logging.info("- proteins that pass the threshold p2qc: " + str(len(set(list(dfp_filtered["q"])))))
    logging.info("- proteins that pass the threshold pgm2p: " + str(len(set(list(dfpgm_filtered["q"])))))
    logging.info("- proteins that pass the threshold qc2q: " + str(len(set(list(dfqc_filtered["q"])))))
    
    logging.info("- creating p2qc report...")
    df_p2qc,df_p2qc_filtered = p2qcMaker(dfp, listproteins,threshold_p2qc)

    logging.info("- creating qc2q report...")
    dfqc_2,dfqc_2_filtered= qc2qMaker(dfqc, listproteins,threshold_qc2q)
    
    return df_p2qc,df_p2qc_filtered, dfqc_2,dfqc_2_filtered,dfpgm,dfpgm_filtered,listproteins

def plot_single_protein(prot, df_p2qc_filtered, dfpgm_filtered, dfqc_2_filtered, group_path, font_size, grid, plot_width, plot_height):

    listafail = []
    dfpgm_filtered["n"].astype('int')

    q = prot
    df1= df_p2qc_filtered[df_p2qc_filtered.q.eq(prot)]
    df1pgm= dfpgm_filtered[dfpgm_filtered.q.eq(prot)]
    df1pgm["pgmFreq"] = df1pgm["pgmFreq"].astype(float)

    dfqc_3= dfqc_2_filtered[dfqc_2_filtered.q.eq(prot)]
    dfqc_3["qcFreq"] = dfqc_3["qcFreq"].astype(float)
    list1 = list(df1pgm["n"])
    list1 = [int(x) for x in list1]
    dfqc_3["q"] = dfqc_3["q"].replace(prot,"qc2q")
    listw= list1+list(dfqc_3["position"])+list(df1["position"])
    listw.sort()
    df1pgm["a_g"] = df1pgm["a_g_d"] + "<br>" + "p= "+ df1pgm["p"]
    try: 
        fig1 = px.scatter(df1, x="position", y="LPS_p2qc",
                    size="pFreq", color="Missing_Cleavages",
                                hover_name="Missing_Cleavages", size_max=8, opacity=1, title=list(df1["description"])[0],color_discrete_map={"DT": "lightgreen", "DP": "black"}, width=400, height=400)
        fig1.update_traces(
            marker=dict(symbol="square", line=dict(width=0, color="DarkSlateGrey")),
            selector=dict(mode="markers"),)
    except: 
        fig1= "false"

    try:
        fig2 = px.scatter(df1pgm, x="n", y="New_LPS",
                size="pgmFreq", color="g",
                            hover_name="g", size_max=90,text="a_g", hover_data={"a_g": True},color_discrete_map={"NM": "orchid", 'Mod' :"red"}, width=400, height=400)
        fig2.for_each_trace(lambda t: t.update(textfont_color=t.marker.color))
        fig2.for_each_trace(lambda t: t.update(textfont_color='rgba(0,0,0,0)'))
    except: 
        fig2 ="false"

    try:
        fig3 = px.scatter(dfqc_3, x="position", y="LPS_qc2q", size="qcFreq",color = 'q',hover_name= 'q', opacity=1, size_max=9,color_discrete_map={"qc2q": "orange"}, width=400, height=400)
        fig3.update_traces(
            marker=dict( symbol="square", line=dict(width=0, color="orange")),
            selector=dict(mode="markers"),)
    except:
        fig3 = "false"


    if fig1 =="false" and fig2!="false" and fig3!= "false":
        fig = go.Figure(data = fig3.data  + fig2.data)
    elif fig1 =="false" and fig2=="false" and fig3!= "false":
        fig = go.Figure(data = fig3.data)
    elif fig1 =="false" and fig2!="false" and fig3== "false":
        fig = go.Figure(data = fig2.data)
    elif fig1 !="false" and fig2=="false" and fig3== "false":     
        fig = go.Figure(data = fig1.data)
    elif fig1 !="false" and fig2=="false" and fig3!= "false":
        fig = go.Figure(data = fig3.data  + fig1.data)  
    elif fig1!="false" and fig2!="false" and fig3== "false":
        fig = go.Figure(data = fig1.data  + fig2.data) 
    else: 
        fig = go.Figure(data = fig3.data + fig1.data + fig2.data)
    try: 
        fig.update_xaxes(range=[0,(listw[-1]+100)])
    except: 
        listafail.append(prot)
        pass

    try : 
        fig.update_layout(title_text=list(dfqc_3["description"])[0])
    except: 
        try : 
            fig.update_layout(title_text=list(df1["description"])[0])
        except: 
            fig.update_layout(title_text=list(df1pgm["description"])[0])
    
    fig.update_traces(textfont_size=1)
    fig.update_layout(yaxis = dict(tickfont = dict(size=font_size)))
    fig.update_layout(xaxis = dict(tickfont = dict(size=font_size)))
    fig.update_layout(paper_bgcolor = "rgba(0,0,0,0)",plot_bgcolor = "rgba(0,0,0,0)")
    if grid == "No": 
        fig.update_yaxes(showline=True, linewidth=5, linecolor='black', gridcolor='white', gridwidth=0,zeroline=True, zerolinewidth=5, zerolinecolor='black')
    else: 
        fig.update_yaxes(showline=True, linewidth=3, linecolor='black', gridcolor='black', gridwidth=1,zeroline=True, zerolinewidth=5, zerolinecolor='black',)
        fig.update_xaxes(showline=True, linewidth=3, linecolor='black', 
                gridcolor='black', gridwidth=1)
        
    fig.update_xaxes(tickangle=-90, showline=True, linewidth=5, linecolor='black')
    fig.update_layout(width=plot_width, height=plot_height, xaxis=dict(ticks="outside",ticklen=15, tickwidth=5), yaxis=dict(ticks="outside",ticklen=15, tickwidth=5))
    fig.write_html(group_path + "/" + q + ".html", config={'toImageButtonOptions': {'format': 'svg', 'filename': q, 'height': plot_height, 'width': plot_width, 'scale': 1}})



###################
# Main functions #
###################
def main(config):

    """
    Reading configuration file
    """
    logging.info("Reading PTMap configuration file")

    # extract required column parameters
    pgm_first_header, pgm_second_header = config.get("pgm_column_name", ["", ""])
    pgm = f"{pgm_first_header}_{pgm_second_header}"
    g_first_header, g_second_header = config.get("g_column_name", ["", ""])
    g = f"{g_first_header}_{g_second_header}"
    a_first_header, a_second_header = config.get("a_column_name", ["", ""])
    a = f"{a_first_header}_{a_second_header}"
    n_first_header, n_second_header = config.get("n_column_name", ["", ""])
    n = f"{n_first_header}_{n_second_header}"
    e_first_header, e_second_header = config.get("e_column_name", ["", ""])
    e = f"{e_first_header}_{e_second_header}"
    p_first_header, p_second_header = config.get("p_column_name", ["", ""])
    p = f"{p_first_header}_{p_second_header}"
    q_first_header, q_second_header = config.get("q_column_name", ["", ""])
    q = f"{q_first_header}_{q_second_header}"
    d_first_header, d_second_header = config.get("d_column_name", ["", ""])
    d = f"{d_first_header}_{d_second_header}"
    qc_first_header, qc_second_header = config.get("qc_column_name", ["", ""])
    qc = f"{qc_first_header}_{qc_second_header}"
    pFreq_first_header, pFreq_second_header = config.get("pFreq_column_name", ["", ""])
    pFreq = f"{pFreq_first_header}_{pFreq_second_header}"
    qcFreq_first_header, qcFreq_second_header = config.get("qcFreq_column_name", ["", ""])
    qcFreq = f"{qcFreq_first_header}_{qcFreq_second_header}"
    pgmFreq_first_header, pgmFreq_second_header = config.get("pgmFreq_column_name", ["", ""])
    pgmFreq = f"{pgmFreq_first_header}_{pgmFreq_second_header}"
    first_b_first_header, first_b_second_header = config.get("first_b_column_name", ["", ""])
    first_b = f"{first_b_first_header}_{first_b_second_header}"
    description_first_header, description_second_header = config.get("description_column_name", ["", ""])
    description = f"{description_first_header}_{description_second_header}"
    Missing_Cleavages_first_header, Missing_Cleavages_second_header = config.get("Missing_Cleavages_column_name", ["", ""])
    Missing_Cleavages = f"{Missing_Cleavages_first_header}_{Missing_Cleavages_second_header}"

    NM = config.get("NM")

    # extract threshold parameters
    threshold_pgm2p_NM = config.get("threshold_pgm2p_NM") 
    threshold_pgm2p = config.get("threshold_pgm2p") 
    threshold_p2qc = config.get("threshold_p2qc") 
    threshold_qc2q = config.get("threshold_qc2q")     
    pgmFreqThreshold = config.get("pgmFreqThreshold")

    # extract map parameters
    font_size = config.get("font_size")
    grid= config.get("grid")
    plot_width= config.get("plot_width")
    plot_height= config.get("plot_height")

    # extract folders to save the maps
    path_plots_FDR = config.get("path_plots_with_threshold")
    path_plots = config.get("path_plots_Without_threshold")

    # extract the significance value: p-value or q-value
    significance_value = config.get("significance_value")

    # extract the groups
    groups = config.get("groups")

    # get the n_cpu from config file. Otherwise, get the 75% of total cpu's
    n_cpu_total = multiprocessing.cpu_count()
    n_cpu = config.get('n_cpu', (n_cpu_total * 75) // 100)
    n_cpu = max(1, n_cpu)  # ensure at least one process


    logging.info(f"Reading input file: {args.infile}...")
    df = readInfile(args.infile,pgm)

    logging.info(f'Processing by groups: {groups}')
    # for grp in groups:
    for group in groups:
        grp = '-'.join(group)
        logging.info(f"Preparing workspace for '{grp}'...")
        # prepare workspaces
        group_path_FDR = os.path.join(args.outdir, path_plots_FDR, grp)
        group_path = os.path.join(args.outdir, path_plots, grp)
        if not os.path.exists(group_path):
            os.makedirs(group_path, exist_ok=False)
        if not os.path.exists(group_path_FDR):
            os.makedirs(group_path_FDR, exist_ok=False)

        logging.info(f'- preparing parameters...')

        # read LPS column mappings
        LPS_mappings = config.get("LPS_ColumnNames", {})
        LPS_p2qc = f"{LPS_mappings['p2qc'][0]}_{grp}_{LPS_mappings['p2qc'][1]}"
        LPS_qc2q = f"{LPS_mappings['qc2q'][0]}_{grp}_{LPS_mappings['qc2q'][1]}"
        LPS_pgm2p = f"{LPS_mappings['pgm2p'][0]}_{grp}_{LPS_mappings['pgm2p'][1]}"
        LPS_pgm2p_NM = f"{LPS_mappings['pgm2p_NM'][0]}_{grp}_{LPS_mappings['pgm2p_NM'][1]}"

        # read NM column mappings
        NM_mappings = config.get("NM_ColumnNames", {})
        FDR_pgm = f"{NM_mappings['pgm2p']}_{grp}_{significance_value}"
        FDR_NM = f"{NM_mappings['pgm2p_NM']}_{grp}_{significance_value}"

        # read Filter column mappings
        Filter_mappings = config.get("Filter_ColumnNames", {})
        FDR_p2qc = f"{Filter_mappings['p2qc']}_{grp}_{significance_value}"
        FDR_qc2q = f"{Filter_mappings['qc2q']}_{grp}_{significance_value}"

        logging.info("- obtaining group data...")
        df_final = obtaindf (df,"New_FDR",g,a,n,first_b,LPS_pgm2p,LPS_pgm2p_NM,FDR_NM,FDR_pgm,FDR_p2qc,FDR_qc2q,Missing_Cleavages,LPS_p2qc,LPS_qc2q,e,description, p,q,qc,pFreq,pgmFreq, qcFreq,d,NM,threshold_pgm2p,pgmFreqThreshold)

        logging.info("- preparing data...")
        df_p2qc,df_p2qc_filtered, dfqc_2,dfqc_2_filtered,dfpgm, dfpgm_filtered, listproteins= TablesMaker (df_final,threshold_p2qc,NM,"New_LPS","New_FDR",threshold_pgm2p,FDR_qc2q,threshold_qc2q)

        logging.info(f"- plotting filtered data (ncpu: {n_cpu})...")
        params_p2qc_filtered = [(prot, df_p2qc_filtered, dfpgm_filtered, dfqc_2_filtered, group_path_FDR, font_size, grid, plot_width, plot_height) for prot in listproteins ]
        with multiprocessing.Pool(processes=n_cpu) as pool:
            pool.starmap(plot_single_protein, params_p2qc_filtered)

        logging.info(f"- plotting all data (ncpu: {n_cpu})...")
        params_p2qc = [(prot, df_p2qc, dfpgm, dfqc_2, group_path, font_size, grid, plot_width, plot_height) for prot in listproteins ]
        with multiprocessing.Pool(processes=n_cpu) as pool:
            pool.starmap(plot_single_protein, params_p2qc)





if __name__ == '__main__':

    # parse arguments
    parser = argparse.ArgumentParser(
        description='''
        PTMMap - Visualize and compare protein post-translational modifications (PTMs)
        
        This tool generates interactive maps for each protein, displaying residue-specific PTM events and zonal changes 
        based on statistical significance (LPS) between experimental conditions.
        Two subfolders will be created:
            - "path_plots_with_threshold" (maps for modifications meeting the threshold), and 
            - "path_plots_without_threshold" (full protein maps).

        Example:
            python PTMMap.py -i limma_output.tsv -o PTM_maps/ -c PTMMap.yml -v
        ''',
        epilog='''Developed for PTM-Analyzer quantitative proteomics workflows''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
      
    # default PTMaps configuration file
    default_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'params.yml')
    parser.add_argument('-i', '--infile', required=True, help='Path to the input report file containing p-values and LPS scores from limma comparisons')
    parser.add_argument('-o', '--outdir', required=True, help='Output directory to save PTM maps.')
    parser.add_argument('-c', '--config', default=default_config_path, help='Path to the YAML configuration file specifying thresholds, plotting options, and residue annotations (default: config/params.yml)')
    parser.add_argument('-v', dest='verbose', action='store_true', help='Enable verbose logging for detailed progress messages')
    args = parser.parse_args()
   
   # parse config
    with open(args.config) as file:
        full_config = yaml.load(file, Loader=yaml.FullLoader)
        # merge 'General' and 'PTMMap' into a single config
        config = {**full_config.get('General', {}), **full_config.get('PTMMap', {})}

    # prepare workspace
    outdir = args.outdir
    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=False)

    # logging debug level. By default, info level
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            handlers=[logging.FileHandler(os.path.join(outdir, 'PTMMap.log')),
                                      logging.StreamHandler()])
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            handlers=[logging.FileHandler(os.path.join(outdir, 'PTMMap_debug.log')),
                                      logging.StreamHandler()])

    # start main function
    logging.info('start script: '+"{0}".format(" ".join([x for x in sys.argv])))
    main(config)
    logging.info("end of the script")
