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
                child.expect("Starting download of selected products.", timeout=120)
            elif index == 1:
                print("Download completed successfully")
                break
            elif index == 2:
                print("Timeout occurred, checking if downloads are complete...")
                break
            elif index == 3:
                print("Process finished or terminated unexpectedly.")
                break

    except pexpect.exceptions.EOF:
        print("End of file reached. Checking for downloads...")
    except pexpect.exceptions.TIMEOUT:
        print("Timeout occurred. Check the child process for issues.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

    # Check if downloads directory exists and proceed
    downloads_path = os.path.join(target_path, "downloads")
    if os.path.exists(downloads_path):
        # Rename /downloads to /raw_data
        raw_data_path = os.path.join(target_path, "raw_data")
        os.rename(downloads_path, raw_data_path)
        print(f"Renamed '{downloads_path}' to '{raw_data_path}'")

        # Copy /raw_data to /working_directory
        working_directory_path = os.path.join(target_path, "working_directory")
        if not os.path.exists(working_directory_path):
            os.makedirs(working_directory_path)
        for item in os.listdir(raw_data_path):
            s = os.path.join(raw_data_path, item)
            d = os.path.join(working_directory_path, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        print(f"Copied contents from '{raw_data_path}' to '{working_directory_path}'")

        # Copy additional files into /working_directory
        additional_files = [
            "/home/joe/Research/IllithidNova/Karlach.py",
            "/home/joe/Research/IllithidNova/config.ini"
        ]
        for file_path in additional_files:
            shutil.copy(file_path, working_directory_path)
            print(f"Copied '{file_path}' to '{working_directory_path}'")

    child.close()

# Call the function
create_directory_copy_script_and_execute()