#!/bin/bash

# Example Usage
# ./run.sh --frequency 10 --debug true --sendopsgenie false --configfilename config.json.demo
frequency=${frequency:-30}
debug=${debug:-true}
sendopsgenie=${sendopsgenie:-false}
sendpagerduty=${sendpagerduty:-false}
configfilename=${configfilename:-config.json}

# credits - https://brianchildress.co/named-parameters-in-bash/
while [ $# -gt 0 ]; do
   if [[ $1 == *"--"* ]]; then
    param="${1/--/}"
    declare $param="$2"
    # echo $1 $2 // Optional to see the parameter:value result
   fi
  shift
done

if [[ "$debug" == "true" ]]; then
  debug="--debug"
else
  debug=""
fi

# if want to send to pagerduty then validate the the url and opsgenie
if [[ "$sendpagerduty" == "true" ]]; then
  CREDS_FILE=creds.json
  if ! [ -f "$CREDS_FILE" ]; then
    echo "ERROR: missing $CREDS_FILE"
    exit 1
  fi
  sendpagerduty="--sendpagerduty"
  PAGERDUTY_API_URL="--pdurl $(cat $CREDS_FILE | jq -r '.PAGERDUTY_API_URL')"
  PAGERDUTY_INTEGRATION_KEY="--pdkey $(cat $CREDS_FILE | jq -r '.PAGERDUTY_INTEGRATION_KEY')"
else
  sendpagerduty=""
fi

# if want to send to opsgenie then validate the the url and opsgenie
if [[ "$sendopsgenie" == "true" ]]; then
  CREDS_FILE=creds.json
  if ! [ -f "$CREDS_FILE" ]; then
    echo "ERROR: missing $CREDS_FILE"
    exit 1
  fi
  sendopsgenie="--sendopsgenie"
  OPSGENIE_API_URL="--ogurl $(cat $CREDS_FILE | jq -r '.OPSGENIE_API_URL')"
  OPSGENIE_API_TOKEN="--ogtoken $(cat $CREDS_FILE | jq -r '.OPSGENIE_API_TOKEN')"
else
  sendopsgenie=""
fi

echo "================================================="
echo "running monitor"
echo ""
echo "LOOP FREQUENCY         : $frequency"
echo "DEBUG SETTING          : $debug"
echo "SEND OPSGENIE SETTING  : $sendopsgenie"
echo "SEND PAGERDUTY SETTING : $sendpagerduty"
echo "OPSGENIE API_URL       : $OPSGENIE_API_URL"
echo "PAGERDUTY_API_URL      : $PAGERDUTY_API_URL"
echo "MONITORS CONFIG FILE   : $configfilename"
echo "================================================="

python3 monitoring.py \
  -f $frequency \
  -c $configfilename \
  $debug \
  $sendopsgenie \
  $OPSGENIE_API_URL \
  $OPSGENIE_API_TOKEN \
  $sendpagerduty \
  $PAGERDUTY_API_URL \
  $PAGERDUTY_INTEGRATION_KEY
