import argparse
import json
import requests
import time
import os
from datetime import datetime
from multiprocessing import Process

debugOutput=False
sendopsgenie=False
sendpagerduty=False
alertFile='results/alert.csv'

def debugMessage(message):
    if debugOutput:
        print(message)

def readConfig(configfilename):
    # load values from the config file
    global data
    f = open(configfilename,)
    data = json.load(f)
    f.close() 

    debugMessage("DEBUG - readConfig() =====================================================")
    debugMessage("DEBUG - readConfig() monitoringFrequencySeconds : " + monitoringFrequencySeconds)
    debugMessage("DEBUG - readConfig() debugOutput                : " + str(debugOutput))
    debugMessage("DEBUG - readConfig() sendopsgenie               : " + str(sendopsgenie))
    debugMessage("DEBUG - readConfig() sendpagerduty              : " + str(sendpagerduty))
    if opsgenieApiUrl:
        debugMessage("DEBUG - readConfig() opsgenieApiUrl             : " + opsgenieApiUrl)
    if pagerDutyApiUrl:
        debugMessage("DEBUG - readConfig() pagerDutyApiUrl            : " + pagerDutyApiUrl)
    debugMessage("DEBUG - readConfig() configfilename             : " + configfilename)
    debugMessage("DEBUG - readConfig() =====================================================")
    debugMessage("DEBUG - readConfig() enabled monitors:")
    for url in data['monitors']:
        if url['enabled'] == "true":
            debugMessage('                       id: ' + url['id'] + ', command: ' + url['command'] + ', url: ' + url['url'] + ', target: ' + url['target'])
    debugMessage("DEBUG - readConfig() =====================================================")

def createAlertFile():
    f = open(alertFile, "w")
    f.write("time,id,type,environment,service,message\n")
    f.close()

