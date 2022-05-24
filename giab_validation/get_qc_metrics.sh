#!/bin/bash

# Runs a comparison of a vcf with truth over a bed file
# This script executes happy_validation.sh as a qsub job

# Builtin shell operations
set -o errexit # Exit if something fails
set -u nounset # Exit if undeclared variables

# main script paths
DIR_SCRIPT_BASE=$(dirname "$(readlink -f "$0")")
QSUB_GROUP="ngc_qc"
HAPPY_WRAPPER="${DIR_SCRIPT_BASE}/happy_validation.sh"

# Fixed paths
DIR_ROOT="/ngc"
# reference-location
DIR_REFERENCES_BASE="/ngc/projects/ngc_qc/references"
# singularity-locations
SNG="/cm/local/apps/singularity/current/bin/singularity"
SNG_HAPPY="/ngc/tools/container-images/dev/qc/hap.py_v0.3.8.sif"

# Load anaconda (python library manager)
module load anaconda3/2021.05

# define help function
function help ()
{
	printf "Usage: %s: -r|--reference <hg19/hg38>
	-v|--vcf <file.vcf.gz>
	-q|--qc_json <summary.json> 
	-n|--nist <NA12878/NA24143/etc..> 
	-o|--output <output_folder> 
	-t|--hist <historic file output folder> 
	-m|--mail <mail adress to send results to> 
	[-c|--cleanup <true/false> default is true] 
	[-h|--help]\n" "$(basename "$0")" >&2
    exit
}

# By default, cleanup is turned on, to turn off, add "-c false" in the execution of this script
CLEANUP=true
# Reading input parameters
while [[ "$#" -gt 0 ]]; do
	case "$1" in
        -r|--reference) REFERENCE_GENOME="$2"; [ "$(echo "$2" | cut -c 1)" == "-" ] || [ "$2" == "" ] && help || shift 2;;
        -v|--vcf) FILE_INPUT_VCF="$2"; [ "$(echo "$2" | cut -c 1)" == "-" ] || [ "$2" == "" ] && help || shift 2;;
        -q|--qc_json) QC_JSON="$2"; [ "$(echo "$2" | cut -c 1)" == "-" ] || [ "$2" == "" ] && help || shift 2;;
        -n|--nist) REFERENCE_NIST="$2"; [ "$(echo "$2" | cut -c 1)" == "-" ] || [ "$2" == "" ] && help || shift 2;;
        -o|--output) OUTBASE="$2"; [ "$(echo "$2" | cut -c 1)" == "-" ] || [ "$2" == "" ] && help || shift 2;;
        -t|--hist) HISTORIC="$2"; [ "$(echo "$2" | cut -c 1)" == "-" ] || [ "$2" == "" ] && help || shift 2;;
        -m|--mail) TO_MAIL="$2"; [ "$(echo "$2" | cut -c 1)" == "-" ] || [ "$2" == "" ] && help || shift 2;;
        -c|--cleanup) CLEANUP="$2"; [ "$(echo "$2" | cut -c 1)" == "-" ] || [ "$2" == "" ] && help || shift 2;;
        -h|--help) help;;
        *) help;;
    esac
done

# Save result historic file here
HISTFILE=${HISTORIC}/historic.csv 

# test for vcf input
test ! -f "${FILE_INPUT_VCF}" && merr "missing vcf file, please provide with -v|--vcf"

# Because the folder 3 levels up of the vcf currently holds the sample name and the vcf holds the run name, grab name like this:
VCF_NAME="$(dirname "${FILE_INPUT_VCF}" | xargs dirname | xargs dirname | xargs dirname | xargs basename)"
GLNID="$(basename "${FILE_INPUT_VCF%.endpoint.vcf.gz}")"

# check and set the reference genome
case ${REFERENCE_GENOME} in

	hg19)
		GID="GRCh37"
		FILE_REF_GENOME="${DIR_REFERENCES_BASE}/genomes/${GID}/hs37d5.fa"
		;;

	hg38)
		GID="GRCh38"
		FILE_REF_GENOME="${DIR_REFERENCES_BASE}/genomes/${GID}/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna"
		;;

	*)    # unknown option
		merr "unknown reference genome identifier, please provide with -r|--ref, supported identifiers: hg19, hg38, exiting"
		;;
esac


# check and set the reference nist
case ${REFERENCE_NIST} in

	NA12878)
		DIR_REFERENCES_PATH="${DIR_REFERENCES_BASE}/nist/NA12878_HG001/NISTv3.3.2/${GID}"
		;;

	NA24143)
		DIR_REFERENCES_PATH="${DIR_REFERENCES_BASE}/nist/AshkenazimTrio/HG004_NA24143_mother/NISTv4.2.1/${GID}"
		;;

	NA24149)
		DIR_REFERENCES_PATH="${DIR_REFERENCES_BASE}/nist/AshkenazimTrio/HG003_NA24149_father/NISTv4.2.1/${GID}"
		;;

	NA24385)
		DIR_REFERENCES_PATH="${DIR_REFERENCES_BASE}/nist/AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/${GID}"
		;;

	*)    # unknown option
		merr "unknown nist identifier, please provide with -n|--nist, supported identifiers: NA12878, NA24143, NA24149, NA24385, NA24631, NA24694, NA24695, exiting"
		;;
esac

# other paths, dependant on the selections
GIAB_REF_VCF="${DIR_REFERENCES_PATH}/*.vcf.gz"
# strata used for happy
FILE_BED_HIGHCONF="${DIR_REFERENCES_PATH}/*.bed"

# Making output directories
mkdir -p "${OUTBASE}"

# make subdir for results
OUTFOLDERNAME=${VCF_NAME}
OUT_SAMPLE_DIR="${OUTBASE}/${OUTFOLDERNAME}"
mkdir -p "${OUT_SAMPLE_DIR}" 

# Summary formatting locations
SUMOUT="${OUT_SAMPLE_DIR}/${VCF_NAME}.summary.csv" # The ".summary.csv" part cannot be modified as it is made by hap.py
SUMFORMATTED=${OUT_SAMPLE_DIR}/${VCF_NAME}.formatted.summary.csv

qsub -W group_list=${QSUB_GROUP} -A ${QSUB_GROUP} -l nodes=1:ppn=28,walltime=01:00:00 \
	"${HAPPY_WRAPPER}" \
	-F "-a ${SNG} \
	-b ${DIR_ROOT} \
	-c ${SNG_HAPPY} \
	-d ${FILE_REF_GENOME} \
	-e ${GIAB_REF_VCF} \
	-f ${FILE_INPUT_VCF} \
	-g ${OUT_SAMPLE_DIR} \
	-h ${FILE_BED_HIGHCONF} \
	-i ${DIR_SCRIPT_BASE} \
	-j ${SUMOUT} \
	-k ${SUMFORMATTED} \
	-l ${VCF_NAME} \
	-m ${GLNID} \
	-n ${REFERENCE_NIST} \
	-o ${QC_JSON} \
	-p ${HISTFILE} \
	-q ${TO_MAIL} \
	-r ${CLEANUP}"
