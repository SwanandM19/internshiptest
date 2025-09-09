#!/bin/bash
# Download NAV data and save Scheme Name + NAV as TSV and JSON

URL="https://www.amfiindia.com/spages/NAVAll.txt"
TSV_OUT="nav_data.tsv"
JSON_OUT="nav_data.json"

# Step 1: Download and extract Scheme Name + NAV into TSV
curl -s "$URL" \
  | awk -F';' 'NF >= 5 && $4 != "Scheme Name" {print $4 "\t" $5}' \
  > "$TSV_OUT"

echo "✅ Saved TSV to $TSV_OUT"

# Step 2: Convert TSV → JSON array
awk -F'\t' 'BEGIN {
    print "["
}
{
    # Escape quotes inside scheme names
    gsub(/"/, "\\\"", $1)
    printf "  {\"scheme\": \"%s\", \"nav\": \"%s\"}", $1, $2
    if (NR != 0) {
        if (!seen_first) {
            seen_first=1
        } else {
            printf ","
        }
    }
    print ""
}
END {
    print "]"
}' "$TSV_OUT" > "$JSON_OUT"

echo "✅ Saved JSON to $JSON_OUT"
