#!/usr/bin/env python3
# (c) 2022 The Danish National Genome Center / Nationalt Genom Center
# Author: PST@NGC.DK
# Last updated: 21-03-2022 by KHO@NGC.DK

# Finds sample JSON and output its path

import os
from argparse import ArgumentParser

if __name__ == '__main__':

    # arguments
    parser = ArgumentParser()
    parser.add_argument("-p", "--partial", action='store_true', default=False)
    parser.add_argument("-t", "--type", required=True,
                        help="type of the file: v or s for vcf or summary.json")
    parser.add_argument("-s", "--sid", required=True, help="sample_name")
    args = parser.parse_args()
    file_type = args.type
    partial = args.partial
    sid = args.sid.rstrip()

    # variables defining locations to search
    base = "/ngc/data_analysis/"
    labs = ["wgs_west", "wgs_east", "wgs_east_test",
            "wgs_west_test", "wgs_center_test"]
    results_locations = {
        "summary": {
            "pre_folder": "/analysis-results/germlineqc",
            "post_folder": "output-latest-completed/output",
            "file_match": "summary.json"
        },
        "s": {
            "pre_folder": "/analysis-results/germlineqc",
            "post_folder": "output-latest-completed/output",
            "file_match": "summary.json"
        },
        "vcf": {
            "pre_folder": "/analysis-results/germline",
            "post_folder": "output-latest-completed/output/gatk",
            "file_match": ".endpoint.vcf.gz"
        },
        "v": {
            "pre_folder": "/analysis-results/germline",
            "post_folder": "output-latest-completed/output/gatk",
            "file_match": ".endpoint.vcf.gz"
        }
    }

    # check type
    if file_type not in results_locations.keys():
        print("unsupported file type, please use: " +
              "|".join(results_locations.keys()))
        exit(1)

    # go over the paths
    for lab in labs:
        path = base + lab + results_locations[file_type]["pre_folder"]
        if os.path.isdir(path):
            for dir_lvl1 in os.listdir(path):
                if os.path.isdir(os.path.join(path, dir_lvl1)):
                    for dir_lvl2 in os.listdir(os.path.join(path, dir_lvl1)):
                        if os.path.isdir(os.path.join(path, dir_lvl1, dir_lvl2)):

                            # partial matching
                            if partial:
                                if sid in dir_lvl2:
                                    sid_path = os.path.join(
                                        path, dir_lvl1, dir_lvl2)
                                    for element in os.listdir(os.path.join(sid_path, results_locations[file_type]["post_folder"])):
                                        if element.endswith(results_locations[file_type]["file_match"]):
                                            print(os.path.join(
                                                sid_path, results_locations[file_type]["post_folder"], element))

                            # exact matching
                            else:
                                if dir_lvl2 == sid:
                                    sid_path = os.path.join(
                                        path, dir_lvl1, dir_lvl2)
                                    for element in os.listdir(os.path.join(sid_path, results_locations[file_type]["post_folder"])):
                                        if element.endswith(results_locations[file_type]["file_match"]):
                                            print(os.path.join(
                                                sid_path, results_locations[file_type]["post_folder"], element))
