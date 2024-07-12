import httpx
import asyncio
import logging
from bs4 import BeautifulSoup
from io import BytesIO
import re
import os
import numpy as np
import matplotlib.pyplot as plt
import argparse

# Globally define get_datasource, so all classes can use it
# In Stellar Ages you need to define the 'Instrument' and 'Datasource'. This is redundant as the instrument defines the data source, so this definition maps the instruments to the appropriate data source
def get_datasource(instrument):
    hst_instruments = ['ACS_HRC', 'ACS_WFC', 'WFC3_UVIS', 'WFPC2']
    return 'HST' if instrument in hst_instruments else 'To Be Coded'

# This class handles interfacing with the webpage and submitting the appropriate request for isochrones
class PARSEC:
    def __init__(self, base_url="http://stev.oapd.inaf.it/cgi-bin/cmd"):
        self.base_url = base_url

    async def send_request(self, form_data):
        url = f"{self.base_url}/cgi-bin/cmd_{form_data['cmd_version']}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': url
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=form_data, headers=headers, timeout=180.0)
            return response

    async def download_dat_file(self, dat_file_url):
        """Download the actual .dat file from the extracted URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(dat_file_url)
            return response.text

    def find_dat_file_link(self, html_content):
        """Extract the .dat file link from the HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        link_tags = soup.find_all('a', href=True)
        dat_file_pattern = re.compile(r'output\d+\.dat$')
        for link in link_tags:
            if dat_file_pattern.search(link['href']):
                return link['href']
        return None

    def parse_errors(self, html_content):
        """Parse HTML content to find error messages."""
        soup = BeautifulSoup(html_content, 'html.parser')
        error_messages = soup.find_all(class_="error")
        if not error_messages:
            error_messages = soup.find_all('div', class_='error')
        for error in error_messages:
            print("Error Message from Server:", error.text)

    async def download_isochrone(self, form_data):
        """Download isochrone data and save it to a file."""
        response = await self.send_request(form_data)
        if response and response.status_code == 200:
            dat_file_url = self.find_dat_file_link(response.text)
            if dat_file_url:
                # Correct the URL by replacing '/cgi-bin/cmd' with '/tmp'
                dat_file_url = f"http://stev.oapd.inaf.it/tmp/{dat_file_url.split('/')[-1]}"
                print(f"Attempting to download from: {dat_file_url}")  # Debug print
                dat_content = await self.download_dat_file(dat_file_url)
                
                # Construct the output filename based on form_data
                photometric_system = form_data['photsys_file'].split('/')[-1].replace('tab_mag_', '').replace('.dat', '').replace('_', ' ').title().replace(' ', '_').upper()
                output_filename = f"IsoParsec_{form_data['track_parsec'].split('_')[-1]}_{photometric_system}_Age_{form_data['isoc_lagelow']}_{form_data['isoc_lageupp']}_{form_data['isoc_dlage']}_MH_{form_data['isoc_metlow']}_{form_data['isoc_metupp']}_{form_data['isoc_dmet']}.set"
                
                if dat_content.startswith('<!DOCTYPE HTML'):
                    print("Error: The downloaded content is an HTML page, not the expected .dat file.")
                else:
                    with open(output_filename, 'w') as file:
                        file.write(dat_content)
                    print(f"Data successfully saved to {output_filename}")
                    # Return necessary data for setting environment variables
                    return output_filename, form_data['photometric_input']
            else:
                print("Failed to find .dat file link")
        else:
            print("Failed to download data")
            if response:
                self.parse_errors(response.text)

    def _convert_to_table(self, html_content):
        """Convert HTML content to a table."""
        soup = BeautifulSoup(html_content, 'html.parser')
        table = []
        for row in soup.find_all('tr'):
            cols = row.find_all('td')
            table.append([ele.text.strip() for ele in cols])
        return table

