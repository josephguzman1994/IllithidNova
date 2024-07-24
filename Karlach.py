import argparse
import configparser
import os
import re
from collections import defaultdict
import stwcs
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from astropy.wcs import WCS
from astropy.io import fits
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.coordinates import Angle
from astroquery.simbad import Simbad
from astropy.visualization.wcsaxes import WCSAxes
from matplotlib.patches import Circle
from matplotlib.ticker import FuncFormatter
from scipy import stats
from scipy.stats import gaussian_kde
from sys import exit
from os import system
import subprocess
import glob

# Coding up the automation of the dolphot processing: Written by Joseph Guzman @josephguzman1994@gmail.com
class TerminalCommandExecutor:
    
    # Step 0: if you used a different photometric system on your last use of dolphot, you need to run 'make clean' and 'make' in 'makefile' directory
    # Called with --make argument
    def run_make(config):
        # Need to find the Makefile directory. Please include 'make_path = ~/Makefile' into config.ini file. The code can attempt to find the directory for you, if you'd rather not
        make_path = config['DOLPHOT_CONFIG'].get('make_path')
        if not make_path or not os.path.exists(make_path):
            print("Config file is missing or 'make_path' is not defined or invalid.")
            choice = input("Do you want to manually type the dolphot2.0 path? (yes/no) (if no, code will attempt to locate make_path for you): ").lower()
            if choice == 'yes' or choice == 'y':
                make_path = input("Enter the path to the dolphot2.0 directory: ")
            else:
                for root, dirs, files in os.walk(os.getcwd()):
                    if 'dolphot2.0' in dirs:
                        make_path = os.path.join(root, 'dolphot2.0')
                        break
                else:
                    print("dolphot2.0 directory not found.")
                    exit(1)  # Exit the script if dolphot2.0 directory is not found
            # Update config.ini with the new make_path
            config['DOLPHOT_CONFIG']['make_path'] = make_path
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
        
        # Now that the directory has been found, run 'make clean' in this directory. Yes no prompt to avoid accidental deletion of current dolphot installation
        choice = input(f"Do you want to run 'make clean' in '{make_path}' directory? (yes/no): ").lower()
        
        if choice == 'yes' or choice == 'y':
            # Execute 'make clean' in makefile directory
            subprocess.run(['make', 'clean'], cwd=make_path)
            print("make clean executed successfully!")

            # Preparing to run 'make'. First, scrub config.ini for 'system_name' in DOLPHOT config, to find desired photometric system to run make
            system_name = config['DOLPHOT_CONFIG'].get('system_name')
            valid_systems = ['WFPC2', 'ACS', 'WFC3', 'ROMAN', 'NIRCAM', 'NIRISS', 'MIRI']
            system_choice = None
            
            if system_name:
                # Extract the base system name in case it includes additional descriptors
                base_system_name = system_name.split('_')[0]
                if base_system_name in valid_systems:
                    system_choice = base_system_name
                else:
                    print(f"System name '{system_name}' in config is not recognized. Valid options are: {valid_systems}")

            if not system_choice:
                system_choice = input("Input a photometric system (WFPC2, ACS, WFC3, ROMAN, NIRCAM, NIRISS, MIRI): ").upper()
                if system_choice not in valid_systems:
                    print("Invalid choice. Please pick from the listed systems.")
                    exit(1)
            
            # Print statements for user to verify path and option
            print(f"Reading Makefile from: {os.path.join(make_path, 'Makefile')}")

            print(f"Editing the Makefile to use {system_choice}...")

            # Read in the 'Makefile'
            makefile_path = os.path.join(make_path, 'Makefile')
            with open(makefile_path, 'r') as file:
                lines = file.readlines()

            # Define the photometric system options found in Makefile
            system_options = [
                    'export USEWFPC2', 'export USEACS', 'export USEWFC3', 
                    'export USEROMAN', 'export USENIRCAM', 'export USENIRISS', 'export USEMIRI'
            ]

            # Generate list of all systems ASIDE from the user's chosen system, used to find lines to edit later
            other_systems = [option for option in system_options if option != f'export USE{system_choice}']
                
            # Prepare to edit 'Makefile'
            edited_lines = []
            for line in lines:
                    
                # Check if the line is already commented
                is_commented = line.strip().startswith('#')

                # Check if the line starts with any of the 'other_systems' and is not already commented, then comment it out
                if any(line.strip().startswith(option) and not is_commented for option in other_systems):
                    print(f"Editing line for other systems: {line.strip()}")
                    edited_line = '#' + line.strip()
                    edited_lines.append(edited_line)
                    print(f"Edited line: {edited_line}")  # Print the edited line

                # Match lines with or without comments that start with "export USE", followed by the user's system choice and "=1"
                elif re.match(r'^\s*#?\s*export USE{0}=1$'.format(system_choice), line.strip()):
                    print(f"Editing line for {system_choice}: {line.strip()}")
                    edited_line = line.replace('#', '') if is_commented else line  # Remove comment for the user's chosen system
                    edited_lines.append(edited_line)
                    print(f"Edited line: {edited_line}")  # Print the edited line

                else:
                    edited_lines.append(line)

            # Write the modified lines back to the Makefile
            with open(makefile_path, 'w') as file:
                file.writelines(edited_lines)

            print("Makefile editing complete.")

            # Now that the Makefile has been edited, we can finally execute 'make' in the makefile directory to prep the dolphot process
            # Run 'make' command
            print("Running 'make'...")
            result = subprocess.run(['make'], cwd=make_path)
            if result.returncode == 0:
                print("make executed successfully!")
            else:
                print("Error occurred during make.")
                # Handle error if needed
        else:
            print("make clean not executed.")

    # Executing the whole dolphot block is long, and there are many potential breaking points.
    # Defining function to log and print error details, and suggest recovery actions.
    # Saves terminal output and suggestions to "dolphot_error.log"
    
    def log_error_and_suggest(self, message, exception=None, suggestion=""):
        error_message = f"Error: {message}"
        if exception:
            error_message += f" | Exception: {str(exception)}"
        print(error_message)
        if suggestion:
            print(f"Suggestion: {suggestion}")
        # Optionally, write to a log file
        with open("dolphot_error.log", "a") as log_file:
            log_file.write(error_message + "\n")
            if suggestion:
                log_file.write(f"Suggestion: {suggestion}\n")

    # Start of the dolphot processing. If you would like to be offered verifications at each step, call --interactive with --dolphot
    # Step 1: execute mask command
    def execute_mask_command(self, command, output_mask):
        print(f"Executing mask command: {command}")
        try:
            with open(output_mask, 'w') as logfile:
                subprocess.run(command, shell=True, stdout=logfile, stderr=subprocess.PIPE)
            print(f"Mask command executed successfully! Output log: {output_mask}\n")
        except Exception as e:
            self.log_error_and_suggest(f"Failed to execute mask command '{command}'.", e,
                                       "Check in working directory that .fits files are correctly formatted and accessible, and retry.")

    # In case step 1 encounters an unfamiliar mask name, allow it to continue by inputting manually. May be an unecessary definition now.
    def execute_command(self, command, output_log):
        print(f"Executing command: {command}")
        with open(output_log, 'w') as logfile:
            subprocess.run(command, shell=True, stdout=logfile, stderr=subprocess.PIPE)
        print(f"{command} executed successfully! Output log: {output_log}\n")

    # Step 2: execute splitgroups command
    def execute_splitgroups_command(self, command, output_splitgroups):
        print(f"Executing splitgroups command: {command}")
        try:
            with open(output_splitgroups, 'w') as logfile:
                subprocess.run(command, shell=True, stdout=logfile, stderr=subprocess.PIPE)
            print(f"Splitgroups command executed successfully! Output log: {output_splitgroups}")
        except Exception as e:
            self.log_error_and_suggest("Failed to execute splitgroups command.", e,
                                       "Verify the presence and format of .fits files in the directory. Additionally, verify that splitgroups is valid for chosen photometric system. Inspect mask log file")

    # Step 3: execute calcsky command for all chip1 and chip2 files:
    def execute_calcsky_commands(self, working_directory, obj_name, system_name, calcsky_values=None):
        if working_directory is None:
            working_directory = os.getcwd()  # Get the current working directory if not provided
        
        output_log = f'calcsky_{obj_name}.log'

        # Define patterns based on system_name
        if system_name in ['ACS_HRC', 'WFC3_IR', 'NIRCAM', 'NIRISS', 'MIRI', 'ROMAN']:
            file_patterns = [os.path.join(working_directory, '*.fits')]  # Run calcsky on .fits for systems without splitgroups
        elif system_name == 'WFPC2':
            file_patterns = [os.path.join(working_directory, f'*chip{i}*.fits') for i in range(1, 5)]  # WFPC2 has chip1 to chip4
        else:
            file_patterns = [os.path.join(working_directory, '*chip1*'), os.path.join(working_directory, '*chip2*')]  # chip1 or chip2, default case for other systems

        # Define default calcsky values based on system_name
        if not calcsky_values:
            if system_name in ['ACS_HRC', 'ACS_WFC', 'WFC3_UVIS']:
                calcsky_values = [15, 35, -128, 2.25, 2.00]
            elif system_name == 'WFC3_IR':
                calcsky_values = [10, 25, -64, 2.25, 2.00]
            elif system_name == 'WFPC2':
                calcsky_values = [10, 25, -50, 2.25, 2.00]
            else:
                calcsky_values = [15, 35, -128, 2.25, 2.00]

        try:
            for pattern in file_patterns:
                chip_files = glob.glob(pattern)
                if chip_files:
                    print(f"Executing calcsky commands for files matching {pattern}:")
                    with open(output_log, 'a') as logfile:
                        for file in chip_files:
                            filename = os.path.basename(file).split('.')[0]
                            # Can change default calcsky values through --calcsky_values, allowing manual input. 
                            command = f'calcsky "{filename}" {" ".join(str(val) for val in calcsky_values)} >> {output_log}'
                            subprocess.run(command, shell=True, stdout=logfile, stderr=subprocess.PIPE)

            print(f"All calcsky commands executed successfully! Combined output log: {output_log}\n")
        except Exception as e:
            self.log_error_and_suggest("Failed to execute calcsky commands.", e,
                                       "Verify the presence of .fits files, check calcsky values for chosen system, inspect mask and splitgroups log files. Consider syntax of file pattern in def execute_calcsky_commands for system, and retry.")

    # Step 4a.1: Now that all the pre-processing is done, we need to track down specific files for generating the dolphot parameter file
    def find_chip_files(self, working_directory, system_name):
        all_files = os.listdir(working_directory)
        
        # Define patterns based on system_name
        if system_name in ['ACS_HRC', 'WFC3_IR', 'NIRCAM', 'NIRISS', 'MIRI', 'ROMAN']:
            # Include only .fits files that do not have extra identifiers like .sky.fits, .res.fits, etc.
            chip_files = [f for f in os.listdir(working_directory) if f.endswith('.fits') and not re.search(r'\.(sky|res|psf|chip1|chip2)\.fits$', f)]
        elif system_name == 'WFPC2':
            # Include files for chip1 through chip4
            chip_files = [f for f in all_files if re.match(r'.*\.chip[1-4]\.fits$', f)]
        else:
            # find .chip1, .chip2 Default case for other systems
            chip_files = [f for f in all_files if re.match(r'.*\.chip[12]\.fits$', f)]
        
        # Exclude files with specific patterns if haven't already i.e. ACS_WFC, WFC3_UVIS
        chip_files = [f for f in chip_files if not re.search(r'\.(sky|res|psf)\.fits$', f)]
        
        # Identify all drz/drc files with a more inclusive regex
        drz_drc_files = [f for f in chip_files if re.search(r'\_dr[zc]\.fits$', f)]
        other_chip_files = [f for f in chip_files if not re.search(r'\_dr[zc]\.fits$', f)]

        # Select the deepest image from drz/drc files
        selected_drz_drc_file = self.select_deepest_image(drz_drc_files, working_directory)

        # Debugging output
        print("All drz/drc files found:", drz_drc_files)
        print("Selected deepest drz/drc file:", selected_drz_drc_file)

        # Construct the final list of files to use
        selected_files = [selected_drz_drc_file] if selected_drz_drc_file else []
        selected_files += other_chip_files

        print("Selected image files for dolphot photometry")
        for file in selected_files:
            print(file)

        return selected_files

    # Step 4a.2: Find the deepest exposure drz or drc image to use as reference image in dolphot params
    def select_deepest_image(self, files, working_directory):
        max_exposure = 0
        selected_file = None

        for file in files:
            with fits.open(os.path.join(working_directory, file)) as hdul:
                exposure = hdul[0].header.get('EXPTIME', 0)

            # Update the selected file based on the exposure time and preferences
            if exposure > max_exposure or (exposure == max_exposure and self.is_preferred_file(file, selected_file)):
                max_exposure = exposure
                selected_file = file

        return selected_file

    # Step 4a.3: Choose the 'best' reference image. Rules: 1. Deepest exposure. 2. drc over drz (as this corrects for CTE exposure)
    # 3. Chip1 over Chip2, as some systems may not generate .Chip2 files. 
    def is_preferred_file(self, new_file, current_best):
        if not current_best:
            return True
        # Preference order: DRC over DRZ, CHIP1 over CHIP2
        if 'drc' in new_file and 'drz' in current_best:
            return True
        if 'chip1' in new_file and 'chip2' in current_best:
            return True
        return False

    # Extra Option: Each image in dolphot photometry allows you to specify imgshift and imgform, in case you want to play with that
    # Call --customize-img, then you can specify which image and values you want to alter
    def customize_image_parameters(self, selected_files):
        print("Available images for customization:")
        for index, file in enumerate(selected_files):
            print(f"{index}: {file}")

        customizations = {}
        while True:
            index_input = input("Enter the index of the image you want to customize (or 'done' to finish): ")
            if index_input.lower() == 'done':
                break

            try:
                index = int(index_input)
                if index < 0 or index >= len(selected_files):
                    print("Invalid index, please try again.")
                    continue
            except ValueError:
                print("Please enter a valid integer index or 'done'.")
                continue

            shift = input(f"Enter shift for img{index} (default '0 0', format 'x y'): ") or "0 0"
            xform = input(f"Enter transformation for img{index} (default '1 0 0', format 'scale x y'): ") or "1 0 0"
            customizations[index] = (shift, xform)

        return customizations

    # Step 4b: Create and edit dolphot parameter file
    def write_parameter_file(self, selected_files, customizations, config_file):
        config = configparser.ConfigParser()
        config.optionxform = str  # Preserve case sensitivity of keys
        config.read(config_file)

        obj_name = config['DOLPHOT_CONFIG']['obj_name']
        system_name = config['DOLPHOT_CONFIG']['system_name']
        param_file = f"{obj_name}_{system_name}_phot.param"

        # Check if parameter file already exists
        file_exists = os.path.isfile(param_file)
        
        try:
            if file_exists:
                user_input = input(f"Found '{param_file}' already exists. Do you want to make a new one? (y/n): ")
                if user_input.lower() not in ('y', 'yes'):
                    print("Skipping parameter file creation")
                    return False, file_exists

            with open(param_file, 'w') as file:
                file.write(f"Nimg = {len(selected_files) - 1}\n")

                # Write additional lines for each image
                for index, image_file in enumerate(selected_files):
                    base_name = os.path.splitext(image_file)[0]  # Remove the .fits extension
                    # Retrieve customizations or use default values
                    shift, xform = customizations.get(index, ("0 0", "1 0 0"))
                    file.write(f"img{index}_file = {base_name}\n")
                    file.write(f"img{index}_shift = {shift}\n")  # Use custom or default shift
                    file.write(f"img{index}_xform = {xform}\n")  # Use custom or default transformation

                # Directly write the config file section, preserving formatting
                with open(config_file, 'r') as cfg:
                    write_section = False
                    for line in cfg:
                        if line.strip().startswith('[' + system_name + ']'):
                            write_section = True
                            continue  # Skip writing the section header e.g. [ACS_HRC]
                        elif line.strip().startswith('[') and not line.strip().startswith('[' + system_name + ']'):
                            write_section = False
                        if write_section:
                            file.write(line)

            print(f"Path to new parameter file: {os.path.abspath(param_file)}")
            return True, not file_exists # Return True if new file, False if updated
        except Exception as e:
            self.log_error_and_suggest("Failed to create/update the parameter file.", e,
                                       "Check the selected image files. Verify the existence of drc/drz files. Verify system_name and corresponding [section], key-value pairs exists for system in config.ini.")

    # Step 4c: Find the parameters associated with specific sections. Define system_name = (e.g.: ACS_HRC) under [DOLPHOT_CONFIG] in config.ini
    # Refer to various dolphot manuals for how to define everything
    def get_section_data(self, config_file, section_name):
        
        # Initialize an empty dictionary to store the section data
        section_data = {}

        # Create a ConfigParser object and read the config file
        config = configparser.ConfigParser()
        config.read(config_file)

        # Check if the specified section exists in the config file
        if section_name in config:
            # Get all keys and values from the specified section
            section_data = dict(config[section_name])

        return section_data

    # Step 5: With the parameter file created, we can finally execute dolphot
    def execute_dolphot(self, obj_name, param_file, working_directory, config):
        # Fetch system name from the configuration
        system_name = config['DOLPHOT_CONFIG'].get('system_name', 'default_system')

        # Prompt the user to confirm execution of dolphot
        user_input = input("Would you like to execute dolphot? This will take awhile and should not be interrupted. (y/n): ")
        if user_input.lower() not in ('y', 'yes'):
            print("Dolphot execution cancelled.")
            return False

        # Construct the dolphot terminal command 
        output_phot_file = f"{obj_name}_{system_name}.phot"
        log_file = f"dolphot_{obj_name}_{system_name}.log"
        command = f"time dolphot {output_phot_file} -p{param_file} >> {log_file}"

        # Execute the command in the working directory
        print(f"Executing dolphot command: {command}")
        try:
            subprocess.run(command, shell=True, cwd=working_directory, check=True)
            print(f"Dolphot executed successfully! Output logged in {log_file}.\n")
            print(f"Output photometry file: {output_phot_file}")
            return True
        except subprocess.CalledProcessError as e:
            self.log_error_and_suggest("Failed to execute dolphot.", e,
                                       "Check the parameter file exists and for errors. Verify images in parameter file exist in directory. Check obj_name defined in config.ini. Compare parameter file to dolphot manuals. Inspect log files")
            return False

    # Step 6: Now that dolphot has executed, .phot file and reference image should exist, and be clear to define and manipulate
    # to plot data and make data files. Need to first update config.ini with phot_file and ref_file
    def update_config_with_files(self, config, working_directory): 
        # This definition currently has a minor bug, which does not preserve the whitespacing when updating config.ini.

        # Ensure 'DOLPHOT_CONFIG' is a valid section
        if 'DOLPHOT_CONFIG' in config:

            # Check if 'phot_file' is manually specified in the config, if so, respect that and leave it alone
            manual_phot_file = config['DOLPHOT_CONFIG'].get('phot_file')
            if manual_phot_file:
                phot_file_path = os.path.join(working_directory, manual_phot_file)
                if not os.path.exists(phot_file_path):
                    print(f"Specified photometry file {manual_phot_file} not found in working directory.")
            else:
                # If not manually defined, attempt to find .phot file in working directory based on obj_name, as generated by --dolphot
                generated_phot_file = f"{config['DOLPHOT_CONFIG']['obj_name']}_{config['DOLPHOT_CONFIG']['system_name']}.phot"
                phot_file_path = os.path.join(working_directory, generated_phot_file)
                if os.path.exists(phot_file_path):
                    config['DOLPHOT_CONFIG']['phot_file'] = generated_phot_file
                    print(f"Using generated photometry file: {generated_phot_file}")
                else:
                    print("Photometry file not found. Please run --dolphot to generate it, or manually input 'phot_file' in config.ini.")

            # Similar logic for reference image
            manual_ref_file = config['DOLPHOT_CONFIG'].get('ref_file')
            if manual_ref_file:
                ref_file_path = os.path.join(working_directory, manual_ref_file)
                if not os.path.exists(ref_file_path):
                    print(f"Specified reference image {manual_ref_file} not found in working directory.")
            else:
                # Logic to automatically find the best reference image to add to config.ini
                selected_files = os.listdir(working_directory)
                deepest_image = self.select_deepest_image([f for f in selected_files if 'drc' in f or 'drz' in f], working_directory)
                ref_file_path = deepest_image if deepest_image else None
                if ref_file_path:
                    config['DOLPHOT_CONFIG']['ref_file'] = ref_file_path
                    print(f"Using found reference image: {ref_file_path}")
                else:
                    print("Reference image not found. Please ensure suitable images are in the working directory or manually input 'ref_file' in config.ini.")       

            # Write updates back to config.ini only if either file is updated
            if os.path.exists(phot_file_path) or ref_file_path:
                with open('config.ini', 'w') as configfile:
                    config.write(configfile)
        else:
            print("DOLPHOT_CONFIG section is missing in the config.")


