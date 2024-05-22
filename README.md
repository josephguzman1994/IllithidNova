# IllithidNova
IllithidNova is a place with multiple python tools for astronomers and astrophysicists. Currently contains Karlach.py which automates DOLPHOT processing, and Gale.py which automates queries to CMD 3.7 to download and unpack isochrones.

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
- `--interactive`: Enables interactive mode, prompting user confirmation before proceeding with each step.
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

## Dependencies
- Python 3.6+
- numpy
- matplotlib
- astropy
- astroquery
- scipy
- stwcs

Please find installation instructions towards the bottom of this README for more detail.

## Examples

Here are some example commands to get you started:
bash
#### Run make clean, and make
```python Karlach.py --make```
#### Execute DOLPHOT processing
```python Karlach.py --dolphot --interactive```
#### Create dolphot parameter file by itself, assuming preprocessing has been done separately.
```python Karlach.py --param```
#### Generate plots and save them to a PDF
```python Karlach.py --phot --pdf output.pdf```
#### Save dolphot photometry data with quality and distance masks
```python Karlach.py --save_data ```

## Notes
- Executing ```--make``` assumes you have dolphot2.0 installed, as well as the necessary PSF and PAM files for your images. Verify that your 'Makefile' is in your /dolphot2.0/ directory.
- In case you are unaware, executing some of the dolphot commands assumes you are in the dolphot2.0 directory. Therefore, you may want to edit your .bashrc file (or equivalent) to execute these commands elsewhere.
- At the moment, calcsky defaults to these values:  15 35 -128 2.25 2.00, which is only relevant for certain photometric systems. If you would like to use other values, activate ```--calcsky_values``` when executing the dolphot process.
- Testing of Karlach.py has only been completed with some ACS photometric systems. As a result, bugs may persist in other systems which will likely be worked out sooner, rather than later.

**Gale.py** is an advanced Python script designed for astronomers and astrophysicists to dynamically generate and download stellar isochrone data from the CMD 3.7 service hosted at `stev.oapd.inaf.it`. The script allows users to specify a range of parameters that define the characteristics of the isochrones they are interested in, such as age, metallicity, and photometric systems. It is currently optimized to use the PARSEC and COLIBRI models to fetch photometric system data, which it then unpacks into structured `.npy` files for further analysis.

## Key Features
- **Download Isochrone Data**: Downloads data directly from the CMD 3.7 interface.
  - **Dynamic Parameter Input**: Users can input specific parameters such as log age limits, metallicity [M/H] limits, and step sizes directly through the command line interface.
  - **Error Handling**: Provides robust error handling to manage and report issues like connection timeouts or data retrieval errors.
  - **Support for Multiple Photometric System Files**: Users can choose from predefined photometric systems, or add new ones to the `photometric_systems` dictionary, which maps system names to corresponding data file paths.
  - **Direct Data Download and Save**: Automatically downloads the corresponding `.dat` (relabeld to `.set`) file containing the isochrone data, and saves it locally, handling any necessary URL corrections and format validations.
- **Data Unpacking**: Converts downloaded `.set` files into `.npy` files, separating data into individual isochrones separated by age and metallicity.
- **Flexible Directory Handling**: Users can specify the output directory for unpacked files or use the default working directory.

## Configuration

- Users are prompted to enter specific parameters such as photometric system and age limits. These inputs dictate the scope of the data to be downloaded and processed.
- Users can modify the `photometric_systems` dictionary, or the `form_data` to add or change to their desired settings and use cases.
- Default values and error handling behaviors can be adjusted within the script.

## Dependencies

- Python 3.6+
- httpx
- asyncio
- BeautifulSoup
- numpy

## Notes
- Ensure that your internet connection is stable when downloading data from CMD 3.7.
- The script currently does not handle gzip-compressed files. If you need to download large datasets, consider modifying the script (under `form_data`) to handle gzip compression.

## Usage
To use `Gale.py`, you can utilize the following command-line arguments:

- `--download_iso`: Trigger the download of isochrone data.
- `--UnpackIsoSet`: Unpack the downloaded `.set` file into separate `.npy` files.
- `--isodir`: Specify the directory where unpacked data should be stored. If not utilized, defaults to the current working directory.

### Examples
1. **Downloading and Unpacking Data**
bash ```python3 Gale.py --download_iso --UnpackIsoSet```
This command downloads the isochrone data based on user inputs and immediately unpacks it into the current directory. Utilizes environment variables to minimize user input

2. **Unpacking Existing Data and Choosing Output Directory**
bash ```python3 Gale.py --UnpackIsoSet --isodir /path/to/directory```
This uses an existing `.set` file to unpack the data in a specified directory. If you ran ```--download_iso``` in the same terminal session, it will use the environment variables to automatically find the output files. Otherwise, you can manually define the necessary files with user input.

## Installation (For Karlach and Gale)

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
