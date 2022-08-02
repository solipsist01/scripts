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

#@background
def fetch_btfs_data(container):
    node = container.name
    print(str(container.name))
    timestamp = datetime.timestamp(datetime.now())

### fetch wallet address    
    uri = "http://" + container.name + ":5001/api/v1/id"
    try:
        response = requests.post(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
### fetch bttc onchain balance
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


    ### fetch host score and storage in use
    uri = "http://" + container.name + ":5001/api/v1/storage/stats/info"
    print("Querying: " +uri)
    try:
        response = requests.post(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        hostscore = response['host_stats']['score']
        storage_used = response['host_stats']['storage_used']
        print(hostscore)
        graphyte.send('btt.' + node + '.host.score', hostscore, timestamp=timestamp)
        graphyte.send('btt.' + node + '.host.storage_used', storage_used, timestamp=timestamp)
        

### fetch Contract Data ####
    uri = "http://" + container.name + ":5001/api/v1/storage/contracts/stat?arg=host"
    try:
        response = requests.post(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        print("parsing contract data")
        active_contract_num = response['active_contract_num']
        compensation_paid = response['compensation_paid']
        compensation_outstanding = response['compensation_outstanding']
        graphyte.send('btt.' + node + '.host.active_contract_num', active_contract_num, timestamp=timestamp)
        graphyte.send('btt.' + node + '.host.compensation_paid', compensation_paid, timestamp=timestamp)
        graphyte.send('btt.' + node + '.host.compensation_outstanding', compensation_outstanding, timestamp=timestamp)

### Vault WBTT Balance
    uri = "http://" + container.name + ":5001/api/v1/vault/balance"
    try:
        response = requests.post(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        vault_addr_wbtt_balance = round(float(response['balance']) / 1000000000000000000)
        graphyte.send('btt.' + node + '.bttc_chain.vault_addr_wbtt_balance', vault_addr_wbtt_balance, timestamp=timestamp)

### wbtt wallet balance
    uri = "http://" + container.name + ":5001/api/v1/vault/wbttbalance?arg=" + bttcaddress
    try:
        response = requests.post(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        bttc_addr_wbtt_balance = round(float(response['balance']) / 1000000000000000000)
        graphyte.send('btt.' + node + '.bttc_chain.bttc_addr_wbtt_balance', bttc_addr_wbtt_balance, timestamp=timestamp)

client = docker.from_env()
for container in client.containers.list():
    if "btfs" in container.name:
        fetch_btfs_data(container)
