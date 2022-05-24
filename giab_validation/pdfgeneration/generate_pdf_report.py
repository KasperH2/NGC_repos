#!/usr/bin/env python3
# Author: PST@NGC.DK
# Last updated: 21-03-2022 by KHO@NGC.DK

# Script will load a table and output data to Latex through Jinja
# to create a pdf document. Called by generate_pdf_report.sh

import argparse
import io
import os
from datetime import datetime

import jinja2
import pandas as pd

import qcreporthelpers as reph  # load_json and normal_round functions

# Define read csv function


def read_csv(path):
    with open(path, 'r') as f:
        lines = [li for li in f if not li.startswith('##')]
    return pd.read_csv(io.StringIO(''.join(lines)))

# prepare the report function


def render_report(output_path, csvname, report_template, report_data, plots=None):

    # set up latex env.
    latex_env = jinja2.Environment(
        block_start_string='{%',  # default jinja start
        block_end_string='%}',  # default jinja end
        variable_start_string='{{ ',  # note the space after {{
        variable_end_string=' }}',  # note the space before }}
        line_comment_prefix='%#',
        trim_blocks=True,  # remove first newline after a block
        lstrip_blocks=True,  # remove spaces to the left of blocks
        autoescape=False,
        loader=jinja2.FileSystemLoader(['/', os.path.abspath('.')])
    )

    # load report_template
    report_template_rendering = latex_env.get_template(report_template)

    # write into new template
    output_tex = output_path + "/" + csvname + ".tex"
    with open(output_tex, 'w') as f:
        print(report_template_rendering.render(report_data=report_data,
              plots=plots, normal_round=reph.normal_round), file=f)


def main():

    # load arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sample_csv', required=True,
                        help="The sample csv file with results")
    parser.add_argument('-t', '--template', required=True,
                        help="The LaTeX report template used with Jinja2")
    parser.add_argument('-o', '--output', required=True, help="Output file")
    args = parser.parse_args()

    # load sample csv
    d = read_csv(args.sample_csv)

    # format results
    dTrans = d.T  # transposing table
    dTrans.columns = ["Value"]

    # Seperating data to dfs
    # Choose parameters for ID:
    params = ["Lab_ID", "Sample_name", "Run_ID", "GiaB_sample"]
    dID = dTrans.loc[params]
    selectedparams = params

    # Get all other columns
    dValues = dTrans.drop(labels=selectedparams, axis=0)
    dValues = dValues.drop(labels="Hap.py_run_date")

    # Seperating data to dfs
    # Choose parameters for ID:
    params = ["Lab_ID", "Sample_name", "Run_ID", "GiaB_sample"]
    dID = dTrans.loc[params]
    selectedparams = params
    # Get all other columns
    dValues = dTrans.drop(labels=selectedparams, axis=0)
    dValues = dValues.drop(labels="Hap.py_run_date")

    # Adding validation target values to dataframe. Must be floats or integers.
    snp_recall = 0.9993
    snp_precision = 0.9904
    snp_F1 = ""
    indel_recall = 0.9865
    indel_precision = 0.9885
    indel_F1 = ""
    mean_coverage = 30
    median_insert_size = 392.59000
    fraction_target_bases_atleast_10x = 0.95000
    fraction_target_bases_atleast_20x = 0.90000

    dValues["Target"] = [snp_recall,
                         snp_precision,
                         snp_F1,
                         indel_recall,
                         indel_precision,
                         indel_F1,
                         fraction_target_bases_atleast_10x,
                         fraction_target_bases_atleast_20x,
                         median_insert_size,
                         mean_coverage
                         ]

    # generate plots, for future use
    plots = {}

    # Create output folder
    csvfile = os.path.basename(args.sample_csv)  # get file
    csvname = os.path.splitext(csvfile)[0]  # get file without its extension

    # Define output
    output_path = args.output

    if not os.path.exists(output_path):
        os.mkdir(output_path)
    else:
        print("!! Out folder for pdf already existed. The old occurence got \"_old\" and a timestamp appended to its name !!")
        now = datetime.now()
        dt_string = now.strftime("%Y_%m_%d_%H_%M_%S")
        os.rename(output_path, str(output_path + "_old_" + dt_string))
        os.mkdir(output_path)

    # generate the tex report file
    render_report(output_path, csvname, args.template, [dID, dValues], plots)


if __name__ == '__main__':
    main()
