#Batch decrypt ps3 iso's
import subprocess
import os
import glob
import re

def is_valid_key(decryption_key):
    pattern = re.compile(r'^[0-9a-fA-F]{32}$')
    return bool(pattern.match(decryption_key))

def decrypt_iso(decryption_key, encrypted_iso_path, decrypted_iso_path, ps3dec):
    command_args = [ps3dec, 'd', 'key', decryption_key, encrypted_iso_path, decrypted_iso_path]
    try:
        subprocess.run(command_args, check=True)
    except subprocess.CalledProcessError as e:
        print("Command execution failed:", e)

def main():
    #path to ps3dec executable
    ps3dec = '/path/to/your/PS3Dec'
    #path to all your decryption key files (.dkey). must be the same name as your iso files.
    decryption_key_path = '/path/to/your/decryptionkeys'
    #path to all your encrypted iso's (.iso)
    encrypted_isos_path = '/path/to/your/encryptedisos'
    #destionation folder for decrypted iso's
    decrypted_isos_path = '/path/to/your/decryptedisos'

    for filename in glob.iglob(encrypted_isos_path + '**/*.iso', recursive=True):
        filename_without_extension = os.path.splitext(os.path.basename(filename))[0]
        filename_dkey = filename_without_extension + '.dkey'
        fullpath_iso_encrypted = filename
        fullpath_dkey = os.path.join(decryption_key_path, filename_dkey)
        fullpath_iso_decrypted = os.path.join(decrypted_isos_path, filename_without_extension + '.iso')

        if not os.path.isfile(fullpath_iso_decrypted):
            if os.path.exists(fullpath_dkey):
                with open(fullpath_dkey, "r") as f:
                    decryption_key = f.read().strip()
                    if is_valid_key(decryption_key):
                        decrypt_iso(decryption_key, fullpath_iso_encrypted, fullpath_iso_decrypted, ps3dec)
                    else:
                        print(f"Invalid decryption key in {filename_dkey}")
            else:
                print(f"Decryption key not found for {filename_without_extension}")

if __name__ == "__main__":
    main()
