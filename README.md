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

`Karlach.py` utilizes a `config.ini` file to manage various settings and parameters for the DOLPHOT photometry software. This configuration is specifically tailored for different imaging systems such as ACS_HRC, ACS_WFC, WFC3_UVIS, and others. Each section in the file corresponds to a specific instrument or module and contains parameters that control aspects of the photometry process, including aperture sizes, PSF settings, alignment, and noise handling.

### Structure of `config.ini`

- **[DOLPHOT_CONFIG]**: Contains global settings for the DOLPHOT run, including paths, object names, and reference files.
  - **System Name**: Define the photometric system used (e.g., ACS_WFC, WFC3_UVIS).
  - **Object Name**: Specify the name of the astronomical object being analyzed.
  - **Make Path**: Set the path to the DOLPHOT makefile directory.
  - **Phot File and Ref File**: Specify the names of the photometry and reference image files. These can be automatically filled in when executing `--phot` immediately after `--dolphot`.

- **[ACS_HRC]**: Parameters specific to the ACS/HRC system, controlling detailed aspects of the photometry process such as centroiding, sky measurement, PSF fitting, and image alignment.

- **[ACS_WFC], [WFC3_UVIS], [WFC3_IR], [WFPC2], [ROMAN], [NIRCAM], [NIRISS], [MIRI]**: These sections are expected to contain similar detailed parameters as seen in the ACS_HRC section, tailored for each specific instrument or module.

- **[Fake_Stars]**: Controls settings for generating and handling fake stars in the images, useful for testing and calibration purposes.

### Generating Parameters for Each System

Given the complexity and specific nature of the parameters under each system, it is recommended to refer to the DOLPHOT documentation to understand and generate the necessary parameters for each system. You can find detailed information and guidance on setting these parameters at the DOLPHOT website:

[Generate DOLPHOT Parameters](http://americano.dolphinsim.com/dolphot/)

This link provides access to manuals, module sources, and additional resources that can help in configuring `config.ini` for different systems and ensuring optimal settings for your photometry tasks.

## Examples

Here are some example commands to get you started:
bash
#### Run make clean, and make
```python Karlach.py --make```
#### Execute DOLPHOT processing
```python Karlach.py --dolphot --interactive```
#### Create dolphot parameter file by itself, assuming preprocessing is done.
```python Karlach.py --param```
#### Generate plots and save them to a PDF
```python Karlach.py --phot --pdf output.pdf```

## Installation

#### Clone the repository and install the required dependencies:

bash
```git clone https://github.com/josephguzman1994/IllithidNova.git```
```cd IllithidNova```
```pip install -r requirements.txt```

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your enhancements.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Contact

For any queries, you can reach out to [josephguzman1994](mailto:josephguzman1994@gmail.com).
