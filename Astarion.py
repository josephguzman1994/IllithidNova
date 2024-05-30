import os
import itertools
import subprocess
import shutil
import argparse
import sys
import time

class StellarProcess:
    def __init__(self, params_file=None, output_dir=None, debug=False):
        # If no params file is provided, default to assume one is in the working directory
        if params_file is None:
            params_file = os.path.join(os.getcwd(), 'Params.dat')
        self.params_file = params_file
        
        # If no output directory is provided, use the working directory
        if output_dir is None:
            output_dir = os.getcwd()
        self.output_dir = output_dir
        
        self.debug = debug
        self.base_params = self.read_params()

        # Set a default initial_params_filename
        self.initial_params_filename = "Params.dat.InitialTables"

    def read_params(self):
        try:
            with open(self.params_file, 'r') as file:
                lines = file.readlines()
            return {line.split('=')[0].strip(): line.split('=')[1].strip() for line in lines if '=' in line}
        except FileNotFoundError:
            print(f"Error: The file {self.params_file} was not found.")
            return {}
        except Exception as e:
            print(f"An error occurred while reading {self.params_file}: {e}")
            return {}
        pass
        
    def validate_params(self):
        if not all(isinstance(age, float) for age in self.base_params.get('genlikeliages', [])):
            print("Error: All ages must be floats.")
            return False
        if not all(isinstance(z, float) for z in self.base_params.get('genlikelizs', [])):
            print("Error: All Z values must be floats.")
            return False
        if not all(isinstance(avtilde, float) for avtilde in self.base_params.get('genlikeliavtildes', [])):
            print("Error: All AvTilde values must be floats.")
            return False
        return True

    def write_params(self, updated_params):
        try:
            # Read existing parameters and update only the specified keys
            existing_params = self.read_params()
            existing_params.update(updated_params)

            # Define precision rules
            precision_rules = {
                'genlikeliages': "{:.2f}",
                'genlikelizs': "{:.2f}",
                'genlikeliavtildes': "{:.1f}",
                'genlikelimmin': "{:.1f}"
            }

            # Write all parameters back to the file
            with open(self.params_file, 'w') as file:
                for key, value in existing_params.items():
                    # Apply precision formatting if the key is in the precision rules
                    if key in precision_rules:
                        # Split the value by commas to handle lists of values
                        formatted_values = [precision_rules[key].format(float(v)) for v in value.split(',')]
                        file.write(f"{key} = {', '.join(formatted_values)}\n")
                    else:
                        file.write(f"{key} = {value}\n")
        except IOError as e:
            print(f"Failed to write to {self.params_file}: {e}")

    def generate_combinations(self, ages, zs, avtildes):
        return list(itertools.product(ages, zs, avtildes))
        
    # Inform the user if the subprocess was successful or not
    def run_subprocess(self, command, debug=False):
        """Run the command in a new terminal."""
        if debug:
            # For debug mode, wrap the debug information in single quotes to ensure it's treated as a single string
            terminal_command = f'gnome-terminal -- bash -c "echo \'{command}\' ; exec bash"'
        else:
            terminal_command = f'gnome-terminal -- bash -c "{command}; exec bash"'
        subprocess.Popen(terminal_command, shell=True)

    def process_tables(self):
        try:
            perfect_sample_av = self.read_params().get('perfectsampleav', 'False') == 'True'
            self.initial_params_filename = "Params.dat.Initial_TZA_tables" if perfect_sample_av else "Params.dat.Initial_TZ_tables"
            shutil.copy(self.params_file, os.path.join(os.path.dirname(self.params_file), self.initial_params_filename))

            ages = list(map(float, self.base_params['genlikeliages'].split(',')))
            zs = list(map(float, self.base_params['genlikelizs'].split(',')))
            avtildes = list(map(float, self.base_params['genlikeliavtildes'].split(',')))

            age_ranges = {
                4.0: [age for age in ages if age <= 7.80],
                2.0: [age for age in ages if 7.80 < age <= 8.60],
                0.5: [age for age in ages if age > 8.60]
            }

            desired_terminals = 6
            total_combinations = sum(len(self.generate_combinations(age_range, zs, avtildes)) for age_range in age_ranges.values())
            terminal_combinations = []

            # Generate and distribute combinations for each mass range
            for min_mass, age_range in age_ranges.items():
                combinations = self.generate_combinations(age_range, zs, avtildes)
                proportion = len(combinations) / total_combinations
                num_terminals_for_range = max(1, round(proportion * desired_terminals))

                # Adjust the number of terminals if the total exceeds the desired count
                if sum(num_terminals_for_range for _, _ in terminal_combinations) + num_terminals_for_range > desired_terminals:
                    num_terminals_for_range = max(1, desired_terminals - sum(num_terminals_for_range for _, _ in terminal_combinations))

                num_combinations_per_terminal = len(combinations) // num_terminals_for_range
                extra_combinations = len(combinations) % num_terminals_for_range

                current_index = 0
                for i in range(num_terminals_for_range):
                    if i < extra_combinations:
                        end_index = current_index + num_combinations_per_terminal + 1
                    else:
                        end_index = current_index + num_combinations_per_terminal

                    terminal_combinations.append((combinations[current_index:end_index], min_mass))
                    current_index = end_index

            # Process each terminal's combinations
            for i, (combinations, min_mass) in enumerate(terminal_combinations):
                unique_ages = sorted(set(age for age, _, _ in combinations))
                unique_zs = sorted(set(z for _, z, _ in combinations))
                unique_avtildes = sorted(set(av for _, _, av in combinations))

                chunk_params = {
                    'genlikeliages': ', '.join(map(str, unique_ages)),
                    'genlikelizs': ', '.join(map(str, unique_zs)),
                    'genlikeliavtildes': ', '.join(map(str, unique_avtildes)),
                    'genlikelimmin': f"{min_mass:.1f}"
                }

                self.write_params(chunk_params)

                command = f"python3 /home/joe/Research/StellarAges/StellarAges.py --Generatelikelihood"
                debug_info = f"Terminal {i+1}:\n" \
                            f"genlikelimmin = {min_mass}\n" \
                            f"genlikeliages = {chunk_params['genlikeliages']}\n" \
                            f"genlikelizs = {chunk_params['genlikelizs']}\n" \
                            f"genlikeliavtildes = {chunk_params['genlikeliavtildes']}\n" \
                            f"Combinations: {len(combinations)}"

                if self.debug:
                    print(debug_info)
                    self.run_subprocess(f"echo '{debug_info}'", debug=False)  # Open terminal and display debug info
                else:
                    self.run_subprocess(command)
                    time.sleep(6)

        except Exception as e:
            print(f"An error occurred in process_tables: {e}")
        print("Exiting process_tables")

