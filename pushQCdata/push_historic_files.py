"""
Executes api call scripts for each json file in given list

Input: csv with list of json paths
Output: api request calls for the chosen calls
"""

import argparse
import getpass
import json
from pathlib import Path

import pandas as pd

# Importing scripts for json reshaping
import patch_analysis as s5
import reshape_analysis as s2
import reshape_idsnp as s4
import reshape_metrics as s3
import reshape_flowcell as s1


# On individual jsons:
def runApiCalls(
    raw_qc: dict, passcheck: str, resulthandling: str, usrname: str, password: str
) -> None:
    """Posts analysis, metrics and idsnp-checks.
    Then patches the analysis to say approved/failed depending on input.

    Args:
        raw_qc (dict): input qc (summary.json on HPC)
        passcheck (str): is this analysis approved/failed by facilities
        resulthandling (str): send the results to Aero or save them locally for testing
        usrname (str): FreeIPA username
        password (str): FreeIPA password
    """
    # shortcuts
    rh = resulthandling
    er = raw_qc["metadata"]["experiment_run"]

    # Getting facility name for api URL
    facilityName = er["lab_id"][0]
    # Testing for '_test' suffix in id string:
    if "_test" in facilityName:
        size = len(facilityName)
        facilityName = facilityName[: size - 5]
    facilityName = facilityName.replace("_", "-")

    # Set type perm IDs:
    analysisTypePermId = (
        # analysis type id for Germline Analysis
        "00000000-e186-4e86-85eb-55145dc0333d"
    )
    # pipeline id for Germline NBA-2 Pipeline
    pipelinePermID = "11111111-af39-4e13-bbc9-6d45cf802945"
    # Run the reshapings of the dict
    analysisRegDict, samplename = s2.reshapeAnalysis(
        raw_qc, analysisTypePermId, pipelinePermID
    )
    metricsDict = s3.reshape(raw_qc)
    idsnpDict = s4.reshape(raw_qc)

    # Send reshaped data to Aero API
    analysisPermID = ""
    if rh == "send":
        # 1: Send analysis and get various analysis specific IDs back
        analysisPermID, pipelineRunPermID, lastUpdateDateTime = s2.sendAnalysisReg(
            analysisRegDict, facilityName, usrname, password
        )

        # 2: Send metrics for analysis
        returnedDict = s3.sendMetrics(
            metricsDict,
            facilityName,
            analysisPermID,
            pipelinePermID,
            pipelineRunPermID,
            usrname,
            password,
        )

        # 3: Send idsnp for analysis
        returnedDict = s4.sendIdsnp(
            idsnpDict, facilityName, analysisPermID, usrname, password
        )

        # Send json as request to AeroAPI
        # 4: Patch analysis approve status
        lastUpdateDateTime = s5.getLastUpdateDateTime(
            facilityName, analysisPermID, usrname, password
        )
        patchDict = s5.patchAnalysis(
            raw_qc, passcheck, analysisPermID, lastUpdateDateTime
        )
        returnedDict = s5.sendPatchRequest(
            patchDict, facilityName, analysisPermID, usrname, password
        )

    else:
        with open(resulthandling + "/analysis_" + samplename + ".json", "w") as outfile:
            returnedDict = json.dumps(analysisRegDict, indent=2)
            outfile.write(returnedDict)
        with open(resulthandling + "/metrics_" + samplename + ".json", "w") as outfile:
            returnedDict = json.dumps(metricsDict, indent=2)
            outfile.write(returnedDict)
        with open(resulthandling + "/idsnp_" + samplename + ".json", "w") as outfile:
            returnedDict = json.dumps(idsnpDict, indent=2)
            outfile.write(returnedDict)
        patchDict = s5.patchAnalysis(
            raw_qc, passcheck, analysisPermID, lastUpdateDateTime
        )
        with open(
            resulthandling + "/patchAnalysis_" + samplename + ".json", "w"
        ) as outfile:
            returnedDict = json.dumps(patchDict, indent=2)
            outfile.write(returnedDict)


def runFlowcellCalls(jsonlist: list, resulthandling: str, usrname: str, password: str) -> None:
    """Runs through all analyses, reshapes them to jsons that fit the Aero API sorted by flowcells and posts or or saves them locally.

    :param jsonlist: List of paths to summary.jsons
    :type jsonlist: list
    :param resulthandling: 'send' will send it to Aero API or input a path to save locally
    :type resulthandling: str
    :param usrname: FreeIPA username
    :type usrname: str
    :param password: FreeIPA password
    :type password: str
    """
    rh = resulthandling
    # Handle flowcell registration from sample jsons:
    multijson = s1.reshapeToFlowcellJsons(jsonlist)
    if rh == "send":
        for flowcellid in multijson.keys():
            # Testing for '_test' suffix in id string:
            facilityName = flowcellid.split("-", 1)[
                1
            ]  # Get first value in split string which contains lab_id aka. facilityName
            if "_test" in facilityName:
                size = len(facilityName)
                facilityName = facilityName[: size - 5]
                facilityName = facilityName.replace("_", "-")
            facilityName = facilityName.replace("_", "-")
            s1.sendFlowcells(multijson[flowcellid],
                             facilityName, usrname, password)
    else:
        for flowcellid in multijson.keys():
            s1.saveFlowcellJsons(multijson[flowcellid], flowcellid, rh)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "qc_list_input",
        type=Path,
        help="Path to file with list of json paths and various parameters on them. Genereated by get_json_paths.py",
    )
    parser.add_argument(
        "resulthandling",
        type=str,
        help="Define if results should be sent or saved to file [send / pathToSaveDir]",
    )
    args = parser.parse_args()

    usrname = input("\nEnter username...\n")
    pw = getpass.getpass("\nEnter password...\n")

    # Handle flowcell registration
    with args.qc_list_input.open("r") as src:
        jsonlist = pd.read_csv(src)
        jsonlist = jsonlist.values.tolist()

    runFlowcellCalls(
        jsonlist, args.resulthandling, usrname, pw
    )

    run_choice = "Not given"
    # Handle other api calls one by one
    for jsonfile in jsonlist:
        jsonpath = jsonfile[0]

        if run_choice == "Not given":
            run_choice = input(
                "\nEnter 'a' to send all jsons in list or 'o' to accept one by one..")

        if run_choice == "a":
            # Open json file
            with open(jsonpath, "r") as src:
                qc_payload = json.load(src)

            runApiCalls(qc_payload, jsonfile[1],
                        args.resulthandling, usrname, pw)
        else:
            while True:
                run_choice = input(
                    "\nSend {}? Enter 'y' to send, 'n' to skip or 'a' to run all remaining samples...".format(jsonfile[6]))

                if run_choice == "y" or run_choice == "a":
                    with open(jsonpath, "r") as src:
                        qc_payload = json.load(src)
                    runApiCalls(
                        qc_payload, jsonfile[1], args.resulthandling, usrname, pw)
                    break
                elif run_choice == "n":
                    break
                else:
                    print("\nWrong choice... try again")
                    continue
