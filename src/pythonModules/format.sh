#!/bin/bash
# Applies PEP8 style rules and doctext formatting to sources
# Requires autopep8 and docformatter
read -p "This will reformat source code and doctext in python sources, hit 'y' to confirm or any other key to cancel." -n 1 -r
echo 
if [[ $REPLY =~ ^[Yy]$ ]]
then
    for dir in */
    do
        module=${dir%*/}
        echo "Processing $module"
        echo "1/3: Replacing leading tabs with spaces"
        find $module/$module -name '*.py' ! -type d -exec bash -c 'expand -t 4 "$0" > /tmp/e && mv /tmp/e "$0"' {} \;
        echo "2/3: Applying autopep8 to $module"
        autopep8 -a -a -a -a -r -i $module/$module/
        echo "3/3: Applying docformatter to $module"
        docformatter --in-place --force-wrap --no-blank --pre-summary-newline -r $module/$module/
    done
    echo "Operation completed."
else
    echo "Operation cancelled, no changes made."
fi
