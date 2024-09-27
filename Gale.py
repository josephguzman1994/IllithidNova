import httpx
import asyncio
import logging
from bs4 import BeautifulSoup
from io import BytesIO
import re
import os
import zipfile
import time
import requests
import numpy as np
import matplotlib.pyplot as plt
import argparse
import pickle
import glob


# Globally define get_datasource, so all classes can use it
# In Stellar Ages you need to define the 'Instrument' and 'Datasource'. This is redundant as the instrument defines the data source, so this definition maps the instruments to the appropriate data source
def get_datasource(instrument):
    hst_instruments = ['ACS_HRC', 'ACS_WFC', 'WFC3_UVIS', 'WFPC2']
    return 'HST' if instrument in hst_instruments else 'To Be Coded'

class MISTDownloader:
    def __init__(self):
        self.photometry_systems = [
            "CFHTugriz", "DECam", "HST_ACSHR", "HST_ACSWF", "HST_WFC3", "HST_WFPC2",
            "IPHAS", "GALEX", "JWST", "LSST", "PanSTARRS", "SDSSugriz", "SkyMapper",
            "SPITZER", "SPLUS", "HSC", "Swift", "UBVRIplus", "UKIDSS", "UVIT", "VISTA",
            "WashDDOuvby", "WFIRST", "WISE"
        ]
        self.output_filename = None

    def download_isochrones(self, rotation, ages, composition, photometry_system, extinction):
        url = "https://waps.cfa.harvard.edu/MIST/iso_form.php"
        data = {
            "version": "1.2",
            "v_div_vcrit": "vvcrit0.4" if rotation == "0.4" else "vvcrit0.0",
            "age_scale": "log10",
            "age_type": "list",
            "age_list": ages,
            "FeH_value": composition,
            "output_option": "photometry",
            "output": photometry_system,
            "Av_value": extinction
        }
        session = requests.Session()
        response = session.post(url, data=data)
        soup = BeautifulSoup(response.text, 'html.parser')
        download_link = soup.find('a', text=lambda text: 'Click here' in text if text else False)
        if not download_link:
            print("Response content:", response.text)
            raise Exception("Couldn't find the link to download the data")
        download_url = "https://waps.cfa.harvard.edu/MIST/" + download_link['href']
        print(f"Downloading from: {download_url}")
        time.sleep(10)
        response = session.get(download_url)
        filename = f"isochrones_{rotation}_{composition}_{photometry_system}.zip"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded: {filename}")
        return filename

    def unzip_isochrones(self, zip_filename, ages):
        # Extract the base name without extension
        base_name = os.path.splitext(zip_filename)[0]
        
        # Parse the components from the filename
        parts = base_name.split('_')
        rotation, composition, photometry_system = parts[1], parts[2], '_'.join(parts[3:])
        
        # Get the min and max ages
        age_list = [float(age) for age in ages.split()]
        min_age, max_age = min(age_list), max(age_list)
        
        # Create the new base name for extracted files
        new_base_name = f"MIST_Rot_{rotation}_Z_{composition}_Age_{min_age:.1f}_{max_age:.1f}"
        
        extracted_files = []
        
        # Unzip the file
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            for file in zip_ref.namelist():
                # Get the name of the file inside the zip
                filename = os.path.basename(file)
                # If it's a .cmd file
                if filename.endswith('.cmd'):
                    # Construct the new filename
                    new_filename = f"{new_base_name}iso.cmd"
                    # Extract the file with the new name
                    with zip_ref.open(file) as zf, open(new_filename, 'wb') as f:
                        f.write(zf.read())
                    extracted_files.append(new_filename)
                # For other files, extract them with their original names
                elif filename:
                    with zip_ref.open(file) as zf, open(filename, 'wb') as f:
                        f.write(zf.read())
                    extracted_files.append(filename)
        
        print(f"Unzipped files: {', '.join(extracted_files)}")
        self.output_filename = extracted_files  # Store all extracted filenames
        return new_base_name

    def run(self):
        while True:
            rotation = input("Enter rotation (0.0 or 0.4): ")
            if rotation in ["0.0", "0.4"]:
                break
            print("Invalid input. Please enter 0.0 or 0.4.")
        ages = input("Enter space-separated log ages (e.g., 7.0 8.0 9.0): ")
        compositions_input = input("Enter space-separated composition values (e.g., -2.0 -1.0 0.0 0.5): ")
        compositions = [float(comp) for comp in compositions_input.split()]
        print("Available photometry systems:")
        for i, system in enumerate(self.photometry_systems, 1):
            print(f"{i}. {system}")
        while True:
            try:
                photometry_index = int(input("Enter the number corresponding to the desired photometry system: ")) - 1
                if 0 <= photometry_index < len(self.photometry_systems):
                    photometry_system = self.photometry_systems[photometry_index]
                    break
                else:
                    print("Invalid input. Please enter a number within the range.")
            except ValueError:
                print("Invalid input. Please enter a number.")
        extinction = "0.0"
        for composition in compositions:
            print(f"Downloading isochrones for composition: {composition}")
            zip_filename = self.download_isochrones(
                rotation=rotation,
                ages=ages,
                composition=str(composition),
                photometry_system=photometry_system,
                extinction=extinction
            )
            time.sleep(20)
        
            # Unzip the downloaded file
            self.unzip_isochrones(zip_filename, ages)

        print("All downloads and extractions completed.")
        return rotation


