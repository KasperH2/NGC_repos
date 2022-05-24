# wgsc-cli-giab-validation

Genome in a Bottle quality control report generation. Will use Illumina hap.py algorithm to compare a query vcf of a GIAB sample to a known control reference and output SNP and INDEL calling metrics (precision/recall, etc.)

How to run:
get_qc_metrics.sh \
-r <genome_id> \
-n <GiaB_id> \
-v <gzipped_vcf> \
-q <summary.json> \
-o <out_folder> \
-h <historic_file_out_folder> \
-m <mail_for_results> \
<-c false>

By default vcf and other intermeditate files are removed after run. If those are to be kept, add "-c false" to the command.

Run example
get_qc_metrics.sh \
-r hg38 \
-n NA12878 \
-v "${VCFPATH}" \
-q "${JSONPATH}" \
-o /ngc/projects/ngc_qc/analysis/giab_validation_results \
-h /ngc/projects/ngc_qc/analysis/giab_validation_results \
-m mail@ngc.dk

Output will be a pdf and a raw data csv file. In addition to being placed in the output folder, the results are also sent to the specified mail address.

The csv is in the format (example):
Lab_ID;Sample_name;Run_ID;GiaB_sample;SNP_recall;SNP_precision;SNP_F1;Indel_recall;Indel_precision;Indel_F1;Fraction_at_least_Q30;Fraction_at_least_30x;Mean_coverage;Median_insert_size;Hap.py_run_date
wgs_east;samplename;NA12878;0,99940;0,99515;0,99727;0,98933;0,99042;0,98988;0,65900;0,70683;32,54407;444,00000;14-01-22

It also saves the csv results of all runs in a historic.csv file as long as the runs' sample id, run id and GiaB id are unique. 
 
After a succesful run, the qsub logfiles can be removed by running clearLog.sh

The get_qc_metrics.sh script contains jobsubmitting of happy_validation.sh
THEN
happy_validation.sh 
RUNS
hap.py 
THEN 
summary_formatter.py 
THEN 
pdfgeneration/generate_qc_report.sh
WHICH RUNS 
pdfgeneration/generate_qc_report.py
