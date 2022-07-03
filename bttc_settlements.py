import subprocess
import json
import docker

def settle(node):
    settlement_output = subprocess.run(['docker', 'exec' , node,  'btfs',  'settlement', 'list'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    settlement_data = json.loads(settlement_output)

    for settlement in settlement_data['settlements']:
        peer = settlement['peer']
        peer_output = subprocess.run(['docker', 'exec' , node,  'btfs',  'cheque', 'cashstatus', peer], stdout=subprocess.PIPE).stdout.decode('utf-8')
        peer_data = json.loads(peer_output)
        
        uncashed = float(peer_data['uncashed_amount'])

        if uncashed > 0:
            subprocess.run(['docker', 'exec' , node,  'btfs',  'cheque', 'cash', peer], stdout=subprocess.PIPE).stdout.decode('utf-8')


client = docker.from_env()
for container in client.containers.list():
    if "btfs" in container.name:
        settle(node=container.name)