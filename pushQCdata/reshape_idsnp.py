"""
Script for reshaping NBA-2 Germline pipeline QC JSON into something more suitable for
HTTP POST idsnp-check payloads.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import cast

import requests


def reshape(raw_qc: dict) -> dict:
    """Reshape a dict of a qc json into an dict of idsnp-checks for the Aero API

    :param raw_qc: dictioany of qc json
    :type raw_qc: dict
    :return: reshaped dict that fits the idsnp-check format of the Aero API
    :rtype: dict
    """

    # Sanity checks and shortcuts.
    es = raw_qc["metadata"]["experiment_run"]["experiment_samples"][0]
    qc_idsnp = raw_qc["all_idsnp_comparisons"]
    assert len(qc_idsnp) == 1
    dets = list(qc_idsnp.values())[0]["details"]
    assert len(dets["all"]) == (
        len(dets["invalid"]) + len(dets["mismatches"]) + len(dets["matches"])
    )

    # Gather per-site counts.
    sites = {}
    for k, v in dets["all"].items():
        assert k not in sites
        sites[k] = {
            "loc": v["position"][0].strip("chr"),
            "diagnosticSample": {
                "baseCounts": {
                    "A": v["query.A.count"][0],
                    "T": v["query.T.count"][0],
                    "G": v["query.G.count"][0],
                    "C": v["query.C.count"][0],
                    "N": v["query.N.count"][0],
                    "gap": v["query.gap.count"][0],
                },
            },
            "IDSNPSample": {
                "baseCounts": {
                    "A": v["target.A.count"][0],
                    "T": v["target.T.count"][0],
                    "G": v["target.G.count"][0],
                    "C": v["target.C.count"][0],
                    "N": v["target.N.count"][0],
                    "gap": v["target.gap.count"][0],
                },
            }
        }

    payload = {
        "IDSNPSampleName": es["idsnp_sample_name"],
        "details": [{"rsID": k, **v} for k, v in sites.items()],
    }

    return payload


def sendIdsnp(idsnpjson: dict, facilityName: str,
                 analysispermID: str, usrname: str, pw: str) -> None:
    """Send idsnp-checks to Aero API

    :param idsnpjson: _description_
    :type idsnpjson: dict
    :param facilityName: _description_
    :type facilityName: str
    :param analysispermID: _description_
    :type analysispermID: str
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
    json.dump(idsnpjson, sys.stdout, separators=(",", ":"), indent=2)

    # Send json as request to AeroAPI
    r = requests.post(
        'https://aero-hpc.dev.ngc.dk/wgs-facilities/' +
        facilityName +
        '/qc/analyses/' +
        analysispermID +
        '/id-snp-checks',
        json=idsnpjson,
        verify='/usr/local/share/ca-certificates/CA-NGC.pem',
        headers={
            'Authorization': 'Bearer {}'.format(keycloaktoken)})

    # Print recieved info:
    sys.stdout.write('\nRECIEVED:\nStatus code: ' + str(r.status_code) + '\n')
    sys.stdout.write('Trace ID: ' + r.headers.get('Trace-ID'))
    sys.stdout.write('JSON:\n')
    json.dump(r.json(), sys.stdout, indent=2)


if __name__ == "__main__":

    usage = cast(str, __doc__).split("\n\n\n", 1)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=usage[0],
        epilog=usage[1],
    )
    parser.add_argument("qc_input", type=Path, help="Path to input QC JSON")

    args = parser.parse_args()

    with args.qc_input.open("r") as src:
        qc_payload = json.load(src)
        reshaped = reshape(qc_payload)

    json.dump(reshaped, sys.stdout, sort_keys=True, separators=(",", ":"))
