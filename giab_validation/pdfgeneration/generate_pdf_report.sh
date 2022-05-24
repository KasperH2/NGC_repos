#!/bin/bash
 
# Builtin shell operations
set -o errexit # Exit if something fails
set -u nounset # Exit if undeclared variables

# This script is executed by happy_vaidation.sh

while getopts ":s:o:m:" arg; do
    case $arg in
        s) FILE_SAMPLE=$OPTARG;;
		o) DIR_OUTPUT=$OPTARG;;
		m) TO_MAIL=$OPTARG;; 
        *)
          # Print helping message for providing wrong options
          echo "Usage: $0 [-s sample path] [-o output folder] [-m mailaddress to send results to]" >&2
          exit 1 ;; # Terminate from the script
    esac
done

DIR_SCRIPT_BASE=$(dirname "$(readlink -f "$0")") # This will refer to the folder where this script is located
# Fixed paths
DIR_ROOT="/ngc" 
SNG="/cm/local/apps/singularity/current/bin/singularity"
SNG_XELATEX="/ngc/tools/container-images/dev/qc/latex_2021_11_22.sif" #"/ngc/tools/container-images/dev/other_software/latex_2021_11_22.sif"

#Locate latex file generation script
REPORT_SCRIPT="${DIR_SCRIPT_BASE}/generate_pdf_report.py"
# Getting report template
REPORT_TEMPLATE="${DIR_SCRIPT_BASE}/happy_pdf_report_template.tex"

# Making endresults folder
END_DIR=${DIR_OUTPUT}/endresults
mkdir -p "${END_DIR}"  

# generate the report as tex file, this will create a subfolder in the END_DIR folder
python "${REPORT_SCRIPT}" -s "${FILE_SAMPLE}" -t "${REPORT_TEMPLATE}" -o "${END_DIR}"

FILE_NAME_EXT=$(basename "$FILE_SAMPLE")
FILE_NAME=${FILE_NAME_EXT%.csv}  
FILE_REPORT_TEX="${END_DIR}/${FILE_NAME}.tex"

# compile latex file to pdf file
if [ -f "${FILE_REPORT_TEX}" ]; then
	
	info "running pdf generation from tex file:"
	echo "${FILE_REPORT_TEX}"    

	${SNG} exec -B ${DIR_ROOT}:${DIR_ROOT} ${SNG_XELATEX} latexmk -pdf -interaction=nonstopmode -output-directory="${END_DIR}" "${FILE_REPORT_TEX}"

else

	echo "Failed to generate pdf report, no tex file found at:"
	echo "${FILE_REPORT_TEX}"    

fi

# Save csv to same folder and cleanup. DotDecimalseperator file is saved in case of future use. 
cp "${FILE_SAMPLE}" "${END_DIR}"/"${FILE_NAME}"_dotDecimalSep.csv
cp "${FILE_SAMPLE%.csv}"_danishComma.csv "${END_DIR}"/"${FILE_NAME}".csv
rm "${END_DIR}"/"${FILE_NAME}".{tex,aux,log,fdb_latexmk,fls}

# Mail endresults
FROM_MAIL="no-reply@ngc.dk" 
# Attachments
ATT1=${END_DIR}/${FILE_NAME}.csv
ATT2=${END_DIR}/${FILE_NAME}.pdf

# For log:
echo
echo "Sending mail with:"
echo mail -r "${FROM_MAIL}" -s "GiaB_validation_results" -a "${ATT1}" -a "${ATT2}" "${TO_MAIL}" "<" "${ATT1}"  
echo

# The < must be given, as it defines the email body
mail -r "${FROM_MAIL}" -s "GiaB_validation_results" -a "${ATT1}" -a "${ATT2}" "${TO_MAIL}" < "GiaB results attached"