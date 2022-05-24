#!/usr/bin/env python3
# (c) 2022 The Danish National Genome Center / Nationalt Genom Center
# Author: KHO@NGC.DK
# Last updated: 21-03-2022 by KHO@NGC.DK

# Formats output summary table from hap.py to pretty table. Called by run_single.sh in bencher.

import datetime
import io
import json
import os
from argparse import ArgumentParser

import pandas as pd

# arguments
parser = ArgumentParser()
parser.add_argument("-i", "--input", required=True,
                    help="input hap.py summary csv")
parser.add_argument("-o", "--output", required=True, help="output csv")
parser.add_argument("-r", "--glnid", required=True, help="gln run id")
parser.add_argument("-s", "--samplename", required=True, help="sample name")
parser.add_argument("-g", "--giab", required=True,
                    help="Genome in a Bottle name")
parser.add_argument("-q", "--qc_json", required=True,
                    help="path to summary.json from QC pipeline")
parser.add_argument("-c", "--historic", required=True,
                    help="path to file to save historic results")

args = parser.parse_args()


def read_csv(path):
    with open(path, 'r') as f:
        lines = [li for li in f if not li.startswith('##')]
    return pd.read_csv(io.StringIO(''.join(lines)))


csvfile = args.input

# load csv data
d = read_csv(csvfile)

# Getting relevant columns from file
type = d["Type"]
dfilter = d["Filter"]
recall = d["METRIC.Recall"]
precision = d["METRIC.Precision"]
F1 = d["METRIC.F1_Score"]

# Formatting table
df = pd.concat([type, dfilter, recall, precision, F1], axis=1)
df.columns = ["Type", "Filter", "Recall", "Precision", "F1"]
df = df[df.Filter == "ALL"]
df = df.drop(["Filter"], axis=1)
indeldf = df[df.Type == "INDEL"]
snpdf = df[df.Type == "SNP"]
snpdfrdy = snpdf.rename(
    columns={"Recall": "SNP_recall", "Precision": "SNP_precision", "F1": "SNP_F1"})
indeldfrdy = indeldf.rename(
    columns={"Recall": "Indel_recall", "Precision": "Indel_precision", "F1": "Indel_F1"})

snpdfrdy = snpdfrdy.drop(["Type"], axis=1)
indeldfrdy = indeldfrdy.drop(["Type"], axis=1)

# Resetting index number to 0, so it can easily be joined to indeldf
snpdfrdy = snpdfrdy.reset_index(inplace=False)
snpdfrdy = snpdfrdy.drop("index", axis=1)
snpdfrdy = snpdfrdy.join([indeldfrdy])

# Getting summary.json qc parameter values
with open(args.qc_json, 'r') as datfile:
    d_dict = json.loads(datfile.read())

# check if the correct format and get parameter values from json file
# JSON key shortcut
qc = d_dict['germline_full']['metrics']['samples'][0]['QC_summary']
# If these names are changed, also change them in the historic file appending (further below)
if 'germline_full' in d_dict.keys():
    LabID = d_dict['metadata']['experiment_run']['experiment_samples'][0]['lab_id']
    RunID = next(iter(d_dict['germline_full']['outputs']))  # It is the only key in this path
    MedianInsertSize = qc['median_insert_size']
    MeanCov = qc['mean_coverage']
    PercentTargetBaseOver10Cov = qc['pct_10x']
    PercentTargetBaseOver20Cov = qc['pct_20x']
else:
    print("No germline_full value in dict. Is this a germline sample file?")

# Adding to dataframe
dfsample = pd.DataFrame({"Lab_ID": LabID, "Sample_name": [
                        args.samplename], "Run_ID": [RunID], "GiaB_sample": [args.giab]})
dfsample = dfsample.join(snpdfrdy)

# Adding other parameters at the end of the dataframe
dfsample["Fraction_at_least_10x"] = float(PercentTargetBaseOver10Cov)
dfsample["Fraction_at_least_20x"] = float(PercentTargetBaseOver20Cov)
dfsample["Median_insert_size"] = float(MedianInsertSize)
dfsample["Mean_coverage"] = float(MeanCov)
dfsample["Hap.py_run_date"] = datetime.datetime.now().strftime(
    "%d-%m-%y")  # Adding date added

# Adds trailing 0's to float numbers so that numbers that are ex 0.73 will be 0.73000.
# This converts the float to object, which can hinder further number processing and is only for excel conventience. Mac Excel "," and "." notation
# acts weird when a table of different numbered decimals are given. The section can be removed if needed, but watch out for excel readability.
for colname in dfsample:
    if dfsample[colname].dtypes == "float64":
        dfsample[colname] = dfsample[colname].map('{:.5f}'.format)
        print("is float:", colname)

# Saving dataframe
pd.DataFrame.to_csv(dfsample, args.output, sep=",", index=False)

# Saving data to historic file
# Checking for file existence
if os.path.exists(args.historic):
    historic = read_csv(args.historic)
    histdf = pd.DataFrame(historic)

    # Checking if sample, run id and giab are unique
    rowuniq = "maybe"
    for index, row in histdf.iterrows():

        if ((row['Sample_name'] == dfsample["Sample_name"][0]) & (row["Run_ID"] == dfsample["Run_ID"][0]) & (row["GiaB_sample"] == dfsample["GiaB_sample"][0])):
            print("A row in the historic file with this sample name, runid and GiaB id already exists, it was not appended")
            print(row['Sample_name'], row["Run_ID"], row['GiaB_sample'])
            rowuniq = "no"
    # if unique, append to historic file
    if rowuniq != "no":
        newdf = histdf.append(dfsample)
        pd.DataFrame.to_csv(newdf, args.historic, sep=",",
                            index=False, quoting=0)
else:
    # Creating file with if no historic file exists.
    pd.DataFrame.to_csv(dfsample, args.historic,
                        sep=",", index=False, quoting=0)
