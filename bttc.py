from datetime import datetime
import os
import docker
import time
import asyncio
import json
import graphyte
import requests

graphyte.init('graphite', prefix='miningtest')

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

@background
def fetch_btfs_data(node, hostid, container):
    timestamp = datetime.timestamp(datetime.now())
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

    uri = "https://scan-backend.btfs.io/api/v0/btfsscan/search/node_info?node_id=" +hostid
    try:
        response = requests.get(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        hostscore = response['data']['score']
        storage_used = response['data']['storage_used']
        graphyte.send('btt.' + node + '.host.storage_used', storage_used, timestamp=timestamp)
        graphyte.send('btt.' + node + '.host.score', hostscore, timestamp=timestamp)

    contracts = container.exec_run("btfs storage contracts stat host")
    
    if contracts is not None:
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