def sendAlert(id,alertType,environment,service,alertMessage):
    # https://developer.pagerduty.com/docs/events-api-v2/overview/
    alertDateTime=str(datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
    # write alert to file
    f = open(alertFile, "a")
    f.write(alertDateTime + ',' + id + ',' + alertType + ',' + environment + ',' + service + ',' + alertMessage+'\n')
    f.close()

    if sendpagerduty:
        summary=environment+'-'+service + '-' + str(datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
        source="simple-monitoring-tool"
        component=environment+'-'+service
        group=""
        theclass=""
        routing_key=pagerdutyApiToken
        event_action="trigger"
        dedup_key=""

        if alertType=='state':
            severity="critical"
        elif alertType=='health':
            severity="error"
        else:   # performance
            severity="warning"

        alertHeaders = {'content-type': 'application/json' }
        alertBodyString = ' { "payload": { \
            "summary":"' + summary + '", \
            "severity":"' + severity + '", \
            "source":"' + source + '", \
            "component":"' + component + '", \
            "group":"' + group + '", \
            "class":"' + theclass + '"}, \
            "routing_key":"' + routing_key + '", \
            "event_action":"' + event_action + '", \
            "dedup_key":"' + dedup_key + '"}'
        alertBodyJson = json.loads(alertBodyString)

        debugMessage("DEBUG - sendAlert() - pagerDutyApiUrl: " + pagerDutyApiUrl)
        debugMessage("DEBUG - sendAlert() - alertBody: " + json.dumps(alertBodyJson))
        debugMessage("DEBUG - sendAlert() - alerteaders: " + str(alertHeaders))
        alertResponse = requests.post(pagerDutyApiUrl, data=json.dumps(alertBodyJson), headers=alertHeaders)
        debugMessage("DEBUG - sendAlert() - alertResponse.text: " + str(alertResponse.text))
        debugMessage("DEBUG - sendAlert() - alertResponse.status_code: " + str(alertResponse.status_code))
    else:
        debugMessage("DEBUG - sendAlert() - Skipping PagerDuty call")

    if sendopsgenie:
        # call Opsgenie API - https://docs.opsgenie.com/docs/alert-api
        entity=environment+'-'+service
        alias=alertType + '-' + entity + '-' + str(datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
        message=alertType + ' Issue in environment: ' + environment + ' on: ' + alias
        description=alertMessage + ' in environment: ' + environment + ' on: ' + alias

        if alertType=='state':
            priorty='P1'
        elif alertType=='health':
            priorty='P2'
        else:   # performance
            priorty='P3'

        alertBodyString = ' { "message": "' + message + '", \
            "alias":"' + alias + '", \
            "description":"' + description + '", \
            "details": { "id":"' + id + '","environment":"' + environment + '","service":"' + service + '" }, \
            "entity":"' + entity + '", \
            "priorty":"' + priorty + '"}'
        alertBodyJson = json.loads(alertBodyString)
        alertHeaders = {'content-type': 'application/json', 'Authorization': 'GenieKey ' + opsgenieApiToken }

        debugMessage("DEBUG - sendAlert() - opsgenieApiUrl: " + opsgenieApiUrl)
        debugMessage("DEBUG - sendAlert() - alertBody: " + json.dumps(alertBodyJson))
        debugMessage("DEBUG - sendAlert() - alerteaders: " + str(alertHeaders))
        alertResponse = requests.post(opsgenieApiUrl, data=json.dumps(alertBodyJson), headers=alertHeaders)
        debugMessage("DEBUG - sendAlert() - alertResponse.text: " + str(alertResponse.text))
        debugMessage("DEBUG - sendAlert() - alertResponse.status_code: " + str(alertResponse.status_code))
    else:
        debugMessage("DEBUG - sendAlert() - Skipping Opsgenie call")


def perform_check(id,type,environment,service,command,url,target):
    alert=False
    alertMessage=''

    if type == 'state':
        try:
            debugMessage('DEBUG - perform_check() - Checking ' + id + ' type = ' + type + ' command: ' + command)
            exit_code=os.system(command)
            debugMessage('DEBUG - perform_check() - ' + id + ' command: ' + command + ' --> got exit code = ' + str(exit_code))
            if exit_code != 0:
                alert=True
                alertMessage='[' + command +'] got response code: ' + str(r.status_code)
        except:
            alert=True
            alertMessage='[' + command +'] state check not successful'
            debugMessage('DEBUG - perform_check() - ' + id + ' command: ' + command + ' --> state check not successful')

    else:
        try:
            debugMessage('DEBUG - perform_check() - Checking ' + id + ' type = ' + type + ' url: ' + url)
            r = requests.get(url)
            debugMessage('DEBUG - perform_check() - ' + id + ' url: ' + url + ' --> got status_code = ' + str(r.status_code))
            if r.status_code != 200:
                alert=True
                alertMessage='[' + url +']  got response code: ' + str(r.status_code)
            
            # performance check
            if type == 'performance':
                responseSeconds=r.elapsed.microseconds/1000000
                debugMessage('DEBUG - perform_check() -  ' + id + ' url: ' + url + ' --> response seconds ' + str(responseSeconds) + ' target: ' + str(target))
                if float(responseSeconds) > float(target):
                    alert=True
                    alertMessage='[' + url +'] seconds taken: [' + str(responseSeconds) + '] target: [' + str(target) + ']'
        except:
            alert=True
            alertMessage='[' + url +'] Failed to reach URL'
            debugMessage('DEBUG - perform_check() - ' + id + ' url: ' + url + ' --> failed to reach URL')

    if alert:
        sendAlert(id,type,environment,service,alertMessage)

# main processing logic that will start the evaluation and loop to test if it is complete
def process(configfilename):
    createAlertFile()
    readConfig(configfilename)

    global procs
    procs = []

    # Loop continuously every monitoringFrequencySeconds
    starttime=time.time() 
    while True: 
        debugMessage("DEBUG - process() - Start monitoring " + str(datetime.now().strftime("%m/%d/%Y %H:%M:%S"))) 

        for row in data['monitors']:
            if row['enabled'] == 'true':
                id=row['id']
                type=row['type']
                environment=row['environment']
                service=row['service']
                command=row['command']
                url=row['url']
                target=row['target']

                debugMessage('DEBUG - process() - processing monitor: ' + id)
                proc = Process(target=perform_check, args=(id,type,environment,service,command,url,target))
                procs.append(proc)
                proc.start()

        # complete the processes
        for proc in procs:
            proc.join()

        # EXIT FOR TESTING
        #break

        # wait
        waitTime = float(monitoringFrequencySeconds)
        debugMessage('DEBUG - process() - waiting ' + str(waitTime) + ' seconds')
        time.sleep(waitTime- ((time.time() - starttime) % waitTime))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('-f','--frequency', required=True, help='monitoring frequency in seconds')
    ap.add_argument('-c','--configfilename', help='montoring config filename', default='config.json')
    ap.add_argument('--debug', help='add for more logging detail', action='store_true', default=False)
    ap.add_argument('--sendopsgenie', help='make opsgenie call', action='store_true', default=False)
    ap.add_argument('--ogurl', help='opsgenie api url')
    ap.add_argument('--ogtoken', help='opsgenie api token')
    ap.add_argument('--sendpagerduty', help='make sendpagerduty call', action='store_true', default=False)
    ap.add_argument('--pdurl', help='pagerduty api url')
    ap.add_argument('--pdkey', help='pagerduty integration key')
    args = vars(ap.parse_args())
    
    opsgenieApiUrl = args['ogurl']
    opsgenieApiToken = args['ogtoken']
    pagerDutyApiUrl = args['pdurl']
    pagerdutyApiToken = args['pdkey']
    monitoringFrequencySeconds = args['frequency']

    print(args["sendopsgenie"])
    if args["sendopsgenie"]:
        sendopsgenie = True
    if args["sendpagerduty"]:
        sendpagerduty = True
    if args["debug"]:
        debugOutput = True

    process(args["configfilename"])