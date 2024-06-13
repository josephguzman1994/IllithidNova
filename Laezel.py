import os
import sys
import shutil
import pexpect
import time
import argparse

class HSTManagement:
    def __init__(self):
        self.object_name = input("Please enter the object name for the new directory: ")
        self.target_path = f"/home/joe/Research/HST_MAST/{self.object_name}"
        self.source_script = "/home/joe/Research/IllithidNova/Halsin.py"
        self.destination_script = os.path.join(self.target_path, "Halsin.py")

    def create_directory_and_copy_script(self):
        if not os.path.exists(self.target_path):
            os.makedirs(self.target_path)
            print(f"Directory '{self.object_name}' created at {self.target_path}")
        else:
            print(f"Directory '{self.object_name}' already exists at {self.target_path}")
            return False
        shutil.copy(self.source_script, self.destination_script)
        print(f"Script 'Halsin.py' copied to {self.destination_script}")
        return True

    def execute_script(self):
        os.chdir(self.target_path)
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

        child.close()

    def manage_downloads(self):
        downloads_path = os.path.join(self.target_path, "downloads")
        if os.path.exists(downloads_path):
            raw_data_path = os.path.join(self.target_path, "raw_data")
            os.rename(downloads_path, raw_data_path)
            print(f"Renamed '{downloads_path}' to '{raw_data_path}'")

            working_directory_path = os.path.join(self.target_path, "working_directory")
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

            additional_files = ["/home/joe/Research/IllithidNova/Karlach.py", "/home/joe/Research/IllithidNova/config.ini"]
            for file_path in additional_files:
                shutil.copy(file_path, working_directory_path)
                print(f"Copied '{file_path}' to '{working_directory_path}'")

            os.remove(self.destination_script)
            print(f"Cleanup, removed script 'Halsin.py' from {self.destination_script}")
            print("\nPlease proceed to edit config.ini to your specific object criterion. Then use Karlach.py to execute dolphot processes and plotting")

def main():
    parser = argparse.ArgumentParser(description="Manage HST data processing tasks.")
    parser.add_argument('--halsin', help="Execute Halsin operations", action='store_true')
    args = parser.parse_args()

    if args.halsin:
        manager = HSTManagement()
        if manager.create_directory_and_copy_script():
            manager.execute_script()
            manager.manage_downloads()

if __name__ == "__main__":
    main()