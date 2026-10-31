#!/bin/bash
# Stage 1 for all books: lines + page labels -> mcq-portal/work/
cd /home/shankar/pup/ghatnachakra
W=mcq-portal/work
for pair in "polity:Preview_Indian_Polity_and_Governance_Part_4_2026_26118_C_E_Book.pdf" "history:Preview_Indian_History_Part_2_2026_26116_C_E_Book_Merged.pdf" "geography:Preview_General_Geography_Part_3_2026_26117_C_E_Book_combined.pdf" "science:Preview_General_Science_Part_7_2026_26121_C_E_Book_combined_1.pdf" "bpsc:Preview_BPSC_General_Studies_2026_2616_N_E_Book_2026.pdf"; do
  n=${pair%%:*}; f=${pair#*:}
  [ -s $W/lines/$n.json ] || python3 mcq-portal/tools/extract_lines.py "$f" $W/lines/$n.json
  [ -s $W/labels/$n.json ] || python3 mcq-portal/tools/page_labels.py "$f" $W/labels/$n.json
  echo "done $n"
done
echo ALLDONE