# This class handles interfacing with the webpage and submitting the appropriate request for isochrones
class PARSEC:
    def __init__(self, base_url="http://stev.oapd.inaf.it/cgi-bin/cmd"):
        self.base_url = base_url
        self.parsec_versions = {
            "1.2S": "parsec_CAF09_v1.2S",
            "2.0": "parsec_CAF09_v2.0"
        }
        self.rotation_options = {
            "0.00": "0.00",
            "0.30": "0.30",
            "0.60": "0.60",
            "0.80": "0.80",
            "0.90": "0.90",
            "0.95": "0.95",
            "0.99": "0.99"
        }

    async def send_request(self, form_data):
        url = f"{self.base_url}/cgi-bin/cmd_{form_data['cmd_version']}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': url
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=form_data, headers=headers, timeout=180.0)
            return response

    async def download_dat_file(self, url):
        """Download the .dat file from the given URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                content = response.text
                if len(content) < 1000:  # Arbitrary small size to check if file is too small
                    print(f"Warning: Downloaded file seems too small ({len(content)} characters)")
                    print("File content:", content)
                return content
            else:
                print(f"Failed to download .dat file. Status code: {response.status_code}")
                return None

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
                dat_file_url = f"http://stev.oapd.inaf.it/tmp/{dat_file_url.split('/')[-1]}"
                dat_content = await self.download_dat_file(dat_file_url)
                
                if dat_content:
                    if dat_content.startswith('<!DOCTYPE HTML'):
                        print("Error: The downloaded content is an HTML page, not the expected .dat file.")
                        print("HTML content:", dat_content[:500])  # Print first 500 characters of the HTML
                    else:
                        # Check the actual metallicities and ages in the data
                        metallicities = set()
                        ages = set()
                        for line in dat_content.split('\n'):
                            if not line.startswith('#'):
                                parts = line.split()
                                if len(parts) > 2:
                                    metallicities.add(float(parts[1]))  # [M/H] is in the second column
                                    ages.add(float(parts[2]))  # log(age) is in the third column
                        
                        print(f"Actual metallicities in the data: {sorted(metallicities)}")
                        print(f"Actual ages in the data: {sorted(ages)}")

                        # Construct the output filename
                        photometric_system = form_data['photsys_file'].split('/')[-1].replace('tab_mag_', '').replace('.dat', '').replace('_', ' ').title().replace(' ', '_').upper()
                        photometric_system_parts = photometric_system.split('_')
                        photometric_system_clean = '_'.join([part for part in photometric_system_parts if not part.isdigit()])
                        
                        rotation = form_data.get('track_omegai', 'NoRot')
                        rotation_str = f"Rot_{rotation}" if rotation != 'NoRot' else ""

                        age_range = f"{min(ages):.2f}_{max(ages):.2f}"
                        mh_range = f"{min(metallicities):.2f}_{max(metallicities):.2f}"

                        output_filename = f"IsoParsec_{form_data['track_parsec'].split('_')[-1]}_{photometric_system_clean}_{rotation_str}_Age_{age_range}_MH_{mh_range}.set"
            
                        with open(output_filename, 'w') as file:
                            file.write(dat_content)
                        print(f"Data successfully saved to {output_filename}")
                        return output_filename, form_data['photometric_input']
                else:
                    print("Failed to download .dat file content")
            else:
                print("Failed to find .dat file link")
                print("Response content:", response.text[:500])  # Print first 500 characters of the response
        else:
            print("Failed to download data")
            if response:
                self.parse_errors(response.text)
        return None, None

    def _convert_to_table(self, html_content):
        """Convert HTML content to a table."""
        soup = BeautifulSoup(html_content, 'html.parser')
        table = []
        for row in soup.find_all('tr'):
            cols = row.find_all('td')
            table.append([ele.text.strip() for ele in cols])
        return table

extdict = {
    'Parsec': {
        'WFC3_UVIS': {
            'F218W': 1.663430, 'F225W': 1.653126, 'F275W': 1.472632, 'F336W': 1.652791,
            'F390W': 1.399138, 'F438W': 1.341482, 'F475W': 1.203670, 'F555W': 1.040890,
            'F606W': 0.928989, 'F814W': 0.587000, 'F850LP': 0.483688
        },
        'ACS_WFC': {
            'F435W': 1.338790, 'F475W': 1.211790, 'F555W': 1.030650, 'F606W': 0.903280,
            'F814W': 0.596960
        },
        'ACS_HRC': {
            'F435W': 1.343700, 'F475W': 1.202820, 'F555W': 1.032020, 'F606W': 0.909390,
            'F814W': 0.585950
        },
        'WFPC2': {
            'F439W': 1.345150, 'F450W': 1.271280, 'F555W': 1.006540, 'F606W': 0.864090,
            'F814W': 0.603520
        },
        'UBVRIJHK': {
            'U': 1.550000, 'B': 1.310000, 'V': 1.000000, 'R': 0.750000, 'I': 0.480000,
            'J': 0.290000, 'H': 0.180000, 'K': 0.120000
        },
        'Gaia': {'G': 0.836270, 'BP': 1.083370, 'RP': 0.634390}
    },
    'Parsec2.0': {
        'WFC3_UVIS': {
            'F218W': 1.663430, 'F225W': 1.653126, 'F275W': 1.472632, 'F336W': 1.652791,
            'F390W': 1.399138, 'F438W': 1.341482, 'F475W': 1.203670, 'F555W': 1.040890,
            'F606W': 0.928989, 'F814W': 0.587000, 'F850LP': 0.483688
        },
        'ACS_WFC': {
            'F435W': 1.338790, 'F475W': 1.211790, 'F555W': 1.030650, 'F606W': 0.903280,
            'F814W': 0.596960
        },
        'ACS_HRC': {
            'F435W': 1.343700, 'F475W': 1.202820, 'F555W': 1.032020, 'F606W': 0.909390,
            'F814W': 0.585950
        },
        'WFPC2': {
            'F439W': 1.345150, 'F450W': 1.271280, 'F555W': 1.006540, 'F606W': 0.864090,
            'F814W': 0.603520
        },
        'UBVRIJHK': {
            'U': 1.550000, 'B': 1.310000, 'V': 1.000000, 'R': 0.750000, 'I': 0.480000,
            'J': 0.290000, 'H': 0.180000, 'K': 0.120000
        },
        'Gaia': {'G': 0.836270, 'BP': 1.083370, 'RP': 0.634390}
    },
    'MIST': {
        'WFC3_UVIS': {
            'F218W': 1.663430, 'F225W': 1.653126, 'F275W': 1.472632, 'F336W': 1.652791,
            'F390W': 1.399138, 'F438W': 1.341482, 'F475W': 1.203670, 'F555W': 1.040890,
            'F606W': 0.928989, 'F814W': 0.587000, 'F850LP': 0.483688
        },
        'ACS_WFC': {
            'F435W': 1.338790, 'F475W': 1.211790, 'F555W': 1.030650, 'F606W': 0.903280,
            'F814W': 0.596960
        },
        'ACS_HRC': {
            'F435W': 1.343700, 'F475W': 1.202820, 'F555W': 1.032020, 'F606W': 0.909390, 'F814W': 0.585950
        },
        'WFPC2': {
            'F439W': 1.345150, 'F450W': 1.271280, 'F555W': 1.006540, 'F606W': 0.864090,
            'F814W': 0.603520
        },
        'UBVRI': {
            'U': 1.550000, 'B': 1.310000, 'V': 1.000000, 'R': 0.750000, 'I': 0.480000
        },
        'Gaia': {'G': 0.836270, 'BP': 1.083370, 'RP': 0.634390}
    }
}

isoindexdict = {
    'Parsec': {
        'WFC3_UVIS': {'F218W': 28, 'F225W': 29, 'F275W': 30, 'F336W': 31, 'F390W': 32, 'F438W': 33, 'F475W': 34, 'F555W': 35, 'F606W': 36, 'F814W': 39, 'F850LP': 40},
        'ACS_WFC': {'F435W': 28, 'F475W': 29, 'F555W': 30, 'F606W': 31, 'F814W': 34},
        'ACS_HRC': {'F435W': 32, 'F475W': 33, 'F555W': 35, 'F606W': 36, 'F814W': 41},
        'WFPC2': {'F439W': 34, 'F450W': 35, 'F555W': 36, 'F606W': 38, 'F814W': 43},
        'UBVRIJHK': {'U': 28, 'B': 29, 'V': 30, 'R': 31, 'I': 32, 'J': 33, 'H': 34, 'K': 35},
        'Gaia': {'G': 28, 'BP': 29, 'RP': 30}
    },
    'Parsec2.0': {
        'WFC3_UVIS': {'F218W': 35, 'F225W': 36, 'F275W': 37, 'F336W': 38, 'F390W': 39, 'F438W': 40, 'F475W': 41, 'F555W': 42, 'F606W': 43, 'F814W': 46, 'F850LP': 47},
        'ACS_WFC': {'F435W': 35, 'F475W': 36, 'F555W': 37, 'F606W': 38, 'F814W': 41},
        'ACS_HRC': {'F435W': 39, 'F475W': 40, 'F555W': 42, 'F606W': 43, 'F814W': 48},
        'WFPC2': {'F439W': 41, 'F450W': 42, 'F555W': 43, 'F606W': 45, 'F814W': 50},
        'UBVRIJHK': {'U': 35, 'B': 36, 'V': 37, 'R': 38, 'I': 39, 'J': 40, 'H': 41, 'K': 42},
        'Gaia': {'G': 35, 'BP': 36, 'RP': 37}
    },
    'MIST': {
        'WFC3_UVIS': {'F218W': 7, 'F225W': 8, 'F275W': 9, 'F336W': 10, 'F390W': 11, 'F438W': 12, 'F475W': 13, 'F555W': 14, 'F606W': 15, 'F814W': 16, 'F850LP': 17},
        'ACS_WFC': {'F435W': 7, 'F475W': 8, 'F555W': 9, 'F606W': 10, 'F814W': 11},
        'ACS_HRC': {'F220W': 9, 'F250W': 10, 'F330W': 11, 'F344N': 12, 'F435W': 13, 'F475W': 14,
                    'F502N': 15, 'F550M': 16, 'F555W': 17, 'F606W': 18, 'F625W': 19, 'F658N': 20,
                    'F660N': 21, 'F775W': 22, 'F814W': 23, 'F850LP': 24, 'F892N': 25},
        'WFPC2': {'F439W': 7, 'F450W': 8, 'F555W': 9, 'F606W': 10, 'F814W': 11},
        'Stroemgren': {'b': 17, 'y': 18},
        'UBVRI-Gaia': {'U': 9, 'B': 10, 'V': 11, 'R': 12, 'I': 13, 'J': 14, 'H': 15, 'G': 30, 'BP': 31, 'RP': 32}
    }
}

# This class handles scrubbing the downloaded isochrones from CMD for the relevant information
class UnpackIsoSet:
    def __init__(self, base_dir, instrument, datasource, isomodel='Parsec', photsystem=None, mags=None, rotation = 0.0):
        self.base_dir = base_dir
        self.instrument = instrument
        self.datasource = datasource
        self.isomodel = isomodel
        self.photsystem = photsystem or instrument
        self.mags = mags
        self.rotation = rotation
        self.params = {}
        self.isodir = base_dir
        self.analyzer = IsochroneAnalyzer(base_dir, instrument, datasource)

    def get_parameters(self):
        self.params['isodir'] = self.base_dir
        self.params['isomodel'] = self.isomodel
        self.params['photsystem'] = self.photsystem
        self.params['instrument'] = self.instrument
        self.params['datasource'] = self.datasource

        available_filters = self.analyzer.list_available_filters(self.isomodel, self.params.get('isosetfile'))
        if not available_filters:
            print(f"No filters available for {self.isomodel} model with {self.instrument} instrument.")
            return

        print("Available filters:")
        for idx, filt in enumerate(available_filters):
            print(f"{idx}: {filt}")
        
        if self.mags is None:
            while True:
                try:
                    blue_idx = int(input("Enter the index for the blue filter: "))
                    red_idx = int(input("Enter the index for the red filter: "))
                    self.mags = [available_filters[blue_idx], available_filters[red_idx]]
                    break
                except IndexError:
                    print("Invalid index. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")

        self.params['mags'] = self.mags

    def get_output_dir(self):
        if self.isomodel == 'Parsec':
            model_dir = 'Parsec_v1.2S'
        elif self.isomodel == 'Parsec2.0':
            model_dir = 'Parsec2.0'
        else:
            model_dir = self.isomodel

        return os.path.join(self.base_dir, 'Isochrones', model_dir, self.photsystem)

    def get_iso_index(self, mag=None):
        if self.isomodel not in isoindexdict or self.photsystem not in isoindexdict[self.isomodel]:
            return {}
        if mag:
            return isoindexdict[self.isomodel][self.photsystem].get(mag, None)
        return isoindexdict[self.isomodel][self.photsystem]
    
    def extinction_factors(self, mag):
        if self.isomodel not in extdict or self.photsystem not in extdict[self.isomodel]:
            return 1.0
        return extdict[self.isomodel][self.photsystem].get(mag, 1.0)
    
    def list_available_filters(self):
        if self.isomodel not in isoindexdict or self.photsystem not in isoindexdict[self.isomodel]:
            return []
        return list(isoindexdict[self.isomodel][self.photsystem].keys())

    def read_iso_set(self, isosetfile):
        self.params['isosetfile'] = isosetfile
        
        # Only call get_parameters() if mags haven't been set yet
        if self.mags is None:
            self.get_parameters()  # This will prompt for filter selection
        else:
            # If mags are already set, just update the other parameters
            self.params['isodir'] = self.base_dir
            self.params['isomodel'] = self.isomodel
            self.params['photsystem'] = self.photsystem
            self.params['instrument'] = self.instrument
            self.params['datasource'] = self.datasource
            self.params['mags'] = self.mags

        print(f"Reading isochrone set file: {isosetfile}")
        print(f"Isomodel: {self.isomodel}")

        output_dir = self.get_output_dir()
        os.makedirs(output_dir, exist_ok=True)

        if self.isomodel in ['Parsec', 'Parsec2.0']:
            self.read_iso_set_parsec(isosetfile, output_dir)
        elif self.isomodel == 'MIST':
            self.read_iso_set_mist(isosetfile, output_dir)
        else:
            raise ValueError(f"Unsupported isomodel: {self.isomodel}")
        
    def read_iso_set_parsec(self, isosetfile, output_dir):
        #print("Starting to read Parsec isochrone set")
        with open(isosetfile, 'r') as f:
            lines = f.readlines()
        nlines = len(lines)
        #print(f"Read {nlines} lines from the file")

        blue = self.mags[0]
        red = self.mags[1]
        isomodel = self.isomodel
        photsystem = self.photsystem
        magindices = list(isoindexdict[isomodel][photsystem].values())
        fblue = extdict[isomodel][photsystem][blue]
        fred = extdict[isomodel][photsystem][red]

        #print(f"Mag indices: {magindices}")
        #print(f"Extinction factors: blue={fblue}, red={fred}")

        # 3 = Mini = 0
        # 5 = Mass = 1
        # 6 = logL = 2
        # 7 = logTe = 3
        icols = [3, 5, 6, 7]

        # Create a dictionary for columns in isofile.
        colsindex = len(icols)
        indexdict = {'Mini': 0, 'Mass': 1, 'LogL': 2, 'logT': 3}
        for key in isoindexdict[isomodel][photsystem]:
            indexdict[key] = colsindex
            colsindex += 1

        # Save the dictionary to a file.
        indexdictfile = os.path.join(output_dir, 'indexdict.pk')
        with open(indexdictfile, 'wb') as f:
            pickle.dump(indexdict, f)

        icols.extend(magindices)

        iiso = 0
        #lastmh = -8.0
        #lastlogage = 0.
        lastmh = None
        lastlogage = None
        printisodata = False  # Don't print in the first unique isochrone.
        isodata = []

        for i in range(nlines):
            if not lines[i].strip().startswith('#'):
                temp = [float(ii) for ii in lines[i].strip().split()]
                data = [temp[ii] for ii in icols]

                mh = temp[1] + 0.  # Adding 0. to make sure that 0. is positive not -0.
                logage = temp[2]
                if (mh != lastmh) or (logage != lastlogage):
                    # The start of a new isochrone
                    if printisodata:
                        isodata = np.array(isodata)
                        isofile = os.path.join(output_dir, f'Iso_{lastlogage:.2f}_{lastmh:.2f}_{self.rotation:.2f}_0.0.npz')
                        print(f"Saving isochrone file: {isofile}, shape: {np.shape(isodata)}")
                        np.savez(isofile, isodata=isodata, isomodel=isomodel, photsystem=photsystem, indexdict=indexdict, fblue=fblue, fred=fred, rotation=self.rotation)
                    isodata = []
                    # Print the previous isochrone from now on.
                    printisodata = True
                isodata.append(data)
                lastmh = mh
                lastlogage = logage

        # Write the last isochrone to file
        if isodata:
            isodata = np.array(isodata)
            isofile = os.path.join(output_dir, f'Iso_{lastlogage:.2f}_{lastmh:.2f}_{self.rotation:.2f}_0.0.npz')
            print(f"Saving final isochrone file: {isofile}, shape: {np.shape(isodata)}")
            np.savez(isofile, isodata=isodata, isomodel=isomodel, photsystem=photsystem, indexdict=indexdict, fblue=fblue, fred=fred, rotation=self.rotation)

        print("Finished reading Parsec isochrone set")

    def read_iso_set_mist(self, isosetfile, output_dir):
        with open(isosetfile) as f:
            lines = f.readlines()

        blue, red = self.mags
        isomodel = self.isomodel
        photsystem = self.photsystem

        # Get the correct indices for the selected filters
        blue_index = isoindexdict[isomodel][photsystem][blue.split('_')[-1]]
        red_index = isoindexdict[isomodel][photsystem][red.split('_')[-1]]

        # Get the extinction factors
        fblue = extdict[isomodel][photsystem].get(blue.split('_')[-1], 1.0)
        fred = extdict[isomodel][photsystem].get(red.split('_')[-1], 1.0)

        icols = [2, 3, 6, 4]  # Mini, Mass, logL, logTe
        icols.extend([blue_index, red_index])

        indexdict = {'Mini': 0, 'Mass': 1, 'LogL': 2, 'logT': 3, blue: 4, red: 5}

        indexdictfile = os.path.join(output_dir, 'indexdict.pk')
        with open(indexdictfile, 'wb') as f:
            pickle.dump(indexdict, f)

        isodata = []
        lastmh = None
        lastlogage = None
        printisodata = False

        for line in lines:
            if len(line.strip()) > 0 and line.strip()[0] != '#':
                temp = [float(ii) for ii in line.strip().split()]
                data = [temp[ii] for ii in icols]

                mh = float(temp[7])
                logage = float(temp[1])
                if mh != lastmh or logage != lastlogage:
                    if printisodata:
                        isodata = np.array(isodata)
                        isofile = os.path.join(output_dir, f'Iso_{float(lastlogage):.2f}_{float(lastmh):.2f}_{float(self.rotation):.2f}_0.0.npz')
                        print(f"Saving isochrone file: {isofile}, shape: {np.shape(isodata)}")
                        np.savez(isofile, isodata=isodata, isomodel=isomodel, photsystem=photsystem, 
                                indexdict=indexdict, fblue=fblue, fred=fred, rotation=float(self.rotation))
                    isodata = []
                    printisodata = True
                isodata.append(data)
                lastmh = mh
                lastlogage = logage

        if printisodata:
            isodata = np.array(isodata)
            isofile = os.path.join(output_dir, f'Iso_{float(lastlogage):.2f}_{float(lastmh):.2f}_{float(self.rotation):.2f}_0.0.npz')
            print(f"Saving final isochrone file: {isofile}, shape: {np.shape(isodata)}")
            np.savez(isofile, isodata=isodata, isomodel=isomodel, photsystem=photsystem, 
                    indexdict=indexdict, fblue=fblue, fred=fred, rotation=float(self.rotation))

        print(f"Finished processing {isofile}")

    @classmethod
    def unpack_isochrone(cls, file, isomodel, base_dir='/home/joe/Research', rotation = 0.0):
        # Get all unique instruments/photsystems from isoindexdict
        all_instruments = set()
        for model in isoindexdict.values():
            all_instruments.update(model.keys())
        all_instruments = sorted(all_instruments)

        print(f"\nAttempting to unpack file: {file}")

        # Present the list of available instruments/photsystems
        print("Available instruments/photsystems:")
        for idx, inst in enumerate(all_instruments):
            print(f"{idx}: {inst}")

        while True:
            try:
                inst_idx = int(input("Please enter the desired index for the instrument/photsystem: "))
                instrument = all_instruments[inst_idx]
                photsystem = instrument
                break
            except (ValueError, IndexError):
                print("Invalid input. Please enter a valid index.")
        
        datasource = get_datasource(instrument)
        
        unpacker = cls(base_dir, instrument, datasource, isomodel, photsystem=photsystem, rotation=rotation)
        
        # Ask for filter indices
        available_filters = unpacker.list_available_filters()
        print("Available filters:")
        for idx, filt in enumerate(available_filters):
            print(f"{idx}: {filt}")

        while True:
            try:
                blue_idx = int(input("Enter the index for the blue filter: "))
                red_idx = int(input("Enter the index for the red filter: "))
                unpacker.mags = [available_filters[blue_idx], available_filters[red_idx]]
                break
            except (ValueError, IndexError):
                print("Invalid input. Please enter valid indices.")
        
        # Process the file
        unpacker.read_iso_set(file)

    @staticmethod
    def extract_rotation(filename):
        # For MIST and Parsec2.0 files
        match = re.search(r'Rot_(\d+\.\d+)', filename)
        if match:
            return float(match.group(1))
        # For Parsec1.2S files (always 0.0)
        elif 'v1.2S' in filename:
            return 0.0
        else:
            return 0.0 # Default to 0.0 if no rotation found
        # If no rotation found in filename
        return None

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
            'WFPC2': {'F439W': 4, 'F450W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8}
        }
        return list(index_map.keys())

    # Find the relevant indices needed for plotting isochrones and inspecting isochrone data
    def get_iso_index(self, mag, mags):
        """Return the index of the magnitude based on the mags list."""
        indices = np.where(mags == mag)
        if len(indices[0]) == 0:
            return None
        return indices[0][0]
    
    # List all unique filters available across all instruments
    def list_available_filters(self, isomodel=None, filename=None):
        if isomodel == 'MIST' and filename:
            return self.get_mist_filters(filename)
        else:
            index_map = {
                'WFC3': {'F438W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8},
                'ACS_WFC': {'F435W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8},
                'ACS_HRC': {'F435W': 4, 'F475W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8},
                'WFPC2': {'F439W': 4, 'F450W': 5, 'F555W': 6, 'F606W': 7, 'F814W': 8}
            }
            unique_filters = set()
            for filters in index_map.values():
                unique_filters.update(filters.keys())
            print("Currently available filters:", ', '.join(sorted(unique_filters)))
            return sorted(unique_filters)
        
    def get_mist_filters(self, filename):
        filters = []
        photsystem = None
        print(f"Reading MIST file: {filename}")
        with open(filename, 'r') as f:
            for line in f:
                if line.startswith('#'):
                    #print(f"Header line: {line.strip()}")
                    if 'photometric system' in line.lower():
                        photsystem = line.split('=')[-1].strip()
                        #print(f"Detected photometric system: {photsystem}")
                    elif 'EEP' in line and 'phase' in line:
                        # This line contains the column headers
                        parts = line.split()
                        filters = [part for part in parts if part not in ['#', 'EEP', 'log10_isochrone_age_yr', 'initial_mass', 'star_mass', 'log_Teff', 'log_g', 'log_L', '[Fe/H]_init', '[Fe/H]', 'phase']]
                        break  # We've found our filters, no need to continue
                else:
                    break  # Stop when we reach the data section
        #print(f"Found filters: {filters}")
        return filters

    async def check_max_iso_age(self, ages, zs):
        # Ensure isodir is correctly set, default to current working directory if not
        if not hasattr(self, 'isodir') or not self.isodir:
            self.isodir = "./"  # Assuming files are in the current working directory

        mu = float(input("Enter the distance modulus (mu): "))
        table_bluemax = float(input("Enter the maximum blue table value (table_bluemax): "))
        self.list_available_filters()
        blue_mag = input("Enter the blue filter (e.g., F435W, F475W): ")

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
                        isofile = os.path.join(self.isodir, f"Iso_{formatted_age}_{formatted_z}_0.0.npz")
                        
                        if os.path.exists(isofile):
                            with np.load(isofile, allow_pickle=True) as data:
                                isodata = data['isodata']
                                
                                # Determine the index for the blue magnitude
                                indexdict = data['indexdict'].item()  # Assuming indexdict is stored in the .npz file
                                iblue = indexdict.get(blue_mag)

                                if iblue is None:
                                    print(f"Error: Invalid blue magnitude {blue_mag} for the given isodata.")
                                    continue
                                
                                bluemin = np.min(isodata[:, iblue] + mu)
                                bluemin_global = max(bluemin_global, bluemin)
                                output = f'age = {formatted_age} z = {formatted_z} bluemin = {bluemin}'
                                print(output)
                                outputs.append(output)
                                file_found = True
                                if bluemin > table_bluemax:
                                    age_excluded = True
                                break
                    if not file_found:
                        output = f"File not found: {isofile}"
                        print(output)
                        outputs.append(output)
                if age_excluded:
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
            
            isofile = os.path.join(isodir, f"Iso_{formatted_age}_{formatted_z}_0.0.npz")
            
            if os.path.exists(isofile):
                print(f"Loading file: {isofile}")  # Debug print
                with np.load(isofile, allow_pickle=True) as data:
                    isodata = data['isodata']
                    print(f"Loaded isodata shape: {isodata.shape}")  # Debug print

                    # Save data to a .txt file for inspection
                    #txt_filename = os.path.join(isodir, f"Data_Inspection_{formatted_age}_{formatted_z}.txt")
                    #with open(txt_filename, 'w') as txt_file:
                    #    txt_file.write("isodata:\n")
                    #    np.savetxt(txt_file, isodata, fmt='%.6e')
                    #    txt_file.write("\nmags:\n")
                    #    np.savetxt(txt_file, mags, fmt='%s')
                    #    txt_file.write(f"\nfblue: {fblue}\n")
                    #    txt_file.write(f"fred: {fred}\n")
                    #print(f"Data saved to {txt_filename}")

                    # Determine the indices for the blue and red magnitudes
                    indexdict = data['indexdict'].item()  # Assuming indexdict is stored in the .npz file
                    blue_index = indexdict.get(blue_mag)
                    red_index = indexdict.get(red_mag)

                    if blue_index is None or red_index is None:
                        print(f"Error: Invalid magnitudes {blue_mag} or {red_mag} for the given isodata.")
                        continue

                    color = isodata[:, blue_index] - isodata[:, red_index]
                    magnitude = isodata[:, red_index]
                    
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
            isofile = os.path.join(isodir, f"Iso_{formatted_age}_{formatted_z}_0.0.npz")
            if os.path.exists(isofile):
                with np.load(isofile, allow_pickle=True) as data:
                    isodata = data['isodata']
                    
                    # Determine the indices for the blue and red magnitudes
                    indexdict = data['indexdict'].item()  # Assuming indexdict is stored in the .npz file
                    blue_index = indexdict.get(blue_mag)
                    red_index = indexdict.get(red_mag)

                    if blue_index is None or red_index is None:
                        print(f"Error: Invalid magnitudes {blue_mag} or {red_mag} for the given isodata.")
                        continue

                    color = isodata[:, blue_index] - isodata[:, red_index]
                    magnitude = isodata[:, red_index]
                    plot_color = cmap(index / num_zs)
                    plt.plot(color, magnitude, color=plot_color)

                    x_range = plt.xlim()
                    y_range = plt.ylim()

                    x_threshold = 0.02 * (x_range[1] - x_range[0])
                    y_threshold = 0.02 * (y_range[1] - y_range[0])

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
        isofile = os.path.join(isodir, f"Iso_{formatted_age}_{formatted_z}_0.0.npz")
        if os.path.exists(isofile):
            with np.load(isofile, allow_pickle=True) as data:
                isodata = data['isodata']
                
                # Determine the indices for the blue and red magnitudes
                indexdict = data['indexdict'].item()  # Assuming indexdict is stored in the .npz file
                blue_index = indexdict.get(blue_mag)
                red_index = indexdict.get(red_mag)

                if blue_index is None or red_index is None:
                    print(f"Error: Invalid magnitudes {blue_mag} or {red_mag} for the given isodata.")
                    return

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

def model_selector(directory='.'):
    # Get all .set and .cmd files in the directory
    files = glob.glob(os.path.join(directory, '*.set')) + glob.glob(os.path.join(directory, '*.cmd'))
    
    if not files:
        print("No .set or .cmd files found in the current directory.")
        return

    print("Available files:")
    for idx, file in enumerate(files):
        print(f"{idx}: {os.path.basename(file)}")

    # Get user input for file selection
    while True:
        try:
            selections = input("Enter the indices of the files you want to unpack (comma-separated): ").split(',')
            selected_indices = [int(idx.strip()) for idx in selections]
            selected_files = [files[idx] for idx in selected_indices if 0 <= idx < len(files)]
            break
        except ValueError:
            print("Invalid input. Please enter comma-separated numbers.")

    # Categorize selected files
    parsec_v1_2s = []
    parsec_v2_0 = []
    mist = []

    for file in selected_files:
        if "IsoParsec_v1.2S" in file:
            parsec_v1_2s.append(file)
        elif "IsoParsec_v2.0" in file:
            parsec_v2_0.append(file)
        elif "MIST" in file or file.endswith('.cmd'):
            mist.append(file)

    # Print results
    if parsec_v1_2s:
        print(f"Using Parsec_v1.2S unpacking logic for files: {[os.path.basename(f) for f in parsec_v1_2s]}")
    if parsec_v2_0:
        print(f"Using Parsec_v2.0 unpacking logic for files: {[os.path.basename(f) for f in parsec_v2_0]}")
    if mist:
        print(f"Using MIST unpacking logic for files: {[os.path.basename(f) for f in mist]}")

    return parsec_v1_2s, parsec_v2_0, mist

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
        print("Choose the isochrone model to download:")
        print("1. PARSEC")
        print("2. MIST")
        choice = input("Enter your choice (1 or 2): ")

        if choice == "1":
            base_url = "http://stev.oapd.inaf.it/cgi-bin/cmd"
            parsec = PARSEC(base_url)

            print("Choose PARSEC version:")
            print("1. PARSEC v1.2S")
            print("2. PARSEC v2.0")
            version_choice = input("Enter your choice (1 or 2): ")

            if version_choice == "1":
                parsec_version = "1.2S"
                rotation_values = [None]  # No rotation for v1.2S
                isomodel = 'Parsec'
            elif version_choice == "2":
                parsec_version = "2.0"
                print("\nAvailable rotation options for PARSEC v2.0:")
                for i, omega in enumerate(parsec.rotation_options.keys(), 1):
                    print(f"{i}. ωi={omega}")
                rotation_choices = input("Enter the numbers of desired rotation options (comma-separated): ")
                rotation_values = [list(parsec.rotation_options.keys())[int(choice)-1] for choice in rotation_choices.split(',')]
                isomodel = 'Parsec2.0'
            else:
                print("Invalid choice. Defaulting to PARSEC v1.2S")
                parsec_version = "1.2S"
                rotation_values = [None]
                isomodel = 'Parsec'
        
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
                'track_parsec': parsec.parsec_versions[parsec_version],
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

            downloaded_files = []
            for rotation in rotation_values:
                # Add delay at the start of each iteration, except for the first one
                if rotation != rotation_values[0]:
                    await asyncio.sleep(20)  # 20 second delay
                
                form_data = form_data.copy()
                
                if rotation:
                    if parsec_version == "2.0":
                        form_data['track_omegai'] = rotation
                    else:
                        form_data['v_div_vcrit'] = parsec.rotation_options[rotation]

                output_filename, instrument_input = await parsec.download_isochrone(form_data)
                if output_filename and instrument_input:
                    downloaded_files.append(output_filename)

                if output_filename and instrument_input:
                    # Set environment variables immediately after download, this will allow use of --UnpackIsoSet during same session without having to manually input values
                    os.environ['ISOSETFILE'] = output_filename
                    os.environ['INSTRUMENT'] = instrument_input
                    os.environ['DATASOURCE'] = 'HST' if instrument_input in ['ACS_HRC', 'ACS_WFC', 'WFC3_UVIS', 'WFPC2'] else 'To Be Coded'
                    print(f"Download complete for rotation ωi={rotation if rotation else 'N/A'}")

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
                        for output_filename in downloaded_files:
                            rotation_value = UnpackIsoSet.extract_rotation(output_filename)
                            UnpackIsoSet.unpack_isochrone(output_filename, isomodel, rotation=rotation_value)
                else:
                    print(f"Failed to download or incorrect data received for rotation ωi={rotation if rotation else 'N/A'}")

        elif choice == "2":
            mist_downloader = MISTDownloader()
            rotation = mist_downloader.run()
            isomodel = 'MIST'

            if args.UnpackIsoSet:
                if isinstance(mist_downloader.output_filename, list):
                    for filename in mist_downloader.output_filename:
                        UnpackIsoSet.unpack_isochrone(filename, isomodel, rotation=rotation)
                elif mist_downloader.output_filename:
                    UnpackIsoSet.unpack_isochrone(mist_downloader.output_filename, isomodel, rotation=rotation)
                else:
                    print("No output file was generated by MIST downloader.")
        else:
            print("Invalid choice. Please enter 1 or 2.")    

    # Can use UnpackIsoSet without download_iso if you have the necessary information.
    # If you ran --download_iso in the same terminal session, it can automatically fetch everything necessary with environment variables
    if args.UnpackIsoSet and not args.download_iso:
        parsec_v1_2s, parsec_v2_0, mist = model_selector()

        all_files = parsec_v1_2s + parsec_v2_0 + mist
        if not all_files:
            print("No files selected for unpacking.")
            return

        for file in all_files:
            filename = os.path.basename(file)
            if file in parsec_v1_2s:
                isomodel = 'Parsec'
                rotation = 0.0
            elif file in parsec_v2_0:
                isomodel = 'Parsec2.0'
                rotation = UnpackIsoSet.extract_rotation(filename)
            elif file in mist:
                isomodel = 'MIST'
                rotation = UnpackIsoSet.extract_rotation(filename)
            else:
                isomodel = input(f"Enter the isochrone model for {file} (Parsec, Parsec2.0, or MIST): ")
                rotation = float(input(f"Enter the rotation value for {file}: "))

            if rotation is None:
                print(f"Warning: Could not determine rotation for {filename}. Assuming rotation = 0.0")
                rotation = 0.0
            
            UnpackIsoSet.unpack_isochrone(file, isomodel, rotation=rotation)

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