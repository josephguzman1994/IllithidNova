<div style="display: flex; align-items: right;">
  <div style="flex-grow: 1;">
    <h1>IllithidNova</h1>
    <p></p>
  </div>
  <div>
    <img src="https://github.com/josephguzman1994/IllithidNova/assets/98617911/ece65425-b8b6-420c-9d90-41e9775f14fa" alt="IllithidNova" width="300">
  </div>
</div>
IllithidNova is a place with multiple python tools for astronomers and astrophysicists. At the moment, it serves as a place for all the tools I have built to accomplish my specific research tasks, but perhaps you may find something of use for your projects. This repo currently contains Karlach.py which automates DOLPHOT processing, Gale.py which automates queries to CMD 3.7, Halsin.py which automates download queries to the MAST portal, and Astarion.py which automates processes for the code StellarAges.

## Contents

- [Karlach.py - DOLPHOT Automation Tool](#karlachpy---dolphot-automation-tool)
- [Gale.py - CMD 3.7 Isochrone Retrieval Tool](#galepy---cmd-37-isochrone-retrieval-tool)
- [Halsin.py - MAST Data Retrieval Tool](#halsinpy---mast-data-retrieval-tool)
- [Astarion.py - Stellar Ages Process Automation](#astarionpy---stellarages-process-automation)
- [Installation](#installation-for-karlach-gale-and-halsin)
- [License](#license)

<div style="display: flex; align-items: center;">
  <div style="flex-grow: 1;">
    <h1 style="display: inline;">Karlach.py - Dolphot Automation Tool</h1>
    <img src="https://github.com/josephguzman1994/IllithidNova/assets/98617911/a70fd20a-a1b1-4c36-907c-43509ac5c729" alt="Dolphot Tool" style="width: 125px;">
  </div>
</div>
  
`Karlach.py` is a Python script designed to automate various processes in the DOLPHOT photometry software, particularly tailored for handling astronomical data related to core-collapse supernovae. This tool simplifies the execution of DOLPHOT commands and organizes output data effectively.

<details>
  <summary>Click to Expand!</summary>
  
  ## Features
  
  - **Automated DOLPHOT Processing**: Simplifies the execution of DOLPHOT photometry tasks.
  - **Parameter File Creation**: Automatically generates and updates parameter files based on user input.
  - **Custom Image Parameter Customization**: Allows users to interactively customize image parameters.
  - **Data Visualization**: Generates plots from DOLPHOT output and saves them in various formats.
  - **Data Organization**: Organizes header key information and filters data based on quality and distance.
  
  ## Usage
  
  Below are the command-line arguments available in `Karlach.py`:
  
  - `--make`: Runs "make clean" and "make" in the DOLPHOT Makefile directory to prepare the system for DOLPHOT processing.
  - `--param`: Creates a parameter file for DOLPHOT based on the current configuration.
  - `--customize-img`: Enables interactive customization of individual image parameters.
  - `--dolphot`: Executes all of terminal commands necessary for DOLPHOT processing (i.e. mask -> splitgroups -> calcsky -> dolphot)
  - `--interactive`: Enables interactive mode, prompting user confirmation before proceeding with each step.
  - `--dolphot_only`: Executes DOLPHOT processing assuming all preparatory steps have been completed.
  - `--calcsky_values`: Allows the user to provide custom values for the calcsky command.
  - `--headerkeys`: Generates header key information from .fits files without performing the entire DOLPHOT process.
  - `--phot`: Generates plots from the DOLPHOT photometry output.
  - `--save_data`: Saves quality and distance filtered data sets to file.
  - `--pdf`: Specifies the plot outputs to PDF file, rather than display.
  
  ## Configuration
  
  `Karlach.py` utilizes a `config.ini` file to manage various settings and parameters for the DOLPHOT photometry software. This configuration is specifically tailored for different imaging systems such as ACS_HRC, ACS_WFC, WFC3_UVIS, and others. Each section in the file corresponds to a specific instrument or module and contains parameters that control aspects of the photometry process, including aperture sizes, PSF settings, alignment, and noise handling. An example `config.ini` is provided for you in the repo.
  
  ### Structure of `config.ini`
  
  - **[DOLPHOT_CONFIG]**: Contains global settings for the DOLPHOT run, including file paths, object names, and reference files.
    - **system_name**: Define the photometric system used (e.g., ACS_WFC, WFC3_UVIS).
    - **obj_name**: Specify the name of the astronomical object being analyzed. The code will attempt to query SIMBAD for relevant coordinates.
    - **make_path**: Set the path to your DOLPHOT makefile directory.
    - **distance**: in units of parsecs to the object of interest. Necessary for processing dolphot output, making distance mask, absolute magnitude plots, etc.
    - **phot_file and ref_file**: Specify the names of the photometry and reference image files. These can be automatically filled in when executing `--phot` immediately after `--dolphot`.
   
    - Below 'DOLPHOT_CONFIG', please define a section with keys and values for your chosen photometric system to generate the appropriate dolphot parameter file.
  
  - **Chosen Photometric System Section, e.g.: [ACS_HRC]**: Parameters specific to the ACS/HRC system, controlling detailed aspects of the photometry process such as centroiding, sky measurement, PSF fitting, and image alignment. Define each parameter as specified in the DOLPHOT manual, or user preference.
  
  - **[ACS_WFC], [WFC3_UVIS], [WFC3_IR], [WFPC2], [ROMAN], [NIRCAM], [NIRISS], [MIRI]**: Similarly, these sections are expected to contain various detailed parameters, tailored for each specific instrument or module. You may store your preferred system settings here as only the photometric system that matches the 'System Name' chosen above will be utilized.
  
  - **[Fake_Stars]**: Controls settings for generating and handling fake stars in the images, useful for testing and calibration purposes. There is currently no separate command / built in capabilities to handle artificial star tests, however if desired, one could alter the code to utilize the ```-dolphot_only``` command, as initiating fakestars is similar to executing 'dolphot', while utilizing the parameters one would presumably define under this section.
  
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
  #### Run make clean, and make (prepare to use new photometric system with DOLPHOT)
  ```python Karlach.py --make```
  #### Execute DOLPHOT processing
  ```python Karlach.py --dolphot --interactive```
  #### Generate the dolphot parameter file by itself, assuming preprocessing (mask, splitgroups, calcsky) have been done separately.
  ```python Karlach.py --param```
  #### Save dolphot photometry data with quality and distance masks, and plot the freshly made data sets to .pdf
  ```python Karlach.py --save_data --phot --pdf```
  
  ## Notes
  - Executing ```--make``` assumes you have dolphot2.0 installed, as well as the necessary PSF and PAM files for your images. Verify that your 'Makefile' is in your /dolphot2.0/ directory.
  - In case you are unaware, executing some of the dolphot commands assumes you are in the dolphot2.0 directory. Therefore, you may want to edit your .bashrc file (or equivalent) to execute these commands elsewhere.
  - At the moment, calcsky defaults to these values:  15 35 -128 2.25 2.00, which is only relevant for certain photometric systems. If you would like to use other values, activate ```--calcsky_values``` when executing the dolphot process.
  - Testing of Karlach.py ```--dolphot``` has thus far been completed with some ACS photometric systems. As a result, bugs may persist in other systems which will likely be worked out sooner, rather than later.
  - Currently ```--save_data``` assumes a default distance from the SN (or object of interest) of 50, 100, and 150 pc. Therefore ```--save_data``` generates 3 different sets of data simultaneously as the default. If you would like to use a different set of distances for the distance mask, please define in your config.ini file, 'proximity_threshold_pc = ' followed by your comma separated values of interest.
</details>

<div style="display: flex; align-items: center;">
  <div style="flex-grow: 1;">
    <h1 style="display: inline;">Gale.py - CMD 3.7 Isochrone Retrieval Tool</h1>
    <img src="https://github.com/josephguzman1994/IllithidNova/assets/98617911/6deed2a1-8f87-4058-8996-9fcb145bbd54" alt="CMD 3.7 Tool" style="width: 125px;">
  </div>
</div>

`Gale.py` is an advanced Python script designed for astronomers and astrophysicists to dynamically generate and download stellar isochrone data from the CMD 3.7 service hosted at `stev.oapd.inaf.it`. The script allows users to specify a range of parameters that define the characteristics of the isochrones they are interested in, such as age, metallicity, and photometric systems. It is currently optimized to use the PARSEC and COLIBRI models to fetch photometric system data, which it then unpacks into structured `.npy` files for further analysis.

<details>
  <summary>Click to Expand!</summary>

  ## Key Features
  - **Download Isochrone Data**: Downloads data directly from the CMD 3.7 interface.
    - **Dynamic Parameter Input**: Users can input specific parameters such as log age limits, metallicity [M/H] limits, and step sizes directly through the command line interface.
    - **Error Handling**: Provides robust error handling to manage and report issues like connection timeouts or data retrieval errors.
    - **Support for Multiple Photometric System Files**: Users can choose from predefined photometric systems, or add new ones to the `photometric_systems` dictionary, which maps system names to corresponding data file paths.
    - **Direct Data Download and Save**: Automatically downloads the corresponding `.dat` (relabeled to `.set`) file containing the isochrone data, and saves it locally, handling any necessary URL corrections and format validations.
  - **Data Unpacking**: Converts downloaded `.set` files into `.npy` files, separating data into individual isochrones separated by appropriate age, metallicity combinations.
  - **Flexible Directory Handling**: Users can specify the output directory for unpacked files or use the default working directory.
  - **Plotting Isochrones**: Provides functionality to plot isochrones by age or metallicity, and single isochrone diagrams.
  - **Maximum Isochrone Age Check**: Allows users to check the maximum isochrone age against table limits to ensure data integrity.

  ## Dependencies
  
  - Python 3.6+
  - httpx
  - asyncio
  - BeautifulSoup
  - numpy
  - matplotlib
  
  ## Configuration
  
  - Users are prompted to enter specific parameters such as photometric system and age limits. These inputs dictate the scope of the data to be downloaded and processed.
  - Users can modify the `photometric_systems` dictionary, or the `form_data` within the script to add or change to their desired settings and use cases.
  - Default values and error handling behaviors can be adjusted within the script.
  
  ## Usage
  To use `Gale.py`, you can utilize the following command-line arguments:
  
  - `--download_iso`: Trigger the download of isochrone data.
  - `--UnpackIsoSet`: Unpack the downloaded `.set` file into separate `.npy` files.
  - `--isodir`: Specify the directory where unpacked data should be stored. If not utilized, defaults to the current working directory.
  - `--plot_age_iso`: Reads in unpacked .npy files to plot isochrones for varying ages and a fixed metallicity.
  - `--plot_z_iso`: Reads in unpacked .npy files to  plot isochrones for varying metallicities and a fixed age.
  - `--plot_single_iso`: Reads in unpacked .npy file to plot a single isochrone for a given age and metallicity.
  - `--MaxIsoAge`: Check the maximum isochrone age against table limits.
  
  ### Examples
  1. **Downloading and Unpacking Data**
  bash ```python3 Gale.py --download_iso --UnpackIsoSet```
  
  &emsp; This command downloads the isochrone data based on user inputs and immediately unpacks it into the current directory. Utilizes environment variables to minimize user input  
  
  2. **Unpacking Existing Data and Choosing Output Directory**
  bash ```python3 Gale.py --UnpackIsoSet --isodir /path/to/directory```
  
  &emsp; This uses an existing `.set` file to unpack the data in a specified directory. If you ran ```--download_iso``` in the same terminal session, it will use the environment variables to automatically find the output files. Otherwise, you will be prompted manually define the necessary files with terminal input.
  
  ## Notes
  - Ensure that your internet connection is stable when downloading data from CMD 3.7
  - For downloading isochrones, the script currently does not handle gzip-compressed files. If you need to download large datasets, consider modifying the script (under `form_data`) to handle gzip compression.
</details>

<div style="display: flex; align-items: center;">
  <div style="flex-grow: 1;">
    <h1 style="display: inline;">Halsin.py - MAST Data Retrieval Tool</h1>
    <img src="https://github.com/josephguzman1994/IllithidNova/assets/98617911/3e589fb7-3253-41c1-90ad-8e527a3c0709" alt="HST MAST Tool" style="width: 100px;">
  </div>
</div>

`Halsin.py`: Is a python script that can query and download data products from the Mikulski Archive for Space Telescopes (MAST). Specifically formatted to query for HST science images and deep exposures. It allows users to specify a target, search radius, and other parameters to find and download relevant astronomical data files, intended for use with DOLPHOT.

<details>
  <summary>Click to Expand!</summary>

  ## Key Features
  - **Query MAST for specific astronomical targets.**
    - Filter results by instruments, exposure time, and product type.
    - Download selected data products automatically.
  
  ## Dependencies
  - Python 3.6+
  - astroquery
  - astropy
  - requests
  
  ## Usage
  To use `Halsin.py`, you can utilize the following command-line arguments:
  - `--hst_download`: Query MAST to download HST data products for specified targets. The script will download the selected files into a `downloads` directory within the same directory where the script is run.
  
  ## Examples
  1. **Downloading HST MAST Data**
  bash ```python3 Halsin.py --hst_download```
  This command will prompt the user to input a target name, then will proceed to automatically query MAST for relevant HST data products.
  
  ## Notes
  - Ensure that your internet connection is stable when downloading data from CMD 3.7
  - For downloading HST MAST data, there are several key assumptions which are currently hard-coded into the class `HST_MAST_Query`. The search filters are: datasets within 1 arcminute of the target, an exposure time greater than or equal to 1000 seconds (necessary for Stellar Ages), return Science images only, and only keep ACS, WFC3, WFPC1 and WFPC2 instruments. Then after selecting the datasets to download, it is currently hardcoded to only download calibrated data products, i.e. drz, drc, flc or flt image files (necessary for DOLPHOT).

</details>

## Installation (For Karlach, Gale and Halsin)

#### Clone the repository and install the required dependencies:

bash

```git clone https://github.com/josephguzman1994/IllithidNova.git```

```cd IllithidNova```

```pip install -r requirements.txt```

<div style="display: flex; align-items: center;">
  <div style="flex-grow: 1;">
    <h1 style="display: inline;">Astarion.py - StellarAges Process Automation</h1>
    <img src="https://github.com/josephguzman1994/IllithidNova/assets/98617911/b32038f6-3533-4294-a9e5-01feb7e63a02" alt="StellarAges Tool" style="width: 125px;">
  </div>
</div>

`Astarion.py` is a python script that automates some of the processing used in the code "[StellarAges](https://github.com/curiousmiah/StellarAges)", handling various tasks such as parameter validation, subprocess management, and data backup. It is currently designed to facilitate the generation of likelihood tables based on stellar parameters and supports functionalities like debugging and basic restarting processes with saved parameters.

<details>
  <summary>Click to Expand!</summary>

  ## Features
  
  - **Parameter Validation**: Ensures all input parameters (`genlikeliages`, `genlikelizs`, `genlikeliavtildes`) are of the correct type.
  - **Subprocess Management**: Automaically runs external commands in new terminal windows, allowing for parallel processing.
  - **Data Backup**: Automatically backs up initial parameter configurations before processing.
  - **Debug Mode**: Provides detailed information outputs without executing the main processing steps for user verification.
  - **Restart Capability**: Provides the user with the necessary information to restart the process using parameters from a backup file, helping to resume processing with the last known good configuration.
  
  ## Dependencies
  
  - Python 3.x
  - Standard Python libraries: `os`, `itertools`, `subprocess`, `shutil`, `argparse`, `sys`, `time`
  
  Ensure Python 3.x is installed on your system. This script does not require external Python packages outside of the Python Standard Library.
  
  ## Installation
  
  No installation is necessary. Simply download the script to your local machine.
  
  ## Usage
  
  Run the script from the command line by navigating to the directory containing the script and executing:
  bash
  `python Astarion.py --option`
  
  ### Options
  
  - `--MakeTables`: Generates likelihood tables based on the provided parameters in `Params.dat`. Opens up a desired number of terminals to parallelize this process efficiently.
  - `--debug`: Runs the script in debug mode, printing detailed processing steps without executing them.
  - `--restart`: Scans output files and suggests parameters to resume processing based on the initial backup.
  
  ### Examples
  
  To process tables with current parameters:
  `python Astarion.py --MakeTables`
  
  To run in debug mode (mimics ```--MakeTables``` behavior, but does not execute command):
  `python Astarion.py --MakeTables --debug`
  
  To retrieve necessary information to restart MakeTables:
  `python Astarion.py --restart`
  
  ## Notes
  - **File Not Found**: The script expects a `Params.dat` file in the working directory or specified path. Ensure this file exists before running. Follow the expected naming conventions for parameters found in StellarAges"
  - **Resource Limitations**: Generating these likelihood tables and running many subprocesses may consume significant system resources. Monitor system performance and adjust the `max_terminals` setting if necessary.

</details>


## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your enhancements.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Contact

For any queries, you can reach out to [josephguzman1994](mailto:josephguzman1994@gmail.com).
