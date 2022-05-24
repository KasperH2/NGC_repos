"""
Find all relevant json files, make a list of their paths,check,facility,NBA,shortname,samplename,file and save as csv.
Does not look for hidden files.

Folder structure of folders holding json files must be /<check>/>facility>/<NBA>/<shortname>/<samplename>/<file.json>
Example: /passed/wgs_east/NBA2/200622_A00559_0210_AHTFHCDMXX/06sjyvj81-17RKG002918-01_103719193860-DNA_Blood-WGS_v1-H27F5DSX2-RHGM00111/qc.json

Input: json folder path
Output: csv files with list of all json
"""

import argparse
import os
from argparse import RawTextHelpFormatter
from pathlib import Path

import pandas as pd


# Making list of all files in the 'path' variable. Avoiding NBA1 and
# hidden folders and files.
def findJSONS(path: Path) -> pd.DataFrame:
    """Find all relevant json files, make a list of their paths,check,facility,NBA,shortname,samplename,file and save as csv.
    Does not look for hidden files. Folder structure of folders holding json files must be /<check>/>facility>/<NBA>/<shortname>/<samplename>/<file.json>
    Example: /passed/wgs_east/NBA2/200622_A00559_0210_AHTFHCDMXX/06sjyvj81-17RKG002918-01_103719193860-DNA_Blood-WGS_v1-H27F5DSX2-RHGM00111/qc.json

    :param path: path to folders to look for summary.json files
    :type path: Path
    :param outfile: outfile path to save csv file with list of all paths
    """

    newlist = []

    for root, dirs, files in os.walk(path):

        files = [f for f in files if not f.startswith('.')]

        for file in files:
            newlist.append(str(os.path.join(root, file)))

    # Converting list to dataframe for filtering
    df = pd.DataFrame(newlist, columns=['path'])

    # split paths of df into values and make new columns for chosen values of
    # the split
    path_length = str(path).split('/')
    jsonpathstart = len(path_length)
    jsonpathend = jsonpathstart + 6

    df[['check', 'facility', 'NBA', 'shortname', 'samplename', 'file']
       ] = df['path'].str.split('/', expand=True).iloc[:, jsonpathstart:jsonpathend]

    # filtering for json files only and no NBA1 samples
    df = df[df['NBA'] == 'NBA2']
    df = df[df['file'].str.contains(".json")]

    return df


if __name__ == "__main__":

    usage = __doc__.split("\n\n\n", 1)

    # RawTextHelpFormatter enables newline use in argparse helptext
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('inpath', type=Path, help="Path to folder to search for json files. \n Folders with json files beneath this path must be in the following structure:\n /<check>/>facility>/<NBA>/<shortname>/<samplename>/<file.json>\n Example:\n .../passed/wgs_east/NBA2/200622_A00559_0210_AHTFHCDMXX/06sjyvj81-17RKG002918-01_103719193860-DNA_Blood-WGS_v1-H27F5DSX2-RHGM00111/qc.json")
    parser.add_argument('savefile', type=Path,
                        help="savefile path, e.g: <alljson.csv>")

    args = parser.parse_args()

    jsondf = findJSONS(args.inpath)
    pd.DataFrame.to_csv(
        jsondf,
        args.savefile,
        sep=",",
        index=False,
        quoting=None)