# After finishing pre-processing, handle image files, or photometry file outputs of dolphot
class DataFilterOrganizer:
    def __init__(self, output_file = None, directory=None):
        self.directory = directory if directory else os.getcwd()
        self.filter_dict = defaultdict(list)
        self.output_file = output_file

    def organize_by_filter(self, file_paths):
        for file_path in file_paths:
            with fits.open(file_path) as hdulist:
                # Attempt to fetch FILTER1 and FILTER2
                filter1_name = hdulist[0].header.get("FILTER1")
                filter2_name = hdulist[0].header.get("FILTER2")
                
                # Fallback to FILTER if FILTER1 and FILTER2 are not available
                if filter1_name and filter2_name:
                    combined_filter = f"{filter1_name}, {filter2_name}"
                else:
                    combined_filter = hdulist[0].header.get("FILTER", "N/A")
                
                self.filter_dict[combined_filter].append(file_path)

    def print_organized_list(self):
        if not self.output_file:
            raise ValueError("Output file not specified.")

        with open(self.output_file, 'w') as output:
            output.write("Files Organized by Filter:\n")
            #print("DEBUG: Writing to file...")
            
            if not self.filter_dict:
                print("DEBUG: filter_dict is empty")  # Debugging statement

            # First, print a simple list of files organized by filter
            for filter_key, files in self.filter_dict.items():
                output.write(f"\nFilter(s): {filter_key}\n")
                for file_path in files:
                    output.write(f"\t{file_path}\n")
                output.write("\t--------------------------------------------------\n")

            # Optionally, print detailed header information
            output.write("\nDetailed Header Information:\n")
            for filter_key, files in self.filter_dict.items():
                output.write(f"\nFilter(s): {filter_key}\n")
                for file_path in files:
                    output.write(f"\t{file_path}\n")
                    with fits.open(file_path) as hdulist:
                        # Print available filter information
                        if 'FILTER' in hdulist[0].header:
                            output.write(f"\t\tFilter = {hdulist[0].header['FILTER']}\n")
                        if 'FILTER1' in hdulist[0].header:
                            output.write(f"\t\tFilter1 = {hdulist[0].header['FILTER1']}\n")
                        if 'FILTER2' in hdulist[0].header:
                            output.write(f"\t\tFilter2 = {hdulist[0].header['FILTER2']}\n")
                        output.write(f"\t\tDetector = {hdulist[0].header.get('DETECTOR', 'N/A')}\n")
                        output.write(f"\t\tTargName = {hdulist[0].header.get('TARGNAME', 'N/A')}\n")
                        output.write(f"\t\tExposure Time = {hdulist[0].header.get('EXPTIME', 'N/A')}\n")
                    output.write("\t--------------------------------------------------\n")

