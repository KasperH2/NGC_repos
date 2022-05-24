"""
Script for patching analysis for pushing of historical data to SQS.
"""

import json
import sys

import requests


def getLastUpdateDateTime(
        facilityName: str, analysisPermID: str, usrname: str, pw: str) -> str:
    """get LastUpdateDateTime from analysis perm ID

    :param facilityName: _description_
    :type facilityName: str
    :param analysisPermID: _description_
    :type analysisPermID: str
    :param usrname: _description_
    :type usrname: str
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

    # Get last updateDateTime
    posturl = 'https://aero-hpc.dev.ngc.dk/wgs-facilities/' + \
        facilityName + '/qc/analyses/' + analysisPermID
    r = requests.get(
        posturl,
        verify='/usr/local/share/ca-certificates/CA-NGC.pem',
        headers={
            'Authorization': 'Bearer {}'.format(keycloaktoken)})
    json.dump(r.json(), sys.stdout, separators=(",", ":"), indent=2)

    lastUpdateDatetime = r.json()['lastUpdateDatetime']

    return lastUpdateDatetime


def patchAnalysis(raw_qc: dict, qcCheck: str, permid: str,
                  lastUpdateDatetime: str):

    if qcCheck == "pass" or qcCheck == "passed":
        checkvalue = "approved"
    elif qcCheck == "fail" or qcCheck == "failed":
        checkvalue = "failed"
    else:
        print("Unknown check:" + qcCheck)

    # shortcuts
    new_json = [{
        "permID": permid,
        "lastUpdateDatetime": lastUpdateDatetime,
        "ops": [
            {"op": "replace",
             "path": "/evalStatus",
             "value": checkvalue
             },
            {"op": "add",
             "path": "/comments",
             "value": "Historical data from NBA 2.0. Pushed in relation to first release of SQS."
             },
            {"op": "replace",
             "path": "/submitStatus",
             "value": "submitted"
             }
        ]
    }]

    return new_json


def sendPatchRequest(analysisRegJson: dict, facilityName: str,
                     lastUpdateDatetime: str, usrname: str, pw: str):

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
    json.dump(analysisRegJson, sys.stdout, separators=(",", ":"), indent=2)

    # Send json as request to AeroAPI
    r = requests.patch(
        'https://aero-hpc.dev.ngc.dk/wgs-facilities/' +
        facilityName +
        '/qc/analyses',
        json=analysisRegJson,
        verify='/usr/local/share/ca-certificates/CA-NGC.pem',
        headers={
            'Authorization': 'Bearer {}'.format(keycloaktoken)})

    # Print recieved info:
    sys.stdout.write('\nRECIEVED:\nStatus code: ' + str(r.status_code) + '\n')
    sys.stdout.write('Trace ID: ' + r.headers.get('Trace-ID'))
    sys.stdout.write('JSON:\n')
    json.dump(r.json(), sys.stdout, indent=2)


if __name__ == "__main__":

    pass
