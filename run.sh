#!/bin/bash

# Example Usage
# ./run.sh --frequency 10 --debug true --sendopsgenie false --configfilename config.json.demo
frequency=${frequency:-30}
debug=${debug:-true}
sendopsgenie=${sendopsgenie:-false}
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

# if want to send to opsgenie then validate the the url and opsgenie
if [[ "$sendopsgenie" == "true" ]]; then
  CREDS_FILE=creds.json
  if ! [ -f "$CREDS_FILE" ]; then
    echo "ERROR: missing $CREDS_FILE"
    exit 1
  fi
  sendopsgenie="--sendopsgenie"
  OPSGENIE_API_URL="-u $(cat $CREDS_FILE | jq -r '.OPSGENIE_API_URL')"
  OPSGENIE_API_TOKEN="-t $(cat $CREDS_FILE | jq -r '.OPSGENIE_API_TOKEN')"
else
  sendopsgenie=""
fi

echo "================================================="
echo "running monitor"
echo ""
echo "LOOP FREQUENCY        : $frequency"
echo "DEBUG SETTING         : $debug"
echo "SEND OPSGENIE SETTING : $sendopsgenie"
echo "OPSGENIE API_URL      : $OPSGENIE_API_URL"
echo "CONFIG FILE           : $configfilename"
echo "================================================="

python3 monitoring.py $OPSGENIE_API_URL $OPSGENIE_API_TOKEN -f $frequency $debug $sendopsgenie -c $configfilename
