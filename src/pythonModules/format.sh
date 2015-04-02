#!/bin/bash
# Applies PEP8 style rules and doctext formatting to sources
# Requires autopep8 and docformatter
read -p "This will reformat source code and doctext in python sources, hit 'y' to confirm or any other key to cancel." -n 1 -r
echo 
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "1/2: Applying autopep8 to meteorpi_model, meteorpi_fdb"
    autopep8 -a -a -a -a -r -i meteorpi_model/meteorpi_model/ meteorpi_fdb/meteorpi_fdb/
    echo "2/2: Applying docformatter to meteorpi_model, meteorpi_fdb"
    docformatter --in-place --force-wrap --no-blank --pre-summary-newline -r meteorpi_model/meteorpi_model/ meteorpi_fdb/meteorpi_fdb/
    echo "Operation completed."
else
    echo "Operation cancelled, no changes made."
fi