# This class handles scrubbing the downloaded isochrones from CMD for the relevant information
class UnpackIsoSet:
    def __init__(self, isodir, instrument, datasource, isomodel='Parsec', photsystem=None, mags=None):
        self.isodir = isodir
        self.instrument = instrument
        self.datasource = datasource
        self.isomodel = isomodel
        self.photsystem = photsystem or instrument
        self.mags = mags

    def get_iso_index(self, mag):
        index_map = {
            'WFC3_UVIS': {'F438W': 33, 'F475W': 34, 'F555W': 35, 'F606W': 36, 'F814W': 39},
            'ACS_WFC': {'F435W': 28, 'F475W': 29, 'F555W': 30, 'F606W': 31, 'F814W': 34},
            'ACS_HRC': {'F435W': 32, 'F475W': 33, 'F555W': 35, 'F606W': 36, 'F814W': 41},
            'WFPC2': {'F439W': 34, 'F450W': 35, 'F555W': 36, 'F606W': 38, 'F814W': 43}
        }
        return index_map.get(self.photsystem, {}).get(mag, None)
    
    def extinction_factors(self, mag):
        factors = {
            'WFC3_UVIS': {'F438W': 1.34148, 'F475W': 1.20367, 'F555W': 1.04089, 'F814W': 0.587},
            'ACS_WFC': {'F435W': 1.33879, 'F475W': 1.21179, 'F555W': 1.03065, 'F606W': 0.90328, 'F814W': 0.59696},
            'ACS_HRC': {'F435W': 1.34370, 'F475W': 1.20282, 'F555W': 1.03202, 'F606W': 0.90939, 'F814W': 0.58595},
            'WFPC2': {'F439W': 1.34515, 'F450W': 1.27128, 'F555W': 1.00654, 'F606W': 0.86409, 'F814W': 0.60352}
        }
        return factors.get(self.photsystem, {}).get(mag, 1.0)
    
    def list_available_filters(self):
        filters_map = {
            'WFC3_UVIS': ['F438W', 'F475W', 'F555W', 'F606W', 'F814W'],
            'ACS_WFC': ['F435W', 'F475W', 'F555W', 'F606W', 'F814W'],
            'ACS_HRC': ['F435W', 'F475W', 'F555W', 'F606W', 'F814W'],
            'WFPC2': ['F439W', 'F450W', 'F555W', 'F606W', 'F814W']
        }
        return filters_map.get(self.photsystem, [])

    def read_iso_set(self, isosetfile):
        with open(isosetfile) as f:
            lines = f.readlines()

        if not self.mags:
            available_filters = self.list_available_filters()
            print("Available filters:")
            for idx, filt in enumerate(available_filters):
                print(f"{idx}: {filt}")

            blue_idx = int(input("Enter the index for the blue filter: "))
            red_idx = int(input("Enter the index for the red filter: "))

            self.mags = [available_filters[blue_idx], available_filters[red_idx]]

        blue, red = self.mags
        iblue = self.get_iso_index(blue)
        ired = self.get_iso_index(red)
        fblue = self.extinction_factors(blue)
        fred = self.extinction_factors(red)

        if iblue is None or ired is None:
            raise ValueError(f"Invalid magnitudes: {blue}, {red} for photometric system {self.photsystem}")

        # Currently hardcoding columns read in. icol format = Mini, Mass, LogL, LogTe, chosen blue and red filters
        # More filters available if necessary.
        icols = [3, 5, 6, 7, iblue, ired]

        # Below splits the combined isochrones, into Age, Metallicity .npy combinations
        isodata = []
        lastmh = -8.0
        lastlogage = 0.
        printisodata = False

        for line in lines:
            if line.strip()[0] != '#':
                temp = [float(i) for i in line.strip().split()]
                data = [temp[i] for i in icols]

                mh = temp[1]
                logage = temp[2]
                if (mh != lastmh or logage != lastlogage):
                    if (printisodata):
                        isodata = np.array(isodata)
                        isofile = f"{self.isodir}Iso_{lastlogage:.2f}_{lastmh:.2f}_0.0.npz"
                        print(isofile, np.shape(isodata))
                        np.savez(isofile, isodata=isodata, isomodel=self.isomodel, photsystem=self.photsystem, mags=self.mags, fblue=fblue, fred=fred)
                    isodata = []
                    printisodata = True
                isodata.append(data)
                lastmh = mh
                lastlogage = logage

        if printisodata:
            isodata = np.array(isodata)
            isofile = os.path.join(self.isodir, f"Iso_{lastlogage:.2f}_{lastmh:.1f}_0.0.npz")
            print(isofile, np.shape(isodata))
            np.savez(isofile, isodata=isodata, isomodel=self.isomodel, photsystem=self.photsystem, mags=self.mags, fblue=fblue, fred=fred)

