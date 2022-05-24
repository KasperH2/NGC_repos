#!/bin/bash
# (c) 2022 The Danish National Genome Center / Nationalt Genom Center
# Author: KHO@NGC.DK
# Last updated: 21-03-2022 by KHO@NGC.DK
 
# Runs a comparison of a vcf with truth over a bed file
# This script is executed by get_qc_metrics.sh and executes happy_validation.sh as a qsub job

# Builtin shell operations
set -o errexit # Exit if something fails
set -u nounset # Exit if undeclared variables

# read arguments
while getopts ":a:b:c:d:e:f:g:h:i:j:k:l:m:n:o:p:q:r:s:" arg; do
    case $arg in
        a) SNG=$OPTARG;;
        b) DIR_ROOT=$OPTARG;;
        c) SNG_HAPPY=$OPTARG;;
        d) FILE_REF_GENOME=$OPTARG;;
        e) GIAB_REF_VCF=$OPTARG;;
        f) FILE_INPUT_VCF=$OPTARG;;
        g) DIR_OUTPUT=$OPTARG;;
        h) FILE_BED_STRATA=$OPTARG;;
        i) DIR_SCRIPT_BASE=$OPTARG;;
        j) SUMOUT=$OPTARG;;
        k) SUMFORMATTED=$OPTARG;;
        l) SAMPLE_NAME=$OPTARG;;
        m) GLNID=$OPTARG;;
        n) REFERENCE_NIST=$OPTARG;;
        o) QC_JSON=$OPTARG;;
        p) HISTFILE=$OPTARG;;
        q) TO_MAIL=$OPTARG;;
        r) CLEANUP=$OPTARG;;
        *)
            # exit if providing wrong options
            exit 1 ;; # Terminate from the script
    esac
done

# Logging information, will be output by qsub into logfile where the get_qc_metrics.sh 
echo
echo    "Sending to mail: " "${TO_MAIL}" 
echo 
echo    "Happy was given the following inputs:"
echo 	root: "${DIR_ROOT}"
echo
echo 	sng_happy: "${SNG_HAPPY}"
echo
echo 	ref genome: "${FILE_REF_GENOME}"
echo
echo 	GiaB ref vcf: "${GIAB_REF_VCF}"
echo
echo 	input vcf: "${FILE_INPUT_VCF}"
echo
echo	output dir: "${DIR_OUTPUT}" 
echo
echo	bed file: "${FILE_BED_STRATA}"
echo
echo	current dir: "${DIR_SCRIPT_BASE}"
echo
echo	happy out file: "${SUMOUT}"
echo
echo	formatted happy outfile: "${SUMFORMATTED}"
echo
echo	file input base "${GLNID}"
echo
echo	sample name: "${SAMPLE_NAME}"
echo
echo	GIAB ref: "${REFERENCE_NIST}"
echo
echo	QC summary json: "${QC_JSON}"

# run happy, happy must have the prefix for output files defined, therefore: ${DIR_OUTPUT}/${SAMPLE_NAME}
"${SNG}" exec -B "${DIR_ROOT}":"${DIR_ROOT}" "${SNG_HAPPY}" /opt/hap.py/bin/hap.py "${GIAB_REF_VCF}" "${FILE_INPUT_VCF}" -f "${FILE_BED_STRATA}" -r "${FILE_REF_GENOME}" -o "${DIR_OUTPUT}"/"${SAMPLE_NAME}"

# Load python anaconda module
module load anaconda3/2021.05

# Format the resulting summary file from hap.py
python "$DIR_SCRIPT_BASE"/summary_formatter.py -i "${SUMOUT}" -o "${SUMFORMATTED}" -r "${GLNID}" -g "${REFERENCE_NIST}" -q "${QC_JSON}" -s "${SAMPLE_NAME}" -c "${HISTFILE}"  

# Prepare excel ready format of formatted summary file
sed 's/,/;/g' "${SUMFORMATTED}" > "${DIR_OUTPUT}"/temp.csv # Replace , with ;
sed '2s/\./,/g' "${DIR_OUTPUT}"/temp.csv > "${SUMFORMATTED%.csv}"_danishComma.csv # Replace . with , but only in 2nd line. 
rm "${DIR_OUTPUT}"/temp.csv

# Create pdf result file with latex, -o defines output folder, -m defines which ngc mail to send the pdf and the formatted csv file
bash "${DIR_SCRIPT_BASE}"/pdfgeneration/generate_pdf_report.sh -s "${SUMFORMATTED}" -o "${DIR_OUTPUT}" -m "${TO_MAIL}"

# Cleanup of vcf files and other intermediate files
if [  "${CLEANUP}" == true ] 
then
    if [ ${#DIR_OUTPUT} -gt 0 ]    
    then
        echo "Removed vcf and other temp files from:"
        echo "${DIR_OUTPUT}"/
        rm  "${DIR_OUTPUT}"/*.* 
    else
        echo "Did not remove temp files"
    fi
else
    echo "Did not remove temp files"
fi