from datetime import datetime
import os
import docker
import time
import asyncio
import json
import graphyte
import requests

#os.environ['GRAPHITE_HOSTNAME'] = ''
#os.environ['GRAPHITE_PORT'] = ''
#os.environ['GRAPHITE_prefix'] = ''

graphite_hostname = os.getenv('GRAPHITE_HOSTNAME')
graphite_port = os.getenv('GRAPHITE_PORT')
graphite_prefix = os.environ.get('GRAPHITE_PREFIX')

graphyte.init(graphite_hostname, port=graphite_port, prefix=graphite_prefix)

def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped

def fetch_hostid(container):
    mounts = container.attrs['Mounts']
    for mount in mounts:
        if "btfs" in mount['Source']:
            configfile = mount['Source'] + '/config'
            f = open(configfile, "r")
            jdata = json.loads(f.read())
            hostid = jdata['Identity']['PeerID']

            return hostid

#@background
def fetch_btfs_data(node, hostid, container):
    print(str(container.name))
    timestamp = datetime.timestamp(datetime.now())
    
    uri = "http://" + container.name + ":5001/api/v1/id"

    try:
        response = requests.post(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        bttcaddress = response['BttcAddress']
        response = None
        uri = "http://" + container.name + ":5001/api/v1/cheque/bttbalance?arg=" + bttcaddress
        
        try:
            response = requests.post(uri).json()
        except:
            ConnectionError
            response = None

        if response is not None:
            bttc_addr_btt_balance = round(float(response['balance']) / 1000000000000000000)
            graphyte.send('btt.' + node + '.bttc_chain.bttc_addr_btt_balance', bttc_addr_btt_balance, timestamp=timestamp)


    uri = "https://scan-backend.btfs.io/api/v0/btfsscan/search/node_info?node_id=" +hostid
    print("Querying: " +uri)
    try:
        response = requests.get(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        print(response)
        hostscore = response['data']['score']
        storage_used = response['data']['storage_used']
        graphyte.send('btt.' + node + '.host.storage_used', storage_used, timestamp=timestamp)
        graphyte.send('btt.' + node + '.host.score', hostscore, timestamp=timestamp)

    contracts = container.exec_run("btfs storage contracts stat host")
    
    if contracts is not None:
        print("parsing contract data")
        contract_data = json.loads(contracts.output)
        active_contract_num = contract_data['active_contract_num']
        compensation_paid = contract_data['compensation_paid']
        compensation_outstanding = contract_data['compensation_outstanding']
        graphyte.send('btt.' + node + '.host.active_contract_num', active_contract_num, timestamp=timestamp)
        graphyte.send('btt.' + node + '.host.compensation_paid', compensation_paid, timestamp=timestamp)
        graphyte.send('btt.' + node + '.host.compensation_outstanding', compensation_outstanding, timestamp=timestamp)

client = docker.from_env()
for container in client.containers.list():
    if "btfs" in container.name:
        fetch_btfs_data(container.name, fetch_hostid(container), container)
