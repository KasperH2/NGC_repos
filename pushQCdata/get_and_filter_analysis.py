
"""
Script for reshaping NBA-2 Germline pipeline QC JSON into something more suitable for
HTTP POST analyses payloads.

Input: csv file with paths of sample json files in first column of each row. Extra columns are ignored.
Output: reshaped json file for each sample. Instead of saving, they can be directly sent as request with option -r
"""

import argparse
import json
import sys

import requests


def getAnalysis(analysisPermID: str,
                        facilityName: str, usrname: str, pw: str) -> dict:
    """GET qc/analysis for a given analysisPermID and filter out keys that is needed for further bioinformatic processing

    :param analysisPermID: _description_
    :type analysisPermID: str
    :param facilityName: _description_
    :type facilityName: str
    :param usrname: _description_
    :type usrname: str
    :param pw: _description_
    :type pw: str
    :return: _description_
    :rtype: dict
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
    sys.stdout.write('\n'+analysisPermID+'\n')

    geturl = 'https://aero-hpc.dev.ngc.dk/wgs-facilities/' + \
        facilityName + '/qc/analyses/' + analysisPermID
    # Send json as request to AeroAPI
    r = requests.get(
        geturl,
        verify='/usr/local/share/ca-certificates/CA-NGC.pem',
        headers={
            'Authorization': 'Bearer {}'.format(keycloaktoken)})

    # Print recieved info:
    sys.stdout.write('\nRECIEVED:\nStatus code: ' + str(r.status_code) + '\n')
    sys.stdout.write('Trace ID: ' + r.headers.get('Trace-ID'))
    sys.stdout.write('JSON:\n')
    json.dump(r.json(), sys.stdout, indent=2)

    return r.json()


def filterAnalysis(analysisjson: dict) -> dict:
    # Get relevant regID from sampleID
    aj = analysisjson
    payload = {}

    # At pipeline level, for each pipelineRun, create a key with nested 'sample
    for plr in aj['pipelineRuns']:
        payload[plr['pipelineID']] = {
            'pipelineID': plr['pipelineID']
        }
        # At sample level
        for smplr in plr['samples']:
            smplsubdict = {
                "subjectID": smplr['subjectID'],
                "sampleName": smplr['sampleName'],
                "registrationID": "",
                "evalStatus": aj['evalStatus']
            }
            if 'samples' not in payload[plr['pipelineID']]:
                payload[plr['pipelineID']]['samples'] = [smplsubdict]
            else:
                payload[plr['pipelineID']]['samples'].append(smplsubdict)

    json.dump(payload, sys.stdout, indent=2)

    return payload


if __name__ == "__main__":

    usage = __doc__.split("\n\n\n", 1)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=usage[0],
        epilog=usage[1],
    )
    parser.add_argument("analysisPermID", type=str,
                        help="analysisPermID on Aero API")
    parser.add_argument("facilityName", type=str,
                        help="facilityName")
    parser.add_argument("usrname", type=str,
                        help="FreeIPA username")
    parser.add_argument("pw", type=str,
                        help="FreeIPA password")

    args = parser.parse_args()

    analysisjson = getAnalysis(args.analysisPermID, args.facilityName, args.usrname, args.pw)
    filtered = filterAnalysis(analysisjson)

    json.dump(filtered, sys.stdout, sort_keys=True, separators=(",", ":"))
