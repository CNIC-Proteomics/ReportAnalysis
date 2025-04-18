# Modules

1. [MergeiSanxotPDM](#1-mergeisanxotpdm)
2. [NMpyCompare](#2-nmpycompare)
3. [ReportLimma](#3-reportlimma)
4. [FDRoptimizer](#4-fdroptimizer)
5. [PTMMap](#5-ptmmap)
6. [qTableReport](#6-qtablereport)

### 1. MergeiSanxotPDM
This Python script merges the iSanXoT report of protein2proteinall with the PDM table.

### 2. NMpyCompare

This module calculates NM-corrected values from the iSanXoT report. It subtracts the Zpgm2p value of the associated non-modified peptidoform from the Zpgm2p value of each modified peptidoform. Users can specify column names for integration levels, quantitative values, and criteria for identifying non-modified peptidoforms through the configuration file. The NM-corrected values are then appended as new columns in the iSanXoT report.

### 3. ReportLimma

This script performs hypothesis testing for comparisons between different groups across integration levels using the **limma** package. It computes p-values for statistical contrasts, the mean difference between groups, and the LPS value (-log(p-value) adjusted by the sign of the mean difference).

### 4. FDRoptimizer

Implemented in Python, this script applies an iterative algorithm to optimize the spectral count threshold at each integration step. It scans different thresholds to maximize the number of elements with a q-value below a user-defined threshold, using the Benjamini-Hochberg algorithm for multiple testing correction.

### 5. PTMMap

PTMMap is a tool developed with the aim of visualizing, interpreting, and comparing the proteins' PTMs. This module represents as many maps as proteins for which any integration meets the threshold established by the user. Each map illustrates the change between one condition and another based on the p-value of all calculated integrations, on the y-axis.

```
LPS = -log2(p-value) * sign (Condition2 - Condition1)
```

On the x-axis, the position of each residue of the protein is represented. Specific modifications and hypermodified zones are represented by circles, while partial and total digestion, and zonal changes are represented by rectangles. The size of these markers depends on the frequency of each parameter, in a relative scale depending on the maximum and minimum PSMs frequency of each type of modification. These graphs offer interactivity and enable the visualization of parameter frequency, modified residue, and the specific group of each Δmass.

- **Input:**
  - `.tsv` file with limma p-values and -LPS calculated for each integration.
  - Configuration file (`.yml`)
    - PTMMap parameters:
      ```
      PTMMap:

        # Folder in which filtered PTM Maps will be saved
        path_plots_with_threshold: PTMmaps_filtered
        path_plots_Without_threshold: PTMmaps

        # Plot parameters
        font_size: 50
        grid: 'No'
        plot_width: 1700
        plot_height: 850

        # Required column names
        pgm_column_name: [pgm, LEVEL]
        g_column_name: [g, REL]
        a_column_name: [a, REL]
        n_column_name: [n, REL]
        e_column_name: [e, REL]
        p_column_name: [p, LEVEL]
        q_column_name: [q, LEVEL]
        d_column_name: [d, REL]
        qc_column_name: [qc, LEVEL]
        pFreq_column_name: [pFreq, REL]
        qcFreq_column_name: [qcFreq, REL]
        pgmFreq_column_name: [pgmFreq, REL]
        first_b_column_name: [first_b, REL]
        description_column_name: [description, REL]
        Missing_Cleavages_column_name: [Missing_Cleavage, REL]

        # How Non-modified are named
        NM: NM

        # Group to be analysed
        groups:
          - H-C

        # LPS integrations for: p2qc, qc2q, pgm2p, pgm2p_MN
        # [LowLevel_firstRow, LowLevel_secondRow]
        LPS_ColumnNames:
          p2qc:     [Z_p2qc_logLimma, LPS]
          qc2q:     [Z_qc2q_logLimma, LPS]
          pgm2p:    [Z_pgm2p_logLimma, LPS]
          pgm2p_NM: [Z_pgm2p_dNM_logLimma, LPS]

        # NM comparison for pgm2p integrations
        # [LowLevel_firstRow, LowLevel_secondRow]
        NM_ColumnNames:
          pgm2p:    [Z_pgm2p_dNM_limma, qvalue]
          pgm2p_NM: [Z_pgm2p_limma_NM_ONLY, qvalue]

        # Filter integrations for: p2qc, qc2q
        # [LowLevel_firstRow, LowLevel_secondRow]
        Filter_ColumnNames:
          p2qc: [Z_p2qc_limma, qvalue]
          qc2q: [Z_qc2q_limma, qvalue]

        # Threshold of filtering for the given integrations: pgm2p_NM, pgm2p, p2qc, qc2q
        threshold_pgm2p_NM: 0.05
        threshold_pgm2p: 0.05
        threshold_p2qc: 0.05
        threshold_qc2q: 0.05
        pgmFreqThreshold: 0
      ```

- **Output:**
  - Two output folders. Both contain only maps of the proteins for which some of their modifications meet the threshold established by the user. In one of the folders (`path_plots_with_threshold`), only the maps featuring modifications that meet the threshold set by the user are represented, while in the other (`path_plots_Without_threshold`), complete maps of the proteins are depicted.


[Go to top](#modules)
___


### 6. qTableReport

This module enables a detailed exploration of significant changes at the protein level in a peptide-centric workflow. It generates an output table summarizing the number of modified and non-modified peptidoforms with significant increases or decreases, along with details on digestion status and qc clusters.


[Go to top](#modules)
___

