import os
import sys
import shutil
import pexpect
import time

def create_directory_copy_script_and_execute():
    object_name = input("Please enter the object name for the new directory: ")
    target_path = f"/home/joe/Research/HST_MAST/{object_name}"
    
    if not os.path.exists(target_path):
        os.makedirs(target_path)
        print(f"Directory '{object_name}' created at {target_path}")
    else:
        print(f"Directory '{object_name}' already exists at {target_path}")
        return

    source_script = "/home/joe/Research/IllithidNova/Halsin.py"
    destination_script = os.path.join(target_path, "Halsin.py")
    shutil.copy(source_script, destination_script)
    print(f"Script 'Halsin.py' copied to {destination_script}")

    os.chdir(target_path)
    child = pexpect.spawn(f"python3 Halsin.py --hst_download", encoding='utf-8', timeout=30, echo=False)
    child.logfile = sys.stdout

    try:
        child.expect("Enter the target name:")
        target_name = input("Enter the target name: ")
        child.sendline(target_name)
        print(f"Sent target name: {target_name}")

        while True:
            index = child.expect([
                r"Enter the indices of products to download \(comma-separated\):",
                "Download completed successfully",
                pexpect.TIMEOUT,
                pexpect.EOF,
            ], timeout=120)

            if index == 0:
                indices = input("Enter the indices of products to download (comma-separated): ")
                print(f"Sending indices: {indices}")
                child.sendline(indices)
                # Wait for a confirmation message or a new prompt before continuing
                child.expect("Starting download of selected products.", timeout=120)
            elif index == 1:
                print("Download completed successfully")
                break
            elif index == 2:
                print("No response or further input needed, exiting.")
                break
            elif index == 3:
                print("Process finished")
                break

    except pexpect.exceptions.EOF:
        print("End of file reached. Process completed.")
    except pexpect.exceptions.TIMEOUT:
        print("Timeout occurred. Check the child process for issues.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

    child.close()

# Call the function
create_directory_copy_script_and_execute()