class PlotManager:
    def __init__(self, config, obj_name, distance, proximity_thresholds, pdf=None, data_dir=None):
        
        if not isinstance(config, configparser.ConfigParser):
            raise ValueError("Config must be an instance of configparser.ConfigParser")

        self.config = config
        self.obj_name = obj_name
        self.distance = distance
        self.proximity_thresholds = proximity_thresholds
        self.pdf = pdf
        self.data_dir = data_dir

        # Assuming you ran --dolphot, the code will automatically write phot_file and ref_file to config.ini for you,
        # if you immediately run --phot. Alternatively, you can choose to define phot_file and ref_file in config.ini manually
        executor = TerminalCommandExecutor()

        # Call update_config_with_files on the executor instance
        executor.update_config_with_files(self.config, os.getcwd())
        
        self.phot_file = self.config['DOLPHOT_CONFIG'].get('phot_file')
        self.ref_file = self.config['DOLPHOT_CONFIG'].get('ref_file')

    def prepare_data(self):
        # Load in the data. Verify phot_file, ref_file, SN object exist and can be used
        print(f"\nPreparing data within {self.proximity_thresholds} pc of {self.obj_name} using {self.phot_file} and {self.ref_file} at distance {self.distance} pc")
        try:
            data = np.genfromtxt(self.phot_file, usecols=(2, 3, 9, 15, 17, 19, 20, 28, 30, 32, 33))
        except IOError:
            print(f"Error: The file {self.phot_file} could not be found.")
            return None

        try:
            with open(self.phot_file + '.columns', 'r') as f:
                columns_data = f.readlines()
        except IOError:
            print(f"Error: The columns file for {self.phot_file} could not be found.")
            return None

        try:
            with fits.open(self.ref_file) as ref:
                # Get system_name from config.ini, if failed to find system_name, use 'default' as system name and move to else
                system_name = self.config['DOLPHOT_CONFIG'].get('system_name', 'default')
                # ACS_HRC has relevant wcs information stored in SCI1 header. Often the distortion information breaks the wcs transformation, and is not necessary
                if system_name == 'ACS_HRC':
                    ref_header = ref['SCI', 1].header
                    # Remove distortion-related keywords to simplify WCS initialization
                    distortion_keywords = ['CPDIS1', 'CPDIS2', 'DP1', 'DP2', 'NPOLEXT']
                    for key in distortion_keywords:
                        if key in ref_header:
                            del ref_header[key]
                else:
                    ref_header = ref[0].header
                wcs = WCS(ref_header)
        except IOError:
            print(f"Error: The reference file {self.ref_file} could not be opened.")
            return None

        # Query simbad to automatically define SN RA and SN Dec. Allows Manual input if not found
        result_table = Simbad.query_object(self.obj_name)
        if result_table is not None:
            ra_str, dec_str = result_table['RA'].data[0], result_table['DEC'].data[0]
            sky_coord = SkyCoord(ra=ra_str, dec=dec_str, unit=("hourangle", "deg"), frame='icrs')
            self.sn_ra, self.sn_dec = sky_coord.ra.deg, sky_coord.dec.deg
        else:
            print(f"Warning: Object {self.obj_name} not found in SIMBAD. Defaulting to manual input.")
            self.sn_ra = float(input("Enter RA (deg): "))
            self.sn_dec = float(input("Enter DEC (deg): "))

        # Columns defined in 2004dj_kochanek.phot.columns (indexing from 1): Currently hardcoded, verify this is generally true.
        # Held true for ACS_HRC data, ACS_WFC data, and WFC3 data.
        #3.  Object X position on reference image (or first image, if no reference) = 0
        #4.  Object Y position on reference image (or first image, if no reference) = 1
        #10. Crowding                                                               = 2
        #16. Instrumental VEGAMAG magnitude, WFC3_F475W                             = 3
        #18. Magnitude uncertainty, WFC3_F475W                                      = 4
        #20. Signal-to-noise, WFC3_F475W                                            = 5
        #21. Sharpness, WFC3_F475W                                                  = 6
        #29. Instrumental VEGAMAG magnitude, WFC3_F814W                             = 7
        #31. Magnitude uncertainty, WFC3_F814W                                      = 8
        #33. Signal-to-noise, WFC3_F814W                                            = 9
        #34. Sharpness, WFC3_F814W                                                  = 10

        # Extract data                                                              
        # Note 'usecols' remapped data. Proper indexes given ----------------------^^^^^
        x, y, crowd = data[:, 0], data[:, 1], data[:, 2]
        blue, blue_unc, blue_sn, blue_sharp = data[:, 3], data[:, 4], data[:, 5], data[:, 6]
        red, red_unc, red_sn, red_sharp = data[:, 7], data[:, 8], data[:, 9], data[:, 10]

        # Prepare dynamic labels
        self.cmd_label = (columns_data[15].split(', ')[1] + '- ' + columns_data[28].split(', ')[1]).strip()
        self.blue_label, self.red_label = columns_data[15].split(', ')[1].strip(), columns_data[28].split(', ')[1].strip()
        self.blue_abs_cut_label, self.red_abs_cut_label = (columns_data[15].split(', ')[1].strip()+'[Abs]'), (columns_data[28].split(', ')[1].strip()+'[Abs]')
        self.blue_unc_label, self.red_unc_label = (columns_data[17].split(', ')[1] + ' Uncertainty').strip(), (columns_data[30].split(', ')[1] + ' Uncertainty').strip()
        
        return (data, x, y, crowd, blue, blue_unc, blue_sn, blue_sharp, red, red_unc, red_sn, red_sharp,
                self.cmd_label, self.red_label, self.blue_label, self.red_abs_cut_label, self.blue_abs_cut_label, self.red_unc_label, self.blue_unc_label, wcs, self.sn_ra, self.sn_dec)

    def process_data(self, prepared_data):
        (data, x, y, crowd, blue, blue_unc, blue_sn, blue_sharp, red, red_unc, red_sn, red_sharp,
        self.cmd_label, self.red_label, self.blue_label, self.red_abs_cut_label, self.blue_abs_cut_label, self.red_unc_label, self.blue_unc_label, wcs, sn_ra, sn_dec) = prepared_data

        # Define the quality cut conditions: Refer to Murphy 2018, NGC6946-BH1
        red_sn_above4 = red_sn >= 4.0
        blue_sn_above4 = blue_sn >= 4.0
        sharp_cond = (blue_sharp**2 + red_sharp**2) <= 0.15
        crowd_cond = crowd <= 1.3
        quality_mask = red_sn_above4 & blue_sn_above4 & sharp_cond & crowd_cond

        # Convert pixel coordinates to world coordinates for all data
        ra_all, dec_all = wcs.all_pix2world(x, y, 1)
        star_coords = SkyCoord(ra=ra_all, dec=dec_all, unit=(u.deg, u.deg), frame='icrs')
        sn_skycoord = SkyCoord(ra=sn_ra, dec=sn_dec, unit=(u.deg, u.deg), frame='icrs')
        sep = sn_skycoord.separation(star_coords)
        
        results = []
        for threshold in self.proximity_thresholds:
            proximity_threshold = float(threshold)
            proximity_mask = (sep.radian * self.distance) <= proximity_threshold
            combined_mask = quality_mask & proximity_mask

            # Perform both quality and distance masks
            x_cut = x[combined_mask]
            y_cut = y[combined_mask]
            blue_cut = blue[combined_mask]
            blue_unc_cut = blue_unc[combined_mask]
            # Convert to absolute magnitude
            blue_abs_cut = blue_cut - 5 * np.log10(self.distance) + 5
            red_cut = red[combined_mask]
            red_unc_cut = red_unc[combined_mask]
            # Convert to absolute magnitude
            red_abs_cut = red_cut - 5 * np.log10(self.distance) + 5
            color_filtered = blue_cut - red_cut
            ra_cut = ra_all[combined_mask]
            dec_cut = dec_all[combined_mask]

            results.append((x_cut, y_cut, blue_cut, red_cut, blue_unc_cut, red_unc_cut, color_filtered, self.cmd_label, self.red_label, self.blue_label, self.red_abs_cut_label, self.blue_abs_cut_label, self.red_unc_label, self.blue_unc_label, ra_cut, dec_cut, blue_abs_cut, red_abs_cut))

        return results

    def save_processed_data(self, data, obj_name, threshold, blue_label, red_label):
        #print(f"Received data type: {type(data)}, length of data: {len(data)}")
        try:
            x_cut, y_cut, blue_cut, red_cut, blue_unc_cut, red_unc_cut, color_filtered, cmd_label, red_label, blue_label, red_abs_cut_label, blue_abs_cut_label, red_unc_label, blue_unc_label, ra_cut, dec_cut, blue_abs_cut, red_abs_cut = data
        except ValueError as e:
            print(f"Error unpacking data: {e}")
            return
        
        # Combine the arrays into a single 2D array
        data_array = np.column_stack((blue_cut, blue_unc_cut, red_cut , red_unc_cut))
        full_data_array = np.column_stack((x_cut, y_cut, blue_cut, blue_unc_cut, red_cut, red_unc_cut, color_filtered, ra_cut, dec_cut, blue_abs_cut, red_abs_cut))

        # Dynamically generate the file names based on the object name and filter labels, save to "data" subdirectory
        file_suffix = f"{obj_name}_{threshold}pc_{self.blue_label}_{self.red_label}"
        file_name_npy = os.path.join(self.data_dir, f'{file_suffix}.err.npy')
        file_name_txt = os.path.join(self.data_dir, f'{file_suffix}.err.txt')
        full_file_name_npy = os.path.join(self.data_dir, f'{file_suffix}_full.npy')
        full_file_name_txt = os.path.join(self.data_dir, f'{file_suffix}_full.txt')

        # Define the header dynamically
        header = f'Blue_Magnitude({self.blue_label}) Blue_Magnitude_Uncertainty({self.blue_label}) Red_Magnitude({self.red_label}) Red_Magnitude_Uncertainty({self.red_label})'
        full_header = "X Y Blue_Mag Blue_Mag_Unc Red_Mag Red_Mag_Unc Color_Filtered RA DEC Blue_Abs_Mag Red_Abs_Mag"

        # Saving the Data to ASCII file for human readability
        np.savetxt(file_name_txt, data_array, fmt='%0.4f', header=header, comments='')
        np.savetxt(full_file_name_txt, full_data_array, fmt='%0.4f', header=full_header, comments='')
        np.save(full_file_name_npy, full_data_array)

        # Save the data to a NumPy binary file for programmatic access
        np.save(file_name_npy, data_array)

        print(f"Magnitudes and Uncertainties saved to {file_name_txt} and {file_name_npy}\n")
        print(f"Full dataset saved to {full_file_name_txt} and {full_file_name_npy}")
        print(f"Shape of data file (number of stars, columns):",np.shape(data_array))

    #Define each plot individually, allows greater control, ease of debugging, modularity. Con is tracking down all the proper
    #Things to pass to each plot.
    
    def set_axes_limits(self, data, lower_percentile=-50, upper_percentile=150):
        # Currently not using this definition, keeping for potential future use. Would allow automatically defining axes limits
        lower_bound = np.percentile(data, max(0, lower_percentile))
        upper_bound = np.percentile(data, min(100, upper_percentile))
        
        # Extend bounds beyond the data range
        if lower_percentile < 0:
            lower_bound -= (np.percentile(data, 50) - lower_bound) * abs(lower_percentile) / 100
        if upper_percentile > 100:
            upper_bound += (upper_bound - np.percentile(data, 50)) * (upper_percentile - 100) / 100
        
        return lower_bound, upper_bound

    def plot_cmd(self, color, magnitude, cmd_label, mag_label, title, include_title=True):
        cmd_label = cmd_label.replace('\n', ' ')
        #print(f"Debug: Length of color array: {len(color)}, Length of magnitude array: {len(magnitude)}")
        if len(color) != len(magnitude):
            raise ValueError("Color and magnitude arrays do not match in length.")
        fig = plt.figure(figsize=(9, 8))
        plt.scatter(color, magnitude)

        # Automatically set axes limits
        #x_lower, x_upper = self.set_axes_limits(color)
        #y_lower, y_upper = self.set_axes_limits(magnitude)
        #plt.xlim(x_lower, x_upper)
        #plt.ylim(y_upper, y_lower)  # Invert y-axis for magnitudes

        plt.xlim(-2, 4) #limits currently hardcoded by eye
        plt.ylim(16, 26)
        plt.gca().invert_yaxis()
        plt.xlabel(cmd_label, fontsize=12, ha='center')
        plt.ylabel(mag_label, fontsize=12)
        
        if include_title:
            plt.title(title)
        return fig

    def plot_cmd_density(self, color, magnitude, cmd_label, mag_label, title, include_title=True):
        cmd_label = cmd_label.replace('\n', ' ')
        # Calculate the point density
        xy = np.vstack([color, magnitude])
        kde = gaussian_kde(xy)
        density = kde(xy)

        fig, ax = plt.subplots(figsize=(8, 8))
        scatter = ax.scatter(color, magnitude, c=density, cmap='viridis', s=50)
        plt.colorbar(scatter, ax=ax, label='Density')
        ax.set_xlim(-2, 4)
        ax.set_ylim(16, 26)
        ax.invert_yaxis()
        ax.set_xlabel(cmd_label, fontsize=12)
        ax.set_ylabel(mag_label, fontsize=12)
        # Adjust tick label font size
        ax.tick_params(axis='both', which='major', labelsize=12)  # Change 14 to your desired font size
        
        if include_title:
            ax.set_title(title)
        return fig

    def plot_color_vs_abs_mag(self, color, abs_magnitude, cmd_label, mag_label, title, include_title=True):
        cmd_label = cmd_label.replace('\n', ' ')
        fig = plt.figure(figsize=(9, 8))
        plt.scatter(color, abs_magnitude)
        plt.xlim(-2, 4)  # Adjust these limits based on your data
        plt.ylim(min(abs_magnitude) - 0.5, max(abs_magnitude) + 0.5)  
        plt.gca().invert_yaxis() # Invert y-axis for magnitudes
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        plt.xlabel(cmd_label, fontsize=12, ha='center')
        plt.ylabel(mag_label, fontsize=12)
        
        if include_title:
            plt.title(title)
        plt.tight_layout()
        return fig

    def plot_mag_mag(self, blue_mag, red_mag, blue_label, red_label, title, include_title=True):
        fig = plt.figure(figsize=(8, 8))
        plt.scatter(blue_mag, red_mag)
        plt.xlim(16, 27) #limits currently hardcoded by eye
        plt.ylim(16, 26)
        plt.gca().invert_xaxis()
        plt.gca().invert_yaxis()
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        plt.xlabel(self.blue_label, fontsize=12, ha='center')
        plt.ylabel(self.red_label, fontsize=12)
        
        if include_title:
            plt.title(title)
        return fig

    def plot_mag_mag_density(self, blue_mag, red_mag, blue_label, red_label, title, include_title=True):
        # Calculate the point density
        xy = np.vstack([blue_mag, red_mag])
        kde = gaussian_kde(xy)
        density = kde(xy)

        fig, ax = plt.subplots(figsize=(8, 8))
        scatter = ax.scatter(blue_mag, red_mag, c=density, cmap='viridis', s=50)
        plt.colorbar(scatter, ax=ax, label='Density')
        ax.set_xlim(16, 27)  # Adjust these limits based on your data
        ax.set_ylim(16, 26)  # Adjust these limits based on your data
        ax.invert_xaxis()
        ax.invert_yaxis()
        ax.set_xlabel(self.blue_label, fontsize=12, ha='center')
        ax.set_ylabel(self.red_label, fontsize=12)
        # Adjust tick label font size
        ax.tick_params(axis='both', which='major', labelsize=12)  # Change 14 to your desired font size
        
        if include_title:
            ax.set_title(title)
        return fig

    def plot_uncertainty(self, mag, unc, mag_label, unc_label, title, include_title=True):
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.scatter(mag, unc)
        
        # Find the lowest magnitude point with uncertainty >= 0.10
        mag_0_10 = mag[unc >= 0.10]
        if len(mag_0_10) > 0:
            min_mag_0_10 = min(mag_0_10)
            ax.plot([16, min_mag_0_10], [0.10, 0.10], color='r', linestyle='--', label='0.10 Uncertainty Threshold')
            ax.plot([min_mag_0_10, min_mag_0_10], [-0.01, 0.10], color='r', linestyle='--')
            ax.text(0.95, 0.90, f'Mag @ 0.10 Unc: {min_mag_0_10:.2f}', ha='right', va='top', color='r', transform=ax.transAxes)

        # Find the lowest magnitude point with uncertainty >= 0.15
        mag_0_15 = mag[unc >= 0.15]
        if len(mag_0_15) > 0:
            min_mag_0_15 = min(mag_0_15)
            ax.plot([16, min_mag_0_15], [0.15, 0.15], color='g', linestyle='--', label='0.15 Uncertainty Threshold')
            ax.plot([min_mag_0_15, min_mag_0_15], [-0.01, 0.15], color='g', linestyle='--')
            ax.text(0.95, 0.85, f'Mag @ 0.15 Unc: {min_mag_0_15:.2f}', ha='right', va='top', color='g', transform=ax.transAxes)

        ax.set_xlim(16, 28)  # Adjust these limits based on your data
        ax.set_ylim(bottom=-0.01)  # Ensure the y-axis starts slightly below 0
        ax.set_xlabel(mag_label, fontsize=12, ha='center')
        ax.set_ylabel(unc_label, fontsize=12)
        # Adjust tick label font size
        ax.tick_params(axis='both', which='major', labelsize=14)  # Change 14 to your desired font size
        
        if include_title:
            ax.set_title(title)
        ax.legend()
        plt.tight_layout()
        return fig

    def plot_skycoord(self, ra, dec, sn_ra, sn_dec, obj_name, title, include_title=True):
        # This plot can output an offset for the x-axis and/or y-axis leading to more confusing tick labels
        base_ra = min(ra)
        base_offset = 114.32 - base_ra #Currently hardcoding offset by eye

        base_dec = min(dec)
        base_dec_offset = 65.6 - base_dec #Currently hardcoding offset for clean tick labels

        fig = plt.figure(figsize=(8, 8))
        plt.scatter(ra, dec, alpha=0.6)
        plt.scatter(sn_ra, sn_dec, color='red', marker='*', label=f"{obj_name}")
        plt.xlabel('RA (deg)', fontsize=12)
        plt.ylabel('Dec (deg)', fontsize=12)
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        if include_title:
            plt.title(title)
        plt.gca().xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x + base_offset:.3f}'))
        plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f'{y + base_dec_offset:.3f}'))
        plt.legend()
        return fig

    def plot_skycoord_sizing(self, ra, dec, sn_ra, sn_dec, obj_name, title, blue_mag, red_mag, include_title=True):
        # Calculate the size of each point relative to the average of blue and red magnitudes
        # Brighter stars should have larger sizes, so we invert the magnitude scale
        # Normalize sizes: The size calculation here is arbitrary and can be adjusted as needed
        avg_mag = (blue_mag + red_mag) / 2
        min_mag = np.min(avg_mag)
        sizes = 100 * (1 / (avg_mag - min_mag + 1))  # +1 to avoid division by zero

        # This plot can output an offset for the x-axis and/or y-axis leading to more confusing tick labels
        base_ra = min(ra)
        base_offset = 114.32 - base_ra  # Currently hardcoding offset by eye

        base_dec = min(dec)
        base_dec_offset = 65.6 - base_dec  # Currently hardcoding offset for clean tick labels

        fig = plt.figure(figsize=(8, 8))
        plt.scatter(ra, dec, s=sizes, alpha=0.6)  # Use calculated sizes
        plt.scatter(sn_ra, sn_dec, color='red', marker='*', label=f"{obj_name}", s=200)  # Supernova with fixed larger size
        plt.xlabel('RA (deg)', fontsize=12)
        plt.ylabel('Dec (deg)', fontsize=12)
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        
        if include_title:
            plt.title(title)
        plt.gca().xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x + base_offset:.3f}'))
        plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f'{y + base_dec_offset:.3f}'))
        plt.legend()
        return fig
    
    def read_saved_data(self, file_path):
        try:
            data = np.load(file_path, allow_pickle=True)
            return data
        except Exception as e:
            print(f"Error reading data from {file_path}: {e}")
            return None

    def plot_data_from_file(self, data, threshold, include_titles=True):
        print("Plotting data...")

        if self.pdf:
            title_suffix = '_notitles' if not include_titles else ""
            pdf_filename = os.path.join(self.data_dir, f"{self.obj_name}_{threshold}pc_plots_from_saved{title_suffix}.pdf")
            with PdfPages(pdf_filename) as pdf_pages:
                # Extract columns from the data array
                x_cut = data[:, 0]
                y_cut = data[:, 1]
                blue_cut = data[:, 2]
                blue_unc_cut = data[:, 3]
                red_cut = data[:, 4]
                red_unc_cut = data[:, 5]
                color_filtered = data[:, 6]
                ra_cut = data[:, 7]
                dec_cut = data[:, 8]
                blue_abs_cut = data[:, 9]
                red_abs_cut = data[:, 10]

                # Extract labels and other necessary data
                cmd_label = self.cmd_label
                blue_label = self.blue_label
                red_label = self.red_label
                blue_abs_cut_label = self.blue_abs_cut_label
                red_abs_cut_label = self.red_abs_cut_label
                blue_unc_label = self.blue_unc_label
                red_unc_label = self.red_unc_label

                # Call the plotting function with these arrays and labels
                self.generate_and_save_plots(pdf_pages, x_cut, y_cut, blue_cut, blue_unc_cut, red_cut, red_unc_cut, color_filtered, ra_cut, dec_cut, blue_abs_cut, red_abs_cut, cmd_label, blue_label, red_label, blue_abs_cut_label, red_abs_cut_label, blue_unc_label, red_unc_label, threshold, include_titles)
                print(f"Successfully generated the PDF file: {pdf_filename}!")
        else:
            # Extract columns from the data array

            x_cut = data[:, 0]
            y_cut = data[:, 1]
            blue_cut = data[:, 2]
            blue_unc_cut = data[:, 3]
            red_cut = data[:, 4]
            red_unc_cut = data[:, 5]
            color_filtered = data[:, 6]
            ra_cut = data[:, 7]
            dec_cut = data[:, 8]
            blue_abs_cut = data[:, 9]
            red_abs_cut = data[:, 10]

            # Extract labels and other necessary data
            cmd_label = self.cmd_label
            blue_label = self.blue_label
            red_label = self.red_label
            blue_abs_cut_label = self.blue_abs_cut_label
            red_abs_cut_label = self.red_abs_cut_label
            blue_unc_label = self.blue_unc_label
            red_unc_label = self.red_unc_label

            # Call the plotting function with these arrays and labels
            self.show_plots(pdf_pages, x_cut, y_cut, blue_cut, blue_unc_cut, red_cut, red_unc_cut, color_filtered, ra_cut, dec_cut, blue_abs_cut, red_abs_cut, cmd_label, blue_label, red_label, blue_abs_cut_label, red_abs_cut_label, blue_unc_label, red_unc_label, threshold)

    # Called with --pdf command. e.g. --phot --pdf [file.pdf]. Saves all figures above to single .pdf
    def generate_and_save_plots(self, pdf_pages, x_cut, y_cut, blue_cut, blue_unc_cut, red_cut, red_unc_cut, color_filtered, ra_cut, dec_cut, blue_abs_cut, red_abs_cut, cmd_label, blue_label, red_label, blue_abs_cut_label, red_abs_cut_label, blue_unc_label, red_unc_label, threshold, include_titles):
        #print(f"Debug: Length of data tuple: {len(data)}, Data: {data}")  # Debug statement
        #try:
        #    (x_cut, y_cut, blue_cut, red_cut, blue_unc_cut, red_unc_cut, color_filtered, cmd_label, self.red_label, self.blue_label, red_abs_cut_label, blue_abs_cut_label, red_unc_label, blue_unc_label, ra_filtered, dec_filtered, proximity_threshold, blue_abs_cut, red_abs_cut) = data
        #except ValueError as e:
        #    print(f"Error unpacking data: {e}")
        #    return

        # Quick check to make sure the arrays are the same length
        if len(color_filtered) != len(red_cut):
            raise ValueError(f"Mismatch in array lengths: color_filtered ({len(color_filtered)}) vs red_cut ({len(red_cut)})")
        
        # Formatting for plotting typically goes: x, y, xlabel, ylabel, title
        # Generate and save the CMD plot
        cmd_fig = self.plot_cmd(color_filtered, red_cut, cmd_label, self.red_label, f"{self.phot_file}: Cut CMD {threshold}pc", include_title=include_titles)
        pdf_pages.savefig(cmd_fig)
        plt.close(cmd_fig)  # Close the figure to free memory

        # Generate and save the CMD density plot
        cmd_density_fig = self.plot_cmd_density(color_filtered, red_cut, cmd_label, self.red_label, f"{self.phot_file}: Density CMD {threshold}pc", include_title=include_titles)
        pdf_pages.savefig(cmd_density_fig)
        plt.close(cmd_density_fig)

        # Generate and save the Color vs Absolute Magnitude plot
        color_abs_mag_fig = self.plot_color_vs_abs_mag(color_filtered, red_abs_cut, cmd_label, red_abs_cut_label, f"{self.phot_file}: Color vs Absolute Magnitude {threshold}pc", include_title=include_titles)
        pdf_pages.savefig(color_abs_mag_fig)
        plt.close(color_abs_mag_fig)

        # Generate and save the Magnitude-Magnitude plot
        magmag_fig = self.plot_mag_mag(blue_cut, red_cut, self.blue_label, self.red_label, f"{self.phot_file}: Cut Mag-Mag {threshold}pc", include_title=include_titles)
        pdf_pages.savefig(magmag_fig)
        plt.close(magmag_fig)

        # Generate and save the density mag-mag plot
        mag_mag_density_fig = self.plot_mag_mag_density(blue_cut, red_cut, self.blue_label, self.red_label, f"{self.phot_file}: Density Mag-Mag {threshold}pc", include_title=include_titles)
        pdf_pages.savefig(mag_mag_density_fig)
        plt.close(mag_mag_density_fig)

        # Generate and save the Blue Uncertainty plot
        blue_unc_fig = self.plot_uncertainty(blue_cut, blue_unc_cut, self.blue_label, blue_unc_label, f"{self.phot_file}: Cut Blue-Unc {threshold}pc", include_title=include_titles)
        pdf_pages.savefig(blue_unc_fig)
        plt.close(blue_unc_fig)

        # Generate and save the Red Uncertainty plot
        red_unc_fig = self.plot_uncertainty(red_cut, red_unc_cut, self.red_label, red_unc_label, f"{self.phot_file}: Cut Red-Unc {threshold}pc", include_title=include_titles)
        pdf_pages.savefig(red_unc_fig)
        plt.close(red_unc_fig)

        # Generate and save the Sky Coordinates plot
        skycoord_fig = self.plot_skycoord(ra_cut, dec_cut, self.sn_ra, self.sn_dec, self.obj_name, f"{self.phot_file} {threshold}pc", include_title=include_titles)
        pdf_pages.savefig(skycoord_fig)
        plt.close(skycoord_fig)

        # Generate and save the Skycoord fig, which adjusts the sizing of the points according to the mag of the star
        skycoord_size_fig = self.plot_skycoord_sizing(ra_cut, dec_cut, self.sn_ra, self.sn_dec, self.obj_name, f"{self.phot_file} {threshold}pc Mag-Sizing", blue_cut, red_cut, include_title=include_titles)
        pdf_pages.savefig(skycoord_size_fig)
        plt.close(skycoord_size_fig)

    # If you don't want to save the .pdf, but want to inspect a plot, simply use --phot
    def show_plots(self, pdf_pages, x_cut, y_cut, blue_cut, blue_unc_cut, red_cut, red_unc_cut, color_filtered, ra_cut, dec_cut, blue_abs_cut, red_abs_cut, cmd_label, blue_label, red_label, blue_abs_cut_label, red_abs_cut_label, blue_unc_label, red_unc_label, threshold):
        # Display the CMD plot
        cmd_fig = self.plot_cmd(color_filtered, red_cut, cmd_label, self.red_label, f"{self.phot_file}: Cut CMD {threshold}pc")
        cmd_fig.show()

        # Display CMD Density plot
        cmd_density_fig = self.plot_cmd_density(color_filtered, red_cut, cmd_label, self.red_label, f"{self.phot_file}: Density CMD {threshold}pc")
        cmd_density_fig.show()

        # Display the Color vs Absolute Magnitude plot
        color_abs_mag_fig = self.plot_color_vs_abs_mag(color_filtered, red_abs_cut, cmd_label, red_abs_cut_label, f"{self.phot_file}: Color vs Absolute Magnitude {threshold}pc")
        color_abs_mag_fig.show()

        # Display the Magnitude-Magnitude plot
        magmag_fig = self.plot_mag_mag(blue_cut, red_cut, self.blue_label, self.red_label, f"{self.phot_file}: Cut Mag-Mag {threshold}pc")
        magmag_fig.show()

        # Generate and display the density mag-mag plot
        mag_mag_density_fig = self.plot_mag_mag_density(blue_cut, red_cut, self.blue_label, self.red_label, f"{self.phot_file}: Density Mag-Mag {threshold}pc")
        mag_mag_density_fig.show()

        # Display the Blue Uncertainty plot
        blue_unc_fig = self.plot_uncertainty(blue_cut, blue_unc_cut, self.blue_label, blue_unc_label, f"{self.phot_file}: Cut Blue-Unc {threshold}pc")
        blue_unc_fig.show()

        # Display the Red Uncertainty plot
        red_unc_fig = self.plot_uncertainty(red_cut, red_unc_cut, self.red_label, red_unc_label, f"{self.phot_file}: Cut Red-Unc {threshold}pc")
        red_unc_fig.show()

        # Display the Sky Coordinates plot
        skycoord_fig = self.plot_skycoord(ra_cut, dec_cut, self.sn_ra, self.sn_dec, self.obj_name, f"{self.phot_file} {threshold}pc")
        skycoord_fig.show()

        # Display the SkyCoord sizing plot
        skycoord_size_fig = self.plot_skycoord_sizing(ra_cut, dec_cut, self.sn_ra, self.sn_dec, self.obj_name, f"{self.phot_file} {threshold}pc Mag-Sizing", blue_cut, red_cut)
        skycoord_size_fig.show()

