"""
Script for reshaping NBA-2 Germline pipeline QC JSON into something more suitable for
HTTP POST analyses payloads.

Input: csv file with paths of sample json files in first column of each row. Extra columns are ignored.
Output: reshaped json file for each sample. Instead of saving, they can be directly sent as request with option -r
"""

import json
import sys

import requests

def reshapeAnalysis(raw_qc: dict, analysisTypePermID: str,
                    pipelinePermID: str):
    """Reshape a dict of a qc json into an analysis for the Aero API

    :param raw_qc: dictioany of qc json
    :type raw_qc: dict
    :param analysisTypePermID: as according to the Aero API
    :type analysisTypePermID: str
    :param pipelinePermID: as according to the Aero API
    :type pipelinePermID: str
    :return: reshaped dict and sample name as a string
    :rtype: dict, str
    """

    # shortcuts
    er = raw_qc["metadata"]["experiment_run"]
    es = er["experiment_samples"][0]

    analysisRegJson = {
        "analysisName": es["sample_name"],
        "analysisTypePermID": analysisTypePermID,
        "pipelineRuns": [
            {"pipelinePermID": pipelinePermID,
                "samples": [
                    {"subjectID": es["subject_id"],
                     "sampleID": es["sample_id"],
                     "sampleName": es["sample_name"]
                     }
                ]
             }
        ]
    }

    return analysisRegJson, es["sample_name"]


def sendAnalysisReg(analysisRegDict: dict,
                    facilityName: str, usrname: str, pw: str):
    """Send analysis to Aero API

    :param analysisRegDict: _description_
    :type analysisRegDict: dict
    :param facilityName: _description_
    :type facilityName: str
    :param usrname: FreeIPA username
    :type usrname: str
    :param pw: Free IPA password
    :type pw: str
    :return: _description_
    :rtype: _type_
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
    json.dump(tokenjson.json(), sys.stdout, indent=2)

    keycloaktoken = tokenjson.json()['access_token']

    # Show sent json:
    sys.stdout.write('\nSENT:\n')
    json.dump(analysisRegDict, sys.stdout, separators=(",", ":"), indent=2)

    posturl = 'https://aero-hpc.dev.ngc.dk/wgs-facilities/' + \
        facilityName + '/qc/analyses'
    # Send json as request to AeroAPI
    r = requests.post(
        posturl,
        json=analysisRegDict,
        verify='/usr/local/share/ca-certificates/CA-NGC.pem',
        headers={
            'Authorization': 'Bearer {}'.format(keycloaktoken)})

    # Print recieved info:
    sys.stdout.write('\nRECIEVED:\nStatus code: ' + str(r.status_code) + '\n')
    sys.stdout.write('Trace ID: ' + r.headers.get('Trace-ID'))
    sys.stdout.write('JSON:\n')
    json.dump(r.json(), sys.stdout, indent=2)

    return r.json()["permID"], r.json()[
        'pipelineRuns'][0]["pipelineRunPermID"], r.json()['lastUpdateDatetime']


if __name__ == "__main__":

    pass
