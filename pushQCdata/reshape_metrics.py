"""
Script for reshaping NBA-2 Germline pipeline QC JSON into something more suitable for
HTTP POST metrics payloads.
"""
import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Callable

import requests


def reshape(raw_qc: dict) -> dict:
    """Reshape a dict of a qc json into an dict of metrics for the Aero API

    :param raw_qc: dictioany of qc json
    :type raw_qc: dict
    :return: reshaped dict that fits the metrics format of the Aero API
    :rtype: dict
    """
    # shortcuts
    er = raw_qc["metadata"]["experiment_run"]
    es = er["experiment_samples"][0]

    qcs = raw_qc["germline_full"]["metrics"]["samples"][0]["QC_summary"]
    qc_idsnp = raw_qc["all_idsnp_comparisons"]

    assert len(qc_idsnp) == 1

    def adj_pct_float(x): return float(Decimal(str(x)) * 100)
    def adj_m_float(x): return int(Decimal(str(x)) * 1000000)

    def to_array(
        x_dps: str,
        x_func: Callable,
        y_dps: str,
        y_func: Callable,
        sep: str = ";",
    ) -> dict:
        x_split = x_dps.split(sep)
        y_split = y_dps.split(sep)
        x_conv = [x_func(i) for i in x_split]
        y_conv = [y_func(i) for i in y_split]
        assert len(x_conv) == len(y_conv), (
            "Unequal number of items in X-axis and Y-axis:"
            f" {len(x_conv)} vs {len(y_conv)}"
        )
        return dict(zip(x_conv, y_conv))

    payload = {
        "sampleLevel": {
            "labels": {
                "seqRunID": er["run_id"][0],
                "readType": er["read_type"][0],
                "pipelineID": es["flow_id"],
                "flowcellID": er["flowcell_id"][0],
                "flowcellType": er["flowcell_type"][0],
                "libraryID": es["library_id"],
                "registrationID": es["registration_id"],
                "labID": es["lab_id"],
                "subjectID": es["subject_id"],
                "ngcSubjectID": es["ngc_subject_id"],
                "protocolID": es["protocol_id"],
                "sampleID": es["registered_sample_id"],
                "sampleName": es["sample_name"],
            },
            "qcValues": {
                "pctDuplicates": adj_pct_float(qcs["pct_duplicates"]),
                "pctQ30": adj_pct_float(qcs["pct_q30"]),
                "medianInsertSize": int(qcs["median_insert_size"]),
                "nReadsMapped": adj_m_float(qcs["m_reads_mapped"]),
                "meanCov": float(qcs["mean_coverage"]),
                "sdCov": float(qcs["sd_coverage"]),
                "pctCov10x": adj_pct_float(qcs["pct_10x"]),
                "pctCov20x": adj_pct_float(qcs["pct_20x"]),
                "pctCov30x": adj_pct_float(qcs["pct_30x"]),
                "nSNPsAll": adj_m_float(qcs["M_nSNPs_all"]),
                "pctSNPsKnown": adj_pct_float(qcs["pct_SNPs_known"]),
                "pctSNPsNovel": adj_pct_float(qcs["pct_SNPs_novel"]),
                "ratioTiTvAll": float(qcs["tiTvRatio_all"]),
                "ratioTiTvKnown": float(qcs["tiTvRatio_known"]),
                "ratioTiTvNovel": float(qcs["tiTvRatio_novel"]),
                "ratioHetHomAll": float(qcs["hetHomRatio_all"]),
                "ratioHetHomKnown": float(qcs["hetHomRatio_known"]),
                "ratioHetHomNovel": float(qcs["hetHomRatio_novel"]),
                "pctMskRegions": float(qcs["msk_pct_regions"]),
                "pctMskHomozygousSites": float(qcs["msk_pct_homozygous_sites"]),
                "meanPctMskMinorAllele": adj_pct_float(qcs["msk_meanpct_minorallele"]),
                "insertSize": to_array(
                    qcs["insert_size_value"],
                    lambda x: int(x),
                    qcs["insert_size_frequency"],
                    lambda y: int(y),
                ),
                "altFreqAll": to_array(
                    qcs["alt_freq_all_value"],
                    lambda x: float(x),
                    qcs["alt_freq_all_frequency"],
                    lambda y: int(y),
                ),
            },
        }
    }

    return payload


def sendMetrics(metricsjson: dict, facilityName: str, analysispermID: str,
                pipelinepermID: str, pipelinerunpermID: str, usrname: str, pw: str) -> None:
    
    """Send metrics to Aero API

    :param metricsjson: _description_
    :type metricsjson: dict
    :param facilityName: _description_
    :type facilityName: str
    :param analysispermID: _description_
    :type analysispermID: str
    :param pipelinepermID: _description_
    :type pipelinepermID: str
    :param pipelinerunpermID: _description_
    :type pipelinerunpermID: str
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
    json.dump(metricsjson, sys.stdout, separators=(",", ":"), indent=2)

    # Send json as request to AeroAPI
    posturlstart = 'https://aero-hpc.dev.ngc.dk/wgs-facilities/' + \
        facilityName + '/qc/analyses/' + analysispermID
    posturlend = '/metrics?pipelinePermID=' + pipelinepermID + \
        '&pipelineRunPermID=' + pipelinerunpermID
    posturl = posturlstart + posturlend
    r = requests.post(
        posturl,
        json=metricsjson,
        verify='/usr/local/share/ca-certificates/CA-NGC.pem',
        headers={
            'Authorization': 'Bearer {}'.format(keycloaktoken)})

    # Print recieved info:
    sys.stdout.write('\nRECIEVED GET JSON:\nStatus code: ' +
                     str(r.status_code) + '\n')
    sys.stdout.write('Trace ID: ' + r.headers.get('Trace-ID'))
    sys.stdout.write('JSON:\n')
    json.dump(r.json(), sys.stdout, indent=2)


if __name__ == "__main__":

    usage = __doc__.split("\n\n\n", 1)

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