def main():
    parser = argparse.ArgumentParser(description="Dolphot Automation Tool")
    parser.add_argument('--make', action='store_true', help='Run "make clean" and "make" in the dolphot makefile directory.')
    parser.add_argument('--param', action='store_true', help='Create the parameter file for dolphot')
    parser.add_argument('--customize-img', action='store_true', help='Customize individual image parameters interactively')
    parser.add_argument('--dolphot', action='store_true', help='Execute terminal commands for dolphot processing')
    parser.add_argument('--interactive', action='store_true', help='Enable interactive mode to confirm each dolphot step before proceeding')
    parser.add_argument('--dolphot_only', action='store_true', help='Assuming you have processed your images and made parameter file, execute dolphot separately')
    parser.add_argument('--calcsky_values', action='store_true', help='Provide custom calcsky values')
    parser.add_argument('--headerkeys', action='store_true', help='If you want to generate headerkey info without performing whole dolphot process')
    parser.add_argument('--phot', action='store_true', help='Make several plots from the output dolphot photometry')
    parser.add_argument('--save_data', action='store_true', help='Save quality and distance filtered datasets to .txt and .npy files')
    parser.add_argument('--no_titles', action='store_true', help='Generate plots without titles for publication')
    parser.add_argument('--pdf', type=str, help='Output PDF files to save the plots')
    args = parser.parse_args()

    organizer = DataFilterOrganizer()

    # Run 'make clean' and 'make' to initialize dolphot to use different photometric systems
    if args.make:
        # Read in config.ini to find {make_path}, used to find users path to dolphot makefile (typically found in ~/dolphot2.0/), code can potentially find the path without this being defined
        config = configparser.ConfigParser()
        config.read('config.ini')
        make_path = TerminalCommandExecutor.run_make(config)

    # Create dolphot parameter file. I think this needs to be folded into args.dolphot
    if args.param:
        executor = TerminalCommandExecutor()
        config = configparser.ConfigParser()
        config.read('config.ini')
        working_directory = os.getcwd()
        system_name = config['DOLPHOT_CONFIG']['system_name']
        obj_name = config['DOLPHOT_CONFIG']['obj_name']
        selected_files = executor.find_chip_files(working_directory, system_name)
        Nimg = len(selected_files) - 1
        print(f"Number of image files (Nimg): {Nimg}")
        
        # Customization step (if the --customize-img flag is used)
        customizations = {}
        if args.customize_img:
            customizations = executor.customize_image_parameters(selected_files)

        # Attempt to create or update the parameter file
        file_created, is_new_file = executor.write_parameter_file(selected_files, customizations, 'config.ini')
        print("Parameter file handling completed")

    # Execute the bulk of dolphot as automatically as possible
    if args.dolphot:
        #Activating with --interactive prompts breaks at each step for user to verify progress.
        #Otherwise, will run automatically with printouts along the way, only breaking when pivotal
        
        config = configparser.ConfigParser()
        working_directory = os.getcwd()
        if os.path.isfile('config.ini'):
            config.read('config.ini')
            if 'DOLPHOT_CONFIG' in config and 'obj_name' in config['DOLPHOT_CONFIG']:
                obj_name = config['DOLPHOT_CONFIG']['obj_name']
            else:
                print("The 'obj_name' parameter is not defined in 'DOLPHOT_CONFIG'.")
                obj_name = input("Enter the object(SN) name to define output files: ")
        else:
            print("Config file 'config.ini' is missing.")
            obj_name = input("Enter the object(SN) name to define output files: ")

        executor = TerminalCommandExecutor()

        # Function to prompt continuation based on --interactive flag
        def continue_prompt(message, always_ask=False):
            if args.interactive or always_ask:
                return input(message).lower() in ['y', 'yes']
            return True

        # Step 1: Initialize dolphot process with mask command
        if continue_prompt("Initialize dolphot process with mask command? (y/n): "):
            #Define 'system_name' in [DOLPHOT_CONFIG] (e.g. ACS_HRC), code will scrub relevant information for mask command
            system_name = config['DOLPHOT_CONFIG'].get('system_name')
            valid_systems = ['WFPC2', 'ACS', 'WFC3', 'ROMAN', 'NIRCAM', 'NIRISS', 'MIRI']
            system_choice = None

            if system_name:
                # Extract the base system name in case it includes additional descriptors
                base_system_name = system_name.split('_')[0]
                if base_system_name in valid_systems:
                    system_choice = base_system_name.lower()  # Use lower case for command consistency

            if system_choice:
                # Prep working directory to only include .fits files you want to process. Save backup of image files elsewhere
                mask_command = f"{system_choice}mask *.fits"
                if continue_prompt(f"Do you want to run '{mask_command}'? (y/n): "):
                    output_mask = f'{system_choice}mask_{obj_name}.log'
                    executor.execute_mask_command(mask_command, output_mask)
                    print(f"Mask command '{mask_command}' executed successfully, output logged in {output_mask}.")
            else:
                print("System name is not recognized or not specified in config.ini, (e.g. ACS_HRC). Please check your configuration.")
        else:
            print("Mask command initialization skipped by user.")

        # Step 2: Run the splitgroups command
        if continue_prompt("Proceed to run splitgroups? (y/n): "):
            # List of system names that should skip splitgroups inferred from dolphot manuals
            skip_splitgroups_systems = ['ACS_HRC', 'WFC3_IR', 'NIRCAM', 'NIRISS', 'MIRI', 'ROMAN']
            
            # Retrieve the system name from the configuration
            system_name = config['DOLPHOT_CONFIG'].get('system_name')
            
            # Check if the system name is in the list of systems that should skip splitgroups
            if system_name in skip_splitgroups_systems:
                print(f"{system_name} only has 1 chip, skipping splitgroups.")
            else:
                # This command is relatively simple, and consistent across ACS, WFC3, and WFPC2. For other systems, need to verify if running 
                # splitgroups breaks the process 
                additional_command = f'splitgroups *.fits >> splitgroups_{obj_name}.log'
                executor.execute_splitgroups_command(additional_command, f'splitgroups_{obj_name}.log')

        # Step 3: Run Calcsky, allow the user to alter the default values by using --calcsky_values
        if continue_prompt("Proceed to run Calcsky? (y/n): "):
            system_name = config['DOLPHOT_CONFIG'].get('system_name')

            # Define default calcsky values based on system_name
            if system_name in ['ACS_HRC', 'ACS_WFC', 'WFC3_UVIS']:
                calcsky_values = [15, 35, -128, 2.25, 2.00]
            elif system_name == 'WFC3_IR':
                calcsky_values = [10, 25, -64, 2.25, 2.00]
            elif system_name == 'WFPC2':
                calcsky_values = [10, 25, -50, 2.25, 2.00]
            else:
                calcsky_values = [15, 35, -128, 2.25, 2.00]

            # Prompt for custom calcsky values if the flag is set
            if args.calcsky_values:
                print(f"Enter custom calcsky values ({' '.join(map(str, calcsky_values))} are defaults):")
                try:
                    calcsky_values = [float(input(f"Enter value {i + 1}: ")) for i in range(5)]
                except ValueError:
                    print("Invalid input: Please enter numeric values.")
                    return  # Exit the function or ask for the input again as appropriate

            executor.execute_calcsky_commands(working_directory, obj_name, system_name, calcsky_values)

        # Step 4: Read-in processed image files, generate header key info file
        if continue_prompt("Proceed to generate header key info file? (y/n): "):
           # Now that the images have been processed, we can gather file information, useful step for making parameter file and log file
           output_file = f'headerkey_{obj_name}.info'
           organizer = DataFilterOrganizer(output_file)
           
           # Define patterns based on system_name
           if system_name in ['ACS_HRC', 'WFC3_IR', 'NIRCAM', 'NIRISS', 'MIRI', 'ROMAN']:
               # Include only .fits files that do not have extra identifiers like .sky.fits, .res.fits, etc.
               chip_files = [f for f in os.listdir(working_directory) if f.endswith('.fits') and not re.search(r'\.(sky|res|psf|chip1|chip2)\.fits$', f)]
           elif system_name == 'WFPC2':
               # Include files for chip1 through chip4
               chip_files = [f for f in os.listdir(working_directory) if re.match(r'.*\.chip[1-4]\.fits$', f)]
           else:
               # Find .chip1 and .chip2, default case for other systems
               chip_files = [f for f in os.listdir(working_directory) if re.match(r'.*\.chip[12]\.fits$', f)]

           # Exclude files with specific patterns
           chip_files = [f for f in chip_files if not re.search(r'\.(sky|res|psf)\.fits$', f)]

           if chip_files:
               organizer.organize_by_filter(chip_files)
               organizer.print_organized_list()
               print(f"Header key info file '{output_file}' created successfully!\n")
           else:
               print("No appropriate .fits files found in the working directory.")

        # Step 5: Create and edit dolphot parameter file
        if continue_prompt("Proceed to create/edit the dolphot parameter file? (y/n): ", args.interactive):
            print("Starting parameter file creation...")
            system_name = config['DOLPHOT_CONFIG'].get('system_name')
            obj_name = config['DOLPHOT_CONFIG'].get('obj_name')
            selected_files = executor.find_chip_files(working_directory, system_name)
            Nimg = len(selected_files) - 1
            print(f"Number of image files (Nimg): {Nimg}")
            customizations = {}
            #if you would like to change the shift or form for any individual file in parameter file, activate --customize_img
            if args.customize_img:
                customizations = executor.customize_image_parameters(selected_files)
            file_created, is_new_file = executor.write_parameter_file(selected_files, customizations, 'config.ini')
            if file_created:
                print(f"Parameter file '{obj_name}_phot.param' created/updated successfully!")
            else:
                print("Parameter file creation/update skipped or failed.")

        # Step 6: Execute dolphot, always ask before executing dolphot, regardless of interactive mode
        if continue_prompt("Proceed to execute dolphot? This can take a while and should not be interrupted. (y/n): ", always_ask=True):
            if file_created:  # Ensure parameter file was created/updated successfully
                param_file = f"{obj_name}_{system_name}_phot.param" #If you ran into error, and attempted to make parameter file manually, make sure file name matches this syntax
                executor.execute_dolphot(obj_name, param_file, working_directory, config)
            else:
                print("Parameter file was not created successfully. Dolphot execution aborted.")

    # Say you only want to execute 'dolphot' in the terminal, and already have everything else needed. Call this argument
    if args.dolphot_only:
        executor = TerminalCommandExecutor()
        config = configparser.ConfigParser()
        config.read('config.ini')
        working_directory = os.getcwd()
        obj_name = config['DOLPHOT_CONFIG'].get('obj_name')

        if not obj_name:
            print("Object name not found in config.ini. Please ensure it's correctly defined under [DOLPHOT_CONFIG].")
            exit(1)  # Exit if obj_name is not defined

        # If you run --dolphot_only, make sure your parameter file name matches this syntax
        param_file = f"{obj_name}_{system_name}_phot.param"

        # Check if the parameter file exists
        if os.path.isfile(param_file):
            executor.execute_dolphot(obj_name, param_file, working_directory)
        else:
            print(f"Parameter file '{param_file}' does not exist. Please ensure the file is in the current directory and named correctly.")
            exit(1)  # Exit if the parameter file does not exist

    # Say you ran up to 'splitgroups', and want to know more about your image files before executing dolphot, call this argument.
    if args.headerkeys:
        print("Headerkey mode activated.")

        config = configparser.ConfigParser()
        config.read('config.ini')
        working_directory = os.getcwd()
        system_name = config['DOLPHOT_CONFIG'].get('system_name')
        obj_name = config['DOLPHOT_CONFIG'].get('obj_name')  # Assumes config.ini exists and 'obj_name' is defined
        output_file = f'headerkey_{obj_name}.info'
        organizer = DataFilterOrganizer(output_file)

        # Define patterns based on system_name
        if system_name in ['ACS_HRC', 'WFC3_IR', 'NIRCAM', 'NIRISS', 'MIRI', 'ROMAN']:
            # Include only .fits files that do not have extra identifiers like .sky.fits, .res.fits, etc.
            chip_files = [f for f in os.listdir(working_directory) if f.endswith('.fits') and not re.search(r'\.(sky|res|psf|chip1|chip2)\.fits$', f)]
        elif system_name == 'WFPC2':
            # Include files for chip1 through chip4
            chip_files = [f for f in os.listdir(working_directory) if re.match(r'.*\.chip[1-4]\.fits$', f)]
        else:
            # Default case for other systems
            chip_files = [f for f in os.listdir(working_directory) if re.match(r'.*\.chip[12]\.fits$', f)]

        # Exclude files with specific patterns
        chip_files = [f for f in chip_files if not re.search(r'\.(sky|res|psf)\.fits$', f)]

        # Ensure files are found before processing
        if not chip_files:
            print("No appropriate .fits files found in the working directory.")
            return

        print("Detected image files:", chip_files)
        # Perform organization and print information
        organizer.organize_by_filter(chip_files)
        organizer.print_organized_list()
        print(f"Header key info file '{output_file}' created successfully!\n")

    # Say you executed --dolphot, and now you want to work with the photometry output, call --phot for plotting, --save_data to generate data file
    # Use both --phot --save_data to do both simultaneously
    if args.phot or args.save_data:
        # Takes in the photometry output of dolphot and performs various calculations and makes many plots
        # You should generate 'config.ini' file in the same directory as your script/photometry files
        # Under [DOLPHOT_CONFIG] define: obj_name, distance, and proximity_threshold_pc
        # If you have not run --dolphot before running this command, then also inlcude phot_file, ref_file in [DOLPHOT_CONFIG]
        working_directory = os.getcwd()
        executor = TerminalCommandExecutor() 
        config = configparser.ConfigParser()
        config.optionxform = str  # Preserve case sensitivity
        config.read('config.ini')
        
        # Update config with files if they exist in the working directory
        executor.update_config_with_files(config, working_directory)

        # Check if 'config.ini' is in the same directory as script
        # If missing, ask for the necessary information
        if not os.path.isfile('config.ini'):
            print("Config file is missing. If you'd like to proceed, we'll ask you for the necessary information")
            phot_file = input("Type in the .phot file name: ")
            ref_file = input("Type in the .fits reference image file name: ")
            obj_name = input("Enter the object(SN) name to query SIMBAD: ")
            distance = float(input("Enter the distance to the object (pc): "))
            proximity_thresholds_input = input("Enter the proximity thresholds in parsecs (pc), separated by commas: ")
            proximity_thresholds = [float(x) for x in proximity_thresholds_input.split(',')] if proximity_thresholds_input else [50, 100, 150]
        # Check if all the necessary parameters are defined in 'config.ini'
        # If some are missing, ask for the necessary information
        elif not all(ket in config['DOLPHOT_CONFIG'] for ket in ['phot_file', 'ref_file', 'obj_name']):
            print("One or more parameters are missing in the config file. Please input the missing values manually.")
            phot_file = config['DOLPHOT_CONFIG'].get('phot_file') or input("Type in the .phot file name: ")
            ref_file = config['DOLPHOT_CONFIG'].get('ref_file') or input("Type in the .fits reference image file name: ")
            obj_name = config['DOLPHOT_CONFIG'].get('obj_name') or input("Enter the object(SN) name to query SIMBAD: ")
            distance = float(config['DOLPHOT_CONFIG'].get('distance') or input("Enter the distance to the object (pc): "))
            # One exception is for proximity thresholds, which are not required to be defined to run the script
            proximity_thresholds_str = config['DOLPHOT_CONFIG'].get('proximity_threshold_pc') or input("Enter the proximity thresholds in parsecs (pc), separated by commas: ")
            proximity_thresholds = [float(x) for x in proximity_thresholds_str.split(',')] if proximity_thresholds_str else [50, 100, 150]
        #If 'config.ini' exists and all parameters are defined, use them
        else:
            phot_file = config['DOLPHOT_CONFIG']['phot_file']
            ref_file = config['DOLPHOT_CONFIG']['ref_file']
            obj_name = config['DOLPHOT_CONFIG']['obj_name']
            distance = float(config['DOLPHOT_CONFIG']['distance'])
            # Use default proximity thresholds of 50, 100, 150pc, if not defined
            proximity_thresholds_str = config['DOLPHOT_CONFIG'].get('proximity_threshold_pc', '50, 100, 150')
            proximity_thresholds = [float(x) for x in proximity_thresholds_str.split(',')]
            print(f"\nPhot File: {phot_file}")
            print(f"Ref File: {ref_file}")
            print(f"Object Name: {obj_name}")
            print(f"Distance: {distance}")
            print(f"Proximity Thresholds: {proximity_thresholds}")

        # Check for "data" subdirectory and create it, if it does not exist
        data_dir = os.path.join(os.getcwd(), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        plotter = PlotManager(config, obj_name, distance, pdf=args.pdf, proximity_thresholds=proximity_thresholds, data_dir=data_dir)
        prepared_data = plotter.prepare_data()
        
        if prepared_data is None:
            print("Error: Data preparation failed.")
            exit(1)

        if args.save_data:
            processed_data = plotter.process_data(prepared_data)
            red_label = prepared_data[13]
            blue_label = prepared_data[14]
            if processed_data is None:
                print("Error: No data to process.")
                exit(1)
            for data, threshold in zip(processed_data, plotter.proximity_thresholds):
                plotter.save_processed_data(data, obj_name, threshold, blue_label, red_label)

        # Execute plotting if --phot is specified
        if args.phot:
            for threshold in plotter.proximity_thresholds:
                full_file_name_npy = f"{plotter.obj_name}_{threshold}pc_{plotter.blue_label}_{plotter.red_label}_full.npy"
                data = plotter.read_saved_data(full_file_name_npy)
                if data is not None:
                    plotter.plot_data_from_file(data, threshold, not args.no_titles)
            else:
                print(f"Failed to load data for threshold {threshold} pc.")

if __name__ == "__main__":
    main()