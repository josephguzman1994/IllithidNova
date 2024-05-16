# IllithidNova

# Karlach.py - Dolphot Automation Tool

`Karlach.py` is a Python script designed to automate various processes in the DOLPHOT photometry software, particularly tailored for handling astronomical data related to core-collapse supernovae. This tool simplifies the execution of DOLPHOT commands and organizes output data effectively.

## Features

- **Automated DOLPHOT Processing**: Simplifies the execution of DOLPHOT photometry tasks.
- **Parameter File Creation**: Automatically generates and updates parameter files based on user input.
- **Custom Image Parameter Customization**: Allows users to interactively customize image parameters.
- **Data Visualization**: Generates plots from DOLPHOT output and saves them in various formats.
- **Data Organization**: Organizes header key information and filters data based on quality and distance.

## Usage

Below are the command-line arguments available in `Karlach.py`:

- `--make`: Runs "make clean" and "make" in the DOLPHOT makefile directory to prepare the system for DOLPHOT processing.
- `--param`: Creates a parameter file for DOLPHOT based on the current configuration.
- `--customize-img`: Enables interactive customization of individual image parameters.
- `--dolphot`: Executes a series of terminal commands for DOLPHOT processing.
- `--interactive`: Enables interactive mode, requiring user confirmation before proceeding with each step.
- `--dolphot_only`: Executes DOLPHOT processing assuming all preparatory steps have been completed.
- `--calcsky_values`: Allows the user to provide custom values for the calcsky command.
- `--headerkeys`: Generates header key information without performing the entire DOLPHOT process.
- `--phot`: Generates plots from the DOLPHOT photometry output.
- `--save_data`: Saves quality and distance filtered data to a file.
- `--pdf [file.pdf]`: Specifies the output PDF file to save the plots.

## Configuration

`Karlach.py` uses a `config.ini` file to manage various settings and parameters. Here's how you can use this file:

- **System Name**: Define the photometric system used (e.g., ACS_WFC, WFC3_UVIS).
- **Object Name**: Specify the name of the astronomical object being analyzed.
- **Make Path**: Set the path to the DOLPHOT makefile directory.
- **Phot File and Ref File**: Specify the names of the photometry and reference image files.

## Examples

Here are some example commands to get you started:
bash
Run make clean and make
python Karlach.py --make
Create a parameter file
python Karlach.py --param
Execute DOLPHOT processing
python Karlach.py --dolphot --interactive
Generate plots and save them to a PDF
python Karlach.py --phot --pdf output.pdf

## Installation

Clone the repository and install the required dependencies:

bash
git clone https://github.com/josephguzman1994/IllithidNova.git
cd IllithidNova
pip install -r requirements.txt

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your enhancements.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Contact

For any queries, you can reach out to [josephguzman1994](mailto:josephguzman1994@gmail.com).
