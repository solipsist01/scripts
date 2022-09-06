from datetime import datetime
import os
import docker
import time
import asyncio
import json
import graphyte
import requests
import socket
import struct
import _pickle as cPickle
import sys

class CarbonClient():

    def __init__(self, host, port):
        '''
        Constructor to create the carbon client
        '''
        self._host = str(host)
        self._port = int(port)

    def send_plaintext(self, name, value, timestamp):
        '''
        Send a value to carbon using the plaintext protocol
        '''
        try:
            sock = socket.socket()
            sock.connect((self._host, self._port))
        except socket.error as msg:
            print(msg)
            print('Could not open socket: ' + self._host + ':' + str(self._port))
            sys.exit(1)

        sock.send("%s %f %d\n" % (name, value, timestamp))
        sock.close()

    def send_pickle(self, pickle_data):
        '''
        Send a value(s) to carbon using the pickle protocol
        The general idea is that the pickled data forms a list of multi-level tuples:
            [(path, (timestamp, value)), ...]
        '''
        payload = cPickle.dumps(pickle_data)
        header = struct.pack("!L", len(payload))
        message = header + payload

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self._host, self._port))

        except socket.error as msg:
            print(msg)
            print('Could not open socket: ' + self._host + ':' + str(self._port))
            sys.exit(1)

        sock.send(message)
        sock.close()


def background(fn):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, fn, *args,**kwargs)
    return wrapped

@background
def fetch_btfs_data(container):
    global pickle
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
        bttc_addr_btt_balance = 0
        bttcaddress = response['BttcAddress']
        while bttc_addr_btt_balance == 0:
            response = None
            uri = "http://" + container.name + ":5001/api/v1/cheque/bttbalance?arg=" + bttcaddress
            
            try:
                response = requests.post(uri).json()
            except:
                ConnectionError
                response = None

            if response is not None:
                try:
                    bttc_addr_btt_balance = round(float(response['balance']) / 1000000000000000000)
                    pickle.append(('mining.btt.' + node + '.bttc_chain.bttc_addr_btt_balance', (timestamp, bttc_addr_btt_balance)))
                except:
                    KeyError


    ### fetch host score and storage in use
    uri = "http://" + container.name + ":5001/api/v1/storage/stats/info"
    try:
        response = requests.post(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        try:
            hostscore = int(response['host_stats']['uptime_level']) + int(response['host_stats']['age_level']) + int(response['host_stats']['version_level']) + int(response['host_stats']['active_level'])
            pickle.append(('mining.btt.' + node + '.host.score', (timestamp, hostscore)))
            pickle.append(('mining.btt.' + node + '.host.uptime_level', (timestamp, response['host_stats']['uptime_level'])))
            pickle.append(('mining.btt.' + node + '.host.age_level', (timestamp, response['host_stats']['age_level'])))
            pickle.append(('mining.btt.' + node + '.host.version_level', (timestamp, response['host_stats']['version_level'])))
            pickle.append(('mining.btt.' + node + '.host.active_level', (timestamp, response['host_stats']['active_level'])))
            pickle.append(('mining.btt.' + node + '.host.level', (timestamp, response['host_stats']['level'])))            
            pickle.append(('mining.btt.' + node + '.host.storage_used', (timestamp, response['host_stats']['storage_used'])))
        except:
            KeyError

### fetch Contract Data ####
    uri = "http://" + container.name + ":5001/api/v1/storage/contracts/stat?arg=host"
    try:
        response = requests.post(uri).json()
    except:
        ConnectionError
        response = None

    if response is not None:
        try:
            pickle.append(('mining.btt.' + node + '.host.active_contract_num', (timestamp, response['active_contract_num'])))
            pickle.append(('mining.btt.' + node + '.host.compensation_paid', (timestamp, response['compensation_paid'])))
            pickle.append(('mining.btt.' + node + '.host.compensation_outstanding', (timestamp, response['compensation_outstanding'])))
        except:
            KeyError

def main():
    background_loop = asyncio.get_event_loop()
    tasks = []

    client = docker.from_env()
    for container in client.containers.list():
        if "btfs" in container.name:
            tasks.append(fetch_btfs_data(container))

    try:
        background_loop.run_until_complete(asyncio.wait(tasks))
    finally:
        background_loop.close()

graphite_hostname = 'graphite'
graphite_port = 2004

carbon = CarbonClient(graphite_hostname, graphite_port)
pickle = []

main()
carbon.send_pickle(pickle)
#print(pickle)



