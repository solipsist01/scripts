import os
import docker
import requests
import graphyte
import json
import asyncio
from datetime import datetime
import time


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

@background
def fetch_btfs_data(container):
    node = container.name
    print("Getting contract data from: " + node)
    contracts = container.exec_run("btfs storage contracts stat host")
    print("Getting storage stats from: " + node)
    storage = container.exec_run("btfs storage stats info")
    print("Getting node IDs from: " + node)
    btfsid = container.exec_run("btfs id")
    print("Getting cheque data from: " + node)
    btfscheques = container.exec_run("btfs cheque stats")

    contract_data = json.loads(contracts.output)
    storage_data = json.loads(storage.output)
    btfsid_data = json.loads(btfsid.output)
    btfscheques_data = json.loads(btfscheques.output)
    active_contract_num = contract_data['active_contract_num']
    compensation_paid = contract_data['compensation_paid']
    compensation_outstanding = contract_data['compensation_outstanding']
    timestamp = datetime.timestamp(datetime.now())
    storage_used = storage_data['host_stats']['storage_used']
    score = storage_data['host_stats']['score']
    hostid = btfsid_data['ID']
    cheques_uncashed_amount = float(btfscheques_data['total_received_uncashed']) / 1000000000000000000
    cheques_total_received_count = float(btfscheques_data['total_received_count'])

    uri = "https://scan-backend.btfs.io/api/v1/node/addr_info?id=" +hostid

    try:
        response = requests.get(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        
        bttc_addr_btt_balance = round(float(response['data']['bttc_addr_btt_balance']) / 1000000000000000000)
        bttc_addr_wbtt_balance = round(float(response['data']['bttc_addr_wbtt_balance']) / 1000000000000000000)
        vault_addr_btt_balance = round(float(response['data']['vault_addr_btt_balance']) / 1000000000000000000)
        vault_addr_wbtt_balance = round(float(response['data']['vault_addr_wbtt_balance']) / 1000000000000000000)
        graphyte.send('btt.' + node + '.bttc_chain.bttc_addr_btt_balance', bttc_addr_btt_balance, timestamp=timestamp)
        graphyte.send('btt.' + node + '.bttc_chain.bttc_addr_wbtt_balance', bttc_addr_wbtt_balance, timestamp=timestamp)
        graphyte.send('btt.' + node + '.bttc_chain.vault_addr_btt_balance', vault_addr_btt_balance, timestamp=timestamp)
        graphyte.send('btt.' + node + '.bttc_chain.vault_addr_wbtt_balance', vault_addr_wbtt_balance, timestamp=timestamp)

    graphyte.send('btt.' + node + '.host.active_contract_num', active_contract_num, timestamp=timestamp)
    graphyte.send('btt.' + node + '.host.storage_used', storage_used, timestamp=timestamp)
    graphyte.send('btt.' + node + '.host.score', score, timestamp=timestamp)
    graphyte.send('btt.' + node + '.host.compensation_paid', compensation_paid, timestamp=timestamp)
    graphyte.send('btt.' + node + '.host.compensation_outstanding', compensation_outstanding, timestamp=timestamp)
    graphyte.send('btt.' + node + '.host.cheques_count', cheques_total_received_count, timestamp=timestamp)
    graphyte.send('btt.' + node + '.host.cheques_uncashed', cheques_uncashed_amount, timestamp=timestamp)

client = docker.from_env()
for container in client.containers.list():
    if "btfs" in container.name:
        fetch_btfs_data(container)
        

