import os
import docker
import time
import asyncio

def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped

@background
def restart_containe(container):
    status = 0
    mounts = container.attrs['Mounts']
    for mount in mounts:
        if "btfs" in mount['Source']:
            while status == 0:
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

                print("Waiting 30 seconds for container: " + container.name)
                time.sleep(30)

                print("Checking if container " + container.name + " started successfully.")

                for line in container.logs(stream=True, follow=False):
                    #this is infact the last line from the logs.
                    data = str((line.strip()))

                if 'Current host settings will be synced' in data:
                    print(container.name + " started successfully")
                    status = 1

client = docker.from_env()
client.images.pull('solipsist01/go-btfs:latest')
for container in client.containers.list():
    if "btfs" in container.name:
        restart_containe(container)