# This class is responsible for managing the potential interruption process, including scanning the output files, determining the remaining combinations, and writing them to a .txt file
class ProcessManager:
    def __init__(self, stellar_process):
        self.stellar_process = stellar_process
        self.process_groups = []

    def scan_output_files(self):
        completed_files = set(os.listdir(self.stellar_process.output_dir))
        return completed_files

    def determine_remaining_combinations(self, completed_files):
        all_combinations = self.stellar_process.generate_combinations(
            list(map(float, self.stellar_process.base_params['genlikeliages'].split(','))),
            list(map(float, self.stellar_process.base_params['genlikelizs'].split(','))),
            list(map(float, self.stellar_process.base_params['genlikeliavtildes'].split(',')))
        )
        remaining_combinations = [
            combo for combo in all_combinations
            if f"LookUpTable_{combo[0]}_{combo[1]}_{combo[2]}.npz" not in completed_files
        ]
        return remaining_combinations

def main():
    parser = argparse.ArgumentParser(description="Process Stellar Ages")
    parser.add_argument("--MakeTables", action="store_true", help="Process tz, or tza tables")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode to print out processing steps without executing")
    parser.add_argument("--restart", action="store_true", help="Scan output files and suggest parameters to resume processing")
    args = parser.parse_args()

    output_dir = os.getcwd()
    stellar_process = StellarProcess(params_file =None, output_dir=output_dir, debug=args.debug)
    process_manager = ProcessManager(stellar_process)

    
    if args.restart:
        # Read the 'perfectsampleav' parameter from Params.dat
        perfect_sample_av = stellar_process.read_params().get('perfectsampleav', 'False') == 'True'

        # Determine the filename based on 'perfectsampleav' in Params.dat
        initial_params_filename = "Params.dat.Initial_TZA_tables" if perfect_sample_av else "Params.dat.Initial_TZ_tables"
        output_filename = "remaining_av_combinations.txt" if perfect_sample_av else "remaining_tz_combinations.txt"

        # Set the initial parameters file path
        initial_params_file = os.path.join(output_dir, initial_params_filename)
        stellar_process.params_file = initial_params_file
        initial_params = stellar_process.read_params()

        # Generate all possible combinations from initial parameters
        all_combinations = stellar_process.generate_combinations(
            list(map(float, initial_params['genlikeliages'].split(','))),
            list(map(float, initial_params['genlikelizs'].split(','))),
            list(map(float, initial_params['genlikeliavtildes'].split(',')))
        )

        # Define age ranges based on mmin criteria
        age_ranges = {
            4.0: [age for age in map(float, initial_params['genlikeliages'].split(',')) if age <= 7.80],
            2.0: [age for age in map(float, initial_params['genlikeliages'].split(',')) if 7.80 < age <= 8.60],
            0.5: [age for age in map(float, initial_params['genlikeliages'].split(',')) if age > 8.60]
        }

        # Scan existing output files
        completed_files = process_manager.scan_output_files()

        # Determine missing combinations for each mmin
        missing_combinations_by_mmin = {mmin: [] for mmin in age_ranges}
        for mmin, ages in age_ranges.items():
            for age in ages:
                for z in map(float, initial_params['genlikelizs'].split(',')):
                    for av in map(float, initial_params['genlikeliavtildes'].split(',')):
                        filename = f"LookUpTable_{age}_{z}_{av}.npz"
                        if filename not in completed_files:
                            missing_combinations_by_mmin[mmin].append((age, z, av))

        # Write remaining combinations to file grouped by mmin
        with open(output_filename, 'w') as file:
            file.write("Comparing the output files versus the initial parameters found, we recommend you set these parameters in Params.dat to pick up where you left off:\n\n")
            for mmin, combinations in missing_combinations_by_mmin.items():
                unique_ages = sorted(set(age for age, _, _ in combinations))
                unique_zs = sorted(set(z for _, z, _ in combinations))
                unique_avtildes = sorted(set(av for _, _, av in combinations))

                file.write(f"For genlikleimmin = {mmin}, use these parameters in Params.dat\n")
                file.write(f"genlikeliages = {unique_ages}\n")
                file.write(f"genlikelizs = {unique_zs}\n")
                file.write(f"genlikeliavtildes = {unique_avtildes}\n\n")

        print(f"To resume with remaining combinations, please see '{output_filename}'")
        return

    if args.debug:
        print("Debug mode activated...")

    try:
        if args.MakeTables:
            print("MakeTables argument detected, processing tables...")
            stellar_process.process_tables()
            print(f"Initial parameter configuration saved to: {os.path.join(os.path.dirname(stellar_process.params_file), stellar_process.initial_params_filename)}\n")
            
            
    except KeyboardInterrupt:
        print("Keyboard interrupt received, exiting.")
        sys.exit(0)

    if args.debug:
        print("Exiting debug mode.")

if __name__ == "__main__":
    main()