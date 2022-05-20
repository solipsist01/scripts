import os
import docker
import time
import asyncio
import subprocess
import sys

def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped

@background
def check_container(container):
    status = 0
    mounts = container.attrs['Mounts']
    for mount in mounts:
        if "btfs" in mount['Source']:
            while status == 0:
                print("Waiting 30 seconds for container: " + container.name)
                time.sleep(30)

                print("Checking if container " + container.name + " started successfully.")

                for line in container.logs(stream=True, follow=False):
                    data = str((line.strip()))

                    #if this line is present in the logs, we assume everything is fine.
                    if 'Current host settings will be synced' in data:
                        print(container.name + " started successfully")
                        status = 1
                        continue

                if status == 0:
                    directory = mount['Source']
                    lockfile = directory + '/repo.lock'
                    chmod = 'chmod 777 ' + directory + ' -R'

                    print("Stopping container: " + container.name)
                    container.stop()
                    time.sleep(1)

                    print("Applying recursive chmod for directory: " + directory)
                    os.system(chmod)

                    print("Checking lockfile in directory: " + directory)
                    existfile_lockfile = os.path.isfile(lockfile)

                    if existfile_lockfile:
                        print("Lock file was left behind. Removed it from directory: " + directory)
                        os.remove(lockfile)

                    print("Starting container: " + container.name)
                    container.start()


process = subprocess.Popen(
    (['docker-compose', '--file', '/docker/compose/btfs/docker-compose.yml', 'pull']), stdout=subprocess.PIPE, stderr=subprocess.STDOUT
)
for line in process.stdout:
    sys.stdout.write(line.decode('utf-8'))


process = subprocess.Popen(
    (['docker-compose', '--env-file', '/docker/compose/btfs/.env', '--file', '/docker/compose/btfs/docker-compose.yml', 'up', '-d']), stdout=subprocess.PIPE, stderr=subprocess.STDOUT
)
for line in process.stdout:
    sys.stdout.write(line.decode('utf-8'))

#we are assuming containers have been recreated by docker-compose up -d
#now we check if the container came up correctly. if not, stop, remove lockfile, start.

client = docker.from_env()
for container in client.containers.list():
    if "btfs" in container.name:
        check_container(container)