from datetime import datetime
import os
import docker
import time
import asyncio
import json
import graphyte
import requests

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
def bttc_collect(node, hostid, container, bttc_destination_address):
    timestamp = datetime.timestamp(datetime.now())
    uri = "https://scan-backend.btfs.io/api/v1/node/addr_info?id=" +hostid

    try:
        response = requests.get(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        bttc_addr_btt_balance = float(response['data']['bttc_addr_btt_balance'])
        bttc_source_address = response['data']['bttc_addr']

        if bttc_destination_address.upper() == bttc_source_address.upper():
            print("we're not sending to ourself. aborting")
        else:
            #keep 10.000 
            to_send = int(bttc_addr_btt_balance - 10000000000000000000000)
            to_send_readable = str(round(to_send / 1000000000000000000))
            print("Checking ammount to send: " + str(to_send_readable))
            if to_send > 0:
                print("sending " + to_send_readable + " from: " + bttc_source_address + " to: " + bttc_destination_address)
                btfs_command = "btfs bttc send-btt-to " + bttc_destination_address + " " + str(to_send)
                print(str(btfs_command))

                output = container.exec_run(btfs_command)
                print(output)

bttc_destination_address = os.getenv('BTTC_DESTINATION_ADDRESS')  

client = docker.from_env()
for container in client.containers.list():
    if "btfs" in container.name:
        bttc_collect(container.name, fetch_hostid(container), container, bttc_destination_address)
