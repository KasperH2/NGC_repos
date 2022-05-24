"""
Script for reshaping NBA-2 Germline pipeline QC JSON into something more suitable for
HTTP POST flowcell payloads.

Input: csv file with paths of sample json files in first column of each row. Extra columns are ignored.
Output: json file for each found flowcell with all samples in that flowcell. Instead of saving
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import requests


def reshapeToFlowcellJsons(jsonlist: list) -> dict:
    """Reshape a list of jsonpaths to a dictionary reshaped and sorted into flowcells

    :param jsonlist: list of jsonpaths
    :type jsonlist: list
    :raises SystemExit: _description_
    :return: jsons reshaped and sorted into flowcells
    :rtype: dict
    """
    # Opening jsons from list one by one and creating a big dict with specific
    # keys from all
    multiFCjson = {}
    for sample in range(len(jsonlist)):
        qc_json = jsonlist[sample][0]  # filepath is first value in list
        # fileCheck = jsonlist[sample][1] # pass/fail check is second value in
        # list

        # Getting summary.json qc parameter values
        with open(qc_json, "r") as src:
            raw_qc = json.load(src)

        # shortcuts
        er = raw_qc["metadata"]["experiment_run"]
        es = er["experiment_samples"][0]

        flowcell_id = er["flowcell_id"][0]

        # Check if date or datetime:
        if len(str(er["start_time"][0])) > 10:
            dateformat = "dateTime"
        elif len(str(er["start_time"][0])) <= 10:
            dateformat = "date"

        # Inputting values for flowcell in directory
        # Check if flowcell_id exists in multiFCjson, else create the keys for
        # it
        if flowcell_id not in multiFCjson.keys():

            # Create new values for flowcell
            # Making dict with either date or datetime, depending on what is
            # given
            if dateformat == "date":
                multiFCjson[flowcell_id + '-' + er['lab_id'][0]] = {
                    "flowcellID": er["flowcell_id"][0],
                    "flowcellNr": er["run_number"][0],
                    "machineSerialNr": er["instrument_serial_nr"][0],
                    "seqRunID": er["run_id"][0],
                    "seqRunDate": er["start_time"][0],
                    "samples": []
                }
            elif dateformat == "dateTime":
                multiFCjson[flowcell_id + '-' + er['lab_id'][0]] = {
                    "flowcellID": er["flowcell_id"][0],
                    "flowcellNr": er["run_number"][0],
                    "machineSerialNr": er["instrument_serial_nr"][0],
                    "seqRunID": er["run_id"][0],
                    # "seqRunDatetime" : er["start_time"][0], TEST
                    "seqRunDate": er["start_time"][0][:10],
                    "samples": []
                }

        else:

            # Check for equal values in already loaded flowcell and new
            # flowcell

            # string conversions [new_json,old_json]
            fCstr = ["flowcellID", "flowcell_id"]
            fIDstr = ["flowcellNr", "run_number"]
            sRID = ["seqRunID", "run_id"]
            dateID = ["seqRunDate", "start_time"]
            dateTimeID = ["seqRunDatetime", "start_time"]  #For possible future use

            # commented out as TEST, currently cant check because datetime is
            # not working at backend
            if dateformat == "dateTime":
                checklist = [fCstr, fIDstr, sRID]  # dateTimeID
            elif dateformat == "date":
                checklist = [fCstr, fIDstr, sRID, dateID]

            for valueToCheck in checklist:
                if multiFCjson[flowcell_id + '-' + er['lab_id']
                               [0]][valueToCheck[0]] != er[valueToCheck[1]][0]:
                    raise SystemExit(f'{valueToCheck[0]} does not match previous values for:\n' +
                                     qc_json +
                                     '\nthis file have\n' +
                                     er[valueToCheck[1]][0] +
                                     '\nand previous have\n' +
                                     multiFCjson[flowcell_id + '-' + er['lab_id'][0]][valueToCheck[0]])

        # Find sample specific values and append to dict
        samplesubdict = {
            "ngcSubjectID": es["ngc_subject_id"],
            "sampleID": es["sample_id"],
            "sampleName": es["sample_name"],
            "subjectID": es["subject_id"],
            "registrationIDs": [
                es["registration_id"]
            ]
        }

        # Append sample specific values to flowcell json
        multiFCjson[flowcell_id + '-' + er['lab_id']
                    [0]]["samples"].append(samplesubdict)

    return multiFCjson


def saveFlowcellJsons(flowcelljson: dict, flowcellid: str,
                      jsonsavepath: str) -> None:
    """Saves flowcell dicts individually in json files

    :param flowcelljson: dict
    :type flowcelljson: dict
    :param flowcellid: flowcell ID
    :type flowcellid: str
    :param jsonsavepath: path to save json file
    :type jsonsavepath: str
    """
    jsonsavepath = str(jsonsavepath)
    filename = str(
        jsonsavepath +
        '/' +
        "flowcellReg" +
        '_' +
        flowcellid +
        '.json')
    with open(str(filename), 'w') as fp:
        json.dump(flowcelljson, fp, indent=2)


def sendFlowcells(flowcelljson: dict, facilityName: str,
                  usrname: str, pw: str) -> None:
    """Send flowcells to the Aero API

    :param flowcelljson: flowcell dictionary
    :type flowcelljson: dict
    :param facilityName: such as wgs-west or wgs-east
    :type facilityName: str
    :param usrname: FreeIPA username
    :type usrname: str
    :param pw: FreeIPA password
    :type pw: str
    """

    keycloackurl = 'https://keycloak.dev.ngc.dk/auth/realms/Ngc/protocol/openid-connect/token'
    header = {'Content-Type': 'application/x-www-form-urlencoded'}
    cert = '/usr/local/share/ca-certificates/CA-NGC.pem'

    tokenjson = requests.post(keycloackurl, headers=header, verify=cert, data={'username': usrname,
                                                                               'password': pw,
                                                                               'scope': 'profile',
                                                                               'grant_type': 'password',
                                                                               'client_id': 'sqs-web'
                                                                               })

    keycloaktoken = tokenjson.json()['access_token']

    # Show sent json:
    sys.stdout.write('\nSENT:\n')
    json.dump(flowcelljson, sys.stdout, separators=(",", ":"), indent=2)

    # Send json as request to AeroAPI
    r = requests.post(
        'https://aero-hpc.dev.ngc.dk/wgs-facilities/' +
        facilityName +
        '/qc/flowcells',
        json=flowcelljson,
        verify='/usr/local/share/ca-certificates/CA-NGC.pem',
        headers={
            'Authorization': 'Bearer {}'.format(keycloaktoken)})

    # Print recieved info:
    sys.stdout.write('\nRECIEVED:\nStatus code: ' + str(r.status_code) + '\n')
    sys.stdout.write('Trace ID: ' + r.headers.get('Trace-ID'))
    sys.stdout.write('JSON:\n')
    json.dump(r.json(), sys.stdout, indent=2)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'qc_list_input',
        type=Path,
        help="Path to list of input QC JSON paths")
    parser.add_argument(
        'resulthandling',
        type=str,
        help="Define if results should be send or saved to file [send / pathToSaveDir]")
    parser.add_argument(
        'username',
        type=str,
        help="FreeIPA username")
    parser.add_argument(
        'pw',
        type=str,
        help="FreeIPA password")
    args = parser.parse_args()

    with args.qc_list_input.open("r") as src:
        jsonpaths = pd.read_csv(src)
        jsonpaths_list = jsonpaths.values.tolist()
        multijson = reshapeToFlowcellJsons(jsonpaths_list)

    # Handle results
    rh = args.resulthandling

    if rh == "send":
        for flowcellid in multijson.keys():
            # Getting facility name for api URL
            er = multijson[flowcellid]["metadata"]["experiment_run"]
            facilityName = er["lab_id"][0]
            # Testing for '_test' suffix in id string:
            if "_test" in facilityName:
                size = len(facilityName)
                facilityName = facilityName[: size - 5]
            facilityName = facilityName.replace("_", "-")

            sendFlowcells(
                multijson[flowcellid],
                facilityName,
                args.username,
                args.pw)
    else:
        for flowcellid in multijson.keys():
            saveFlowcellJsons(multijson[flowcellid], flowcellid, rh)
