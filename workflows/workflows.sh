#!/bin/bash

CUSTOMER="${CUSTOMER:=sometenant}"
API_URL="${API_URL:=https://api.sview.$CUSTOMER.manage.cto2b.eu}"
DIRECTORY=.
API_TOKEN="${API_TOKEN:=}"


# Post workflow templates
for i in $DIRECTORY/workflow-*.json; do
    # Process $i
    curl -XPUT $API_URL/workflow-templates --header "Content-Type: application/json" --header "Authorization: Bearer $API_TOKEN" -d @$i
done

