import httpx
import asyncio
import logging
from bs4 import BeautifulSoup
from io import BytesIO
import re
import numpy as np
import argparse

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

    async def download_isochrone(self, output_filename, form_data):
        """Download isochrone data and save it to a file."""
        response = await self.send_request(form_data)
        if response and response.status_code == 200:
            dat_file_url = self.find_dat_file_link(response.text)
            if dat_file_url:
                # Correct the URL by replacing '/cgi-bin/cmd' with '/tmp'
                dat_file_url = f"http://stev.oapd.inaf.it/tmp/{dat_file_url.split('/')[-1]}"
                print(f"Attempting to download from: {dat_file_url}")  # Debug print
                dat_content = await self.download_dat_file(dat_file_url)
                if dat_content.startswith('<!DOCTYPE HTML'):
                    print("Error: The downloaded content is an HTML page, not the expected .dat file.")
                else:
                    with open(output_filename, 'w') as file:
                        file.write(dat_content)
                    print(f"Data successfully saved to {output_filename}")
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
    parser.add_argument('--download_iso', action='store_true', help="Download isochrone data.")
    args = parser.parse_args()
    
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
        
        3. You want to use CMD 3.7, Parsec v1.2S, and COLIBRI S_37. If you would like to change this, alter CMD, track_parsec, and track_colibri. As I don't know what potential future version you may
        want to use, you will need to track down the correct values yourself.

        4. In general, if you find you want to alter the default values / understand them better, inspect the 'form_data' and html on the webpage
        '''
        
        try:
            print("Let's attempt to download the desired isochrones by defining some parameters")
            
            print("Currently available photometric systems: ", list(photometric_systems.keys()))
            photometric_input = input("Enter the photometric system (e.g., ACS_HRC): ")
            photsys_file = photometric_systems.get(photometric_input.upper())
            
            if photsys_file is None:
                photsys_file = 'YBC_tab_mag_odfnew/tab_mag_wfc3_202101_wide.dat'  # Set default file
                print("Invalid photometric system. Defaulting to WFC3_UVIS file.")
            
            isoc_lagelow = float(input("Enter the lower log age limit (isoc_lagelow): "))
            isoc_lageupp = float(input("Enter the upper log age limit (isoc_lageupp): "))
            isoc_dlage = float(input("Enter the log age step-size (isoc_dlage): "))
            isoc_metlow = float(input("Enter the lower metallicity [M/H] limit (isoc_metlow): "))
            isoc_metupp = float(input("Enter the upper metallicity [M/H] limit (isoc_metupp): "))
            isoc_dmet = float(input("Enter the metallicity [M/H] step-size (isoc_dmet): "))
        
        except ValueError:
            print("Invalid input. Please enter a valid floating-point number.")
            return

        form_data = {
            'cmd_version': '3.7',
            'photsys_file': photsys_file,
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

        await parsec.download_isochrone("output_filename.dat", form_data)

if __name__ == "__main__":
    asyncio.run(main())
   