class IsochroneAnalyzer:
    def __init__(self, isodir, instrument, datasource):
        self.isodir = isodir
        self.instrument = instrument
        self.datasource = datasource

    # Inform the user of the current instruments supported by the get_iso_index method
    def get_supported_instruments(self):
        """Return a list of instruments supported by the get_iso_index method."""
        index_map = {
            'WFC3_UVIS': {'F438W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8},
            'ACS_WFC': {'F435W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8},
            'ACS_HRC': {'F435W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8},
            'WFPC2': {'F439W': 34, 'F450W': 35, 'F555W': 36, 'F606W': 38, 'F814W': 43}
        }
        return list(index_map.keys())

    # Find the relevant indices needed for plotting isochrones and inspecting isochrone data
    def get_iso_index(self, mag):
        """Return the index of the magnitude based on the instrument and magnitude name."""
        index_map = {
            'WFC3_UVIS': {
                'F438W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8
            },
            'ACS_WFC': {
                'F435W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8
            },
            'ACS_HRC': {
                'F435W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8
            },
            'WFPC2': {
                'F439W': 4, 'F450W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8
            }
        }
        return index_map.get(self.instrument, {}).get(mag, None)
    
    # List all unique filters available across all instruments
    def list_available_filters(self):
        """List all unique filters available across all instruments."""
        index_map = {
            'WFC3': {
                'F438W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8
            },
            'ACS_WFC': {
                'F435W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8
            },
            'ACS_HRC': {
                'F435W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8
            },
            'WFPC2': {
                'F439W': 4, 'F450W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8
            }
        }
        unique_filters = set()
        for filters in index_map.values():
            unique_filters.update(filters.keys())
        print("Currently available filters:", ', '.join(sorted(unique_filters)))
        return unique_filters

    async def check_max_iso_age(self, ages, zs):
        # Ensure isodir is correctly set, default to current working directory if not
        if not hasattr(self, 'isodir') or not self.isodir:
            self.isodir = "./"  # Assuming files are in the current working directory

        mu = float(input("Enter the distance modulus (mu): "))
        table_bluemax = float(input("Enter the maximum blue table value (table_bluemax): "))
        self.list_available_filters()
        blue_mag = input("Enter the blue filter (e.g., F435W, F475W): ")

        iblue = self.get_iso_index(blue_mag)
        if iblue is None:
            print(f"Invalid magnitude for the instrument {self.instrument}.")
            return

        bluemin_global = -99.
        # Initialize ages we may want to exclude from the analysis
        excluded_ages = []
        outputs = []
        filename = f"CheckMaxIsoAge_{self.instrument}_{blue_mag}_{ages[0]}_{ages[-1]}.txt"
        with open(filename, 'w') as file:
            for age in ages:
                age_excluded = False
                for z in zs:
                    # Have found that age and metallicity may either be 1 or 2 decimal places, leading to confusion in finding files. Allow code to locate any combination of precision
                    combinations = [
                        (f"{float(age):.1f}", f"{float(z):.1f}"),
                        (f"{float(age):.2f}", f"{float(z):.1f}"),
                        (f"{float(age):.1f}", f"{float(z):.2f}"),
                        (f"{float(age):.2f}", f"{float(z):.2f}")
                    ]
                    file_found = False
                    for formatted_age, formatted_z in combinations:
                        isofile = os.path.join(self.isodir, f"IsoParsec1.2_{self.datasource}_{self.instrument}_{formatted_age}_{formatted_z}_0.0.npy")
                        if os.path.exists(isofile):
                            # Load the isochrone data and calculate the minimum blue magnitude
                            isodata = np.load(isofile)
                            bluemin = np.min(isodata[:, iblue] + mu)
                            bluemin_global = max(bluemin_global, bluemin)
                            output = f'age = {formatted_age} z = {formatted_z} bluemin = {bluemin}'
                            print(output)
                            outputs.append(output)
                            file_found = True
                            # If the minimum blue magnitude is greater than the maximum table value, exclude the age
                            if bluemin > table_bluemax:
                                age_excluded = True
                            break
                    if not file_found:
                        output = f"File not found: {isofile}"
                        print(output)
                        outputs.append(output)
                if age_excluded:
                    # Add the age to the list of excluded ages
                    excluded_ages.append(age)

            # Generate a list of recommended ages to use based upon the ages that have not been excluded
            recommended_ages = [age for age in ages if age not in excluded_ages]
            recommendation = f"Given that table_bluemax = {table_bluemax} and distance modulus = {mu}, we recommend you only use these ages for {blue_mag}: {', '.join(recommended_ages)}"
            print(recommendation)

            # Write to file with the recommendation first
            with open(filename, 'w') as file:
                file.write(recommendation + '\n')
                file.write(f'bluemin_global = {bluemin_global} table_bluemax = {table_bluemax}\n')
                for output in outputs:
                    file.write(output + '\n')

            print(f'bluemin_global = {bluemin_global} table_bluemax = {table_bluemax}\n')

    def plot_age_iso(self, ages, z, blue_mag, red_mag, isodir):
        plt.figure()
        # Use a colormap to generate colors dynamically
        cmap = plt.get_cmap('viridis')  # 'viridis' is a good choice for distinct colors, but you can use 'plasma', 'inferno', etc.
        num_ages = len(ages)
        
        for index, age in enumerate(ages):
            formatted_age = f"{float(age):.2f}"
            formatted_z = f"{float(z):.2f}"
            
            isofile = f"{isodir}/IsoParsec1.2_{self.datasource}_{self.instrument}_{formatted_age}_{formatted_z}_0.0.npy"
            
            if os.path.exists(isofile):
                isodata = np.load(isofile)
                blue_index = self.get_iso_index(blue_mag)
                red_index = self.get_iso_index(red_mag)
                color = isodata[:, blue_index] - isodata[:, red_index]
                magnitude = isodata[:, red_index]
                
                # Generate a color from the colormap based on the index
                plot_color = cmap(index / num_ages)
                plt.plot(color, magnitude, color=plot_color)
                plt.text(color[-1], magnitude[-1], f'{age}', color=plot_color, fontsize=5)
            else:
                print(f"File not found: {isofile}")

        plt.xlabel(f'{blue_mag} - {red_mag}')
        plt.ylabel(f'{red_mag}')
        plt.gca().invert_yaxis()
        plt.title(f'Age CMDs at [M/H] = {formatted_z}')
        plt.savefig(f'Iso_Ages_{ages[0]}_{ages[-1]}.png')
        plt.show()

    def plot_isochrones_by_metallicity(self, age, zs, blue_mag, red_mag, isodir):
        plt.figure()
        cmap = plt.get_cmap('plasma')
        num_zs = len(zs)
        for index, z in enumerate(zs):
            formatted_age = f"{float(age):.2f}"
            formatted_z = f"{float(z):.2f}"
            isofile = f"{isodir}/IsoParsec1.2_{self.datasource}_{self.instrument}_{formatted_age}_{formatted_z}_0.0.npy"
            if os.path.exists(isofile):
                isodata = np.load(isofile)
                blue_index = self.get_iso_index(blue_mag)
                red_index = self.get_iso_index(red_mag)
                color = isodata[:, blue_index] - isodata[:, red_index]
                magnitude = isodata[:, red_index]
                plot_color = cmap(index / num_zs)
                plt.plot(color, magnitude, color=plot_color)

                #Ran into an issue where the generated text ran outside the bounds of the plot. This is a fix.
                # Calculate thresholds as a percentage of the axis ranges
                x_range = plt.xlim()
                y_range = plt.ylim()

                x_threshold = 0.02 * (x_range[1] - x_range[0])
                y_threshold = 0.02 * (y_range[1] - y_range[0])

                # Determine offsets dynamically
                x_offset = -0.02 if color[-1] > (x_range[1] - x_threshold) else (0.02 if color[-1] < (x_range[0] + x_threshold) else 0)
                y_offset = -0.02 if magnitude[-1] > (y_range[1] - y_threshold) else (0.02 if magnitude[-1] < (y_range[0] + y_threshold) else 0)

                plt.text(color[-1] + x_offset, magnitude[-1] + y_offset, f'{z}', color=plot_color, fontsize=6, clip_on=True)
            else:
                print(f"File not found: {isofile}")
        plt.xlabel(f'{blue_mag} - {red_mag}')
        plt.ylabel(f'{red_mag}')
        plt.gca().invert_yaxis()
        plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        plt.title(f'Metallicity CMDs at log Age = {age}')
        plt.savefig(f'Iso_ZS_{zs[0]}_{zs[-1]}.png')
        plt.show()

    def plot_single_isochrone(self, age, z, blue_mag, red_mag, isodir):
        plt.figure()
        formatted_age = f"{float(age):.2f}"
        formatted_z = f"{float(z):.2f}"
        isofile = f"{isodir}/IsoParsec1.2_{self.datasource}_{self.instrument}_{formatted_age}_{formatted_z}_0.0.npy"
        if os.path.exists(isofile):
            isodata = np.load(isofile)
            blue_index = self.get_iso_index(blue_mag)
            red_index = self.get_iso_index(red_mag)
            color = isodata[:, blue_index] - isodata[:, red_index]
            magnitude = isodata[:, red_index]
            plt.plot(color, magnitude, label=f'Age = {age}, Z = {z}')
            plt.legend(fontsize=9)
        else:
            print(f"File not found: {isofile}")
        plt.xlabel(f'{blue_mag} - {red_mag}')
        plt.ylabel(f'{red_mag}')
        plt.gca().invert_yaxis()
        plt.title('Single Isochrone Color-Magnitude Diagram')
        plt.savefig(f'SingleIsoPlot_{age}_{z}.png')
        plt.show()

# Define the photometric_systems dictionary globally
# Currently setup to use HST cameras.
# Note: WFC3_UVIS = 200 to 1000 nm. e.g.F435W, the W refers to wide filters, setting as default when using WFC3_UVIS

photometric_systems = {
    'ACS_HRC': 'YBC_tab_mag_odfnew/tab_mag_acs_hrc.dat',
    'ACS_WFC': 'YBC_tab_mag_odfnew/tab_mag_acs_wfc_202101.dat',
    'WFC3_UVIS': 'YBC_tab_mag_odfnew/tab_mag_wfc3_202101_wide.dat',
    'WFPC2': 'YBC_tab_mag_odfnew/tab_mag_wfpc2.dat'
    # Add more mappings as needed
}

async def main():
    parser = argparse.ArgumentParser(description="Process isochrone data and interact with CMD website.")
    parser.add_argument('--UnpackIsoSet', action='store_true', help="Unpack an isochrone set.")
    parser.add_argument('--download_iso', action='store_true', help="Download isochrone data.")
    parser.add_argument('--MaxIsoAge', action='store_true', help="Check the maximum isochrone age against table limits.")
    parser.add_argument('--plot_age_iso', action='store_true', help="Plot isochrones for varying ages and a fixed metallicity.")
    parser.add_argument('--plot_z_iso', action='store_true', help="Plot isochrones for varying metallicities and a fixed age.")
    parser.add_argument('--plot_single_iso', action='store_true', help="Plot a single isochrone for a given age and metallicity.")
    parser.add_argument('--isodir', type=str, help="Choose directory to store unpacked data, defaults to current working directory.")
    args = parser.parse_args()

    # Assume the current working directory is the default isodir unless --isodir is specified
    isodir = args.isodir if args.isodir else os.getcwd()
    
    if args.download_iso:
        base_url = "http://stev.oapd.inaf.it/cgi-bin/cmd"
        parsec = PARSEC(base_url)
    
        '''
        User input for specific parameters. Currently has a few assumptions:
        
        1. That you want to use log ages, and [M/H] values. If you want to use linear ages or z, that is easily doable,
        but you would need to update the form_data and user input. 
        The keys for activating linear ages are: isoc_agelow','isoc_ageupp', and 'isoc_dage'. Also, set 'isoc_isagelog' = 0.
        Similarly, to activate z values, use 'isoc_zlow', 'isoc_zupp', and 'isoc_dz'. Also set 'isoc_ismetlog' = 0
        
        2. You do not want to gzip your file. This means you are restricted to the CMD's webpage of downloading 400 isochrones at one time.
        If you would like to change this, change 'output_gzip' = 1. (FYI this change will likely conflict with 'UnpackIsoSet' in StellarAges)
        
        3. You want to use CMD 3.7, Parsec v1.2S, and COLIBRI S_37. If you would like to change this, alter 'CMD', 'track_parsec', and 'track_colibri' in 'form_data'. As I don't know what potential future version you may
        want to use, you will need to track down the correct values yourself.

        4. In general, if you find you want to alter the default values / understand them better, inspect the 'form_data' and html on the webpage
        '''
        
        try:
            print("Let's attempt to download the desired isochrones by defining some parameters")
            
            print("Currently available photometric systems: ", list(photometric_systems.keys()))
            photometric_input = input("Enter the photometric system: ")
            photsys_file = photometric_systems.get(photometric_input.upper())
            
            if photsys_file is None:
                photsys_file = 'YBC_tab_mag_odfnew/tab_mag_wfc3_202101_wide.dat'  # Set default file
                print("Invalid photometric system. Defaulting to WFC3_UVIS file.")
            
            # User-defined inputs for relevant parameters
            isoc_lagelow = float(input("Enter the lower log age limit (isoc_lagelow): "))
            isoc_lageupp = float(input("Enter the upper log age limit (isoc_lageupp): "))
            isoc_dlage = float(input("Enter the log age step-size (isoc_dlage): "))
            isoc_metlow = float(input("Enter the lower metallicity [M/H] limit (isoc_metlow): "))
            isoc_metupp = float(input("Enter the upper metallicity [M/H] limit (isoc_metupp): "))
            isoc_dmet = float(input("Enter the metallicity [M/H] step-size (isoc_dmet): "))

            # Clear environment variables at the start of the script, in case running multiple times in a row
            os.environ.pop('AGES', None)
            os.environ.pop('ZS', None)

            # Compute age and metallicity arrays to store in environment variables
            ages = np.arange(isoc_lagelow, isoc_lageupp + isoc_dlage / 10, isoc_dlage)
            zs = np.arange(isoc_metlow, isoc_metupp + isoc_dmet / 10, isoc_dmet)

            # Convert arrays to comma-separated strings with two decimal precision and set environment variables
            os.environ['AGES'] = ','.join(f"{age:.2f}" for age in ages)
            os.environ['ZS'] = ','.join(f"{z:.2f}" for z in zs)
        
        except ValueError:
            print("Invalid input. Please enter a valid floating-point number.")
            return

        # All these values need to match the format found in the html form on the PARSEC webpage
        form_data = {
            'cmd_version': '3.7',
            'photsys_file': photsys_file,
            'photometric_input': photometric_input.upper(),
            'output_kind': '0',
            'output_evstage': '1',
            'output_gzip': '0',
            'track_parsec': 'parsec_CAF09_v1.2S',
            'track_colibri': 'parsec_CAF09_v1.2S_S_LMC_08_web',
            'photsys_version': 'YBCnewVega',
            'dust_sourceM': 'dpmod60alox40',
            'dust_sourceC': 'AMCSIC15',
            'extinction_av': '0.0',
            'extinction_coeff': 'constant',
            'extinction_curve': 'cardelli',
            'kind_LPV': '3',
            'imf_file': 'tab_imf/imf_kroupa_orig.dat',
            'isoc_isagelog': '1',
            'isoc_lagelow': isoc_lagelow,
            'isoc_lageupp': isoc_lageupp,
            'isoc_dlage': isoc_dlage,
            'isoc_ismetlog': '1',
            'isoc_metlow': isoc_metlow,
            'isoc_metupp': isoc_metupp,
            'isoc_dmet': isoc_dmet,
            'submit_form': 'Submit'
        }

        output_filename, instrument_input = await parsec.download_isochrone(form_data)

        if output_filename and instrument_input:
            # Set environment variables immediately after download, this will allow use of --UnpackIsoSet during same session without having to manually input values
            os.environ['ISOSETFILE'] = output_filename
            os.environ['INSTRUMENT'] = instrument_input
            os.environ['DATASOURCE'] = 'HST' if instrument_input in ['ACS_HRC', 'ACS_WFC', 'WFC3_UVIS', 'WFPC2'] else 'To Be Coded'
            print("Download complete.")

            # After setting the environment variables in the download_iso section
            # Print the environment variables to the terminal for user to verify correctness
            print("Environment Variables Set:")
            print("ISOSETFILE:", os.getenv('ISOSETFILE'))
            print("INSTRUMENT:", os.getenv('INSTRUMENT'))
            print("DATASOURCE:", os.getenv('DATASOURCE'))
            print("AGES:", os.getenv('AGES'))
            print("ZS:", os.getenv('ZS'))
            print("\n")
                        
            # Use the directory specified by --isodir or default to the directory of the downloaded file
            if not args.isodir:
                isodir = os.path.dirname(output_filename)
            
            if args.UnpackIsoSet:
                instrument_input = os.getenv('INSTRUMENT', 'Unknown Instrument')
                print(f"Proceeding to unpack isochrone data for {instrument_input}")
                datasource = get_datasource(instrument_input)
                unpacker = UnpackIsoSet(isodir, instrument_input, datasource, photsystem=instrument_input)
                
                available_filters = unpacker.list_available_filters()
                print("Available filters:")
                for idx, filt in enumerate(available_filters):
                    print(f"{idx}: {filt}")

                blue_idx = int(input("Enter the index for the blue filter: "))
                red_idx = int(input("Enter the index for the red filter: "))

                mags = [available_filters[blue_idx], available_filters[red_idx]]
                unpacker.mags = mags
                
                unpacker.read_iso_set(output_filename)
                print("Data unpacking complete.\n")
        else:
            print("Failed to download or incorrect data received.")

    # Can use UnpackIsoSet without download_iso if you have the necessary information.
    # If you ran --download_iso in the same terminal session, it can automatically fetch everything necessary with environment variables
    if args.UnpackIsoSet and not args.download_iso:
        instrument = os.getenv('INSTRUMENT', input("Enter the instrument (e.g., ACS_HRC, ACS_WFC): "))
        datasource = get_datasource(instrument)
        unpacker = UnpackIsoSet(isodir, instrument, datasource, photsystem=instrument)

        available_filters = unpacker.list_available_filters()
        print("Available filters:")
        for idx, filt in enumerate(available_filters):
            print(f"{idx}: {filt}")

        blue_idx = int(input("Enter the index for the blue filter: "))
        red_idx = int(input("Enter the index for the red filter: "))

        mags = [available_filters[blue_idx], available_filters[red_idx]]
        unpacker.mags = mags

        isosetfile = os.getenv('ISOSETFILE', input("Enter the isochrone set file name: "))
        unpacker.read_iso_set(isosetfile)

    # This argument will check the max isochrone age you should consider based on several parameters
    if args.MaxIsoAge:
        # Before using the environment variables in the MaxIsoAge section, print them to the terminal for user verification
        print("Environment Variables Retrieved:")
        print("INSTRUMENT:", os.getenv('INSTRUMENT'))
        print("DATASOURCE:", os.getenv('DATASOURCE'))
        print("AGES:", os.getenv('AGES'))
        print("ZS:", os.getenv('ZS'))
        print("\n")

        # Check if the environment variables are set, and only prompt for input if they are not.
        instrument = os.getenv('INSTRUMENT')
        if not instrument:
            analyzer = IsochroneAnalyzer(isodir, None, None)  # Temporary instance to access methods
            print("Currently available instruments for MaxIsoAge:", ', '.join(analyzer.get_supported_instruments()))
            instrument = input("Enter the instrument (e.g., ACS_HRC, ACS_WFC): ")

        # Datasource is defined by 'INSTRUMENT' whether that is fetched by environment variables or input manually
        datasource = get_datasource(instrument)

        ages = os.getenv('AGES').split(',') if os.getenv('AGES') else input("Enter comma-separated ages of interest: ").split(',')
        zs = os.getenv('ZS').split(',') if os.getenv('ZS') else input("Enter comma-separated [M/H] values of interest: ").split(',')

        analyzer = IsochroneAnalyzer(isodir, instrument, datasource)
        await analyzer.check_max_iso_age(ages, zs)

    # Plot isochrones of varying log ages while fixing metallicity. Currently assumes Av is 0.0
    if args.plot_age_iso:
        
        instrument = os.getenv('INSTRUMENT')
        if not instrument:
            analyzer = IsochroneAnalyzer(isodir, None, None)  # Temporary instance to access methods
            print("Currently available instruments for plotting:", ', '.join(analyzer.get_supported_instruments()))
            instrument = input("Enter the instrument (e.g., ACS_HRC, ACS_WFC): ")

        # Datasource is defined by 'INSTRUMENT' whether that is fetched by environment variables, or input manually
        datasource = get_datasource(instrument)
        
        analyzer = IsochroneAnalyzer(isodir, instrument, datasource)  # Adjust parameters as needed
        ages = os.getenv('AGES')
        if not ages:
            ages = input("Enter comma-separated ages of interest: ")
        ages = ages.split(',')

        z = input("Enter a fixed metallicity (default 0.00): ")
        z = z if z.strip() else "0.00"

        available_filters = analyzer.list_available_filters()
        blue_mag = input("Enter the blue filter (e.g., F435W): ")
        red_mag = input("Enter the red filter (e.g., F814W): ")

        analyzer.plot_age_iso(ages, z, blue_mag, red_mag, isodir)

    # Plot isochrones of varying metallicity while fixing log age. Currently assumes Av is 0.0
    if args.plot_z_iso:
        
        instrument = os.getenv('INSTRUMENT')
        if not instrument:
            analyzer = IsochroneAnalyzer(isodir, None, None)  # Temporary instance to access methods
            print("Currently available instruments for plotting:", ', '.join(analyzer.get_supported_instruments()))
            instrument = input("Enter the instrument (e.g., ACS_HRC, ACS_WFC): ")

        # Datasource is defined by 'INSTRUMENT' whether that is fetched by environment variables, or input manually
        datasource = get_datasource(instrument)
        
        analyzer = IsochroneAnalyzer(isodir, instrument, datasource)

        age = input("Enter a fixed log age: ")
        zs = os.getenv('ZS')
        if not zs:
            zs = input("Enter comma-separated metallicities of interest: ").split(',')
        
        available_filters = analyzer.list_available_filters()
        blue_mag = input("Enter the blue filter (e.g., F435W): ")
        red_mag = input("Enter the red filter (e.g., F814W): ")

        analyzer.plot_isochrones_by_metallicity(age, zs, blue_mag, red_mag, isodir)
    
    # Plot a single isochrone for a given age/metallicity, with given filters
    if args.plot_single_iso:
        
        instrument = os.getenv('INSTRUMENT')
        if not instrument:
            analyzer = IsochroneAnalyzer(isodir, None, None)  # Temporary instance to access methods
            print("Currently available instruments for plotting:", ', '.join(analyzer.get_supported_instruments()))
            instrument = input("Enter the instrument (e.g., ACS_HRC, ACS_WFC): ")

        # Datasource is defined by 'INSTRUMENT' whether that is fetched by environment variables, or input manually
        datasource = get_datasource(instrument)
        
        analyzer = IsochroneAnalyzer(isodir, instrument, datasource) 

        age = input("Enter the log age: ")
        z = input("Enter the [M/H] metallicity: ")

        available_filters = analyzer.list_available_filters()

        blue_mag = input("Enter the blue filter (e.g., F435W): ")
        red_mag = input("Enter the red filter (e.g., F814W): ")
        analyzer.plot_single_isochrone(age, z, blue_mag, red_mag, isodir)

def unpack_iso_set(isodir):
    # Find the environment variables. If missing, have user input the files they want to use.
    isosetfile = os.getenv('ISOSETFILE', input("Enter the isochrone set file name: "))
    instrument = os.getenv('INSTRUMENT', input("Enter the instrument (e.g., ACS_HRC, ACS_WFC): "))
    # Datasource is defined by 'INSTRUMENT' whether that is fetched by environment variables, or input manually
    datasource = get_datasource(instrument)
    
    unpacker = UnpackIsoSet(isodir, instrument, datasource)
    unpacker.read_iso_set(isosetfile)

if __name__ == "__main__":
    asyncio.run(main())