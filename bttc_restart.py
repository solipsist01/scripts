import os
import docker

client = docker.from_env()
client.images.pull('solipsist01/go-btfs')
for container in client.containers.list():
    if "btfs" in container.name:
        mounts = container.attrs['Mounts']
        for mount in mounts:
            if "btfs" in mount['Source']:
                directory = mount['Source']
                lockfile = directory + '/repo.lock'
                chmod = 'chmod 777 ' + directory + ' -R'

                print("Stopping container: " + container.name)
                container.stop()

                print("Applying recursive chmod for directory: " + directory)
                os.system(chmod)

                print("Checking lockfile in directory: " + directory)
                existfile_lockfile = os.path.isfile(lockfile)

                if existfile_lockfile:
                    print("Lock file was left behind. Removed it from directory: " + directory)
                    os.remove(lockfile)

                print("Starting container: " + container.name)
                container.start()

        

