import argparse
import os
import re
import requests
import sys
import urllib.parse
from astroquery.mast import Observations
from astroquery.mast.missions import MastMissions
import astropy.units as u
from astropy.coordinates import SkyCoord
import logging

# Set up basic configuration for logging, only inform users of warnings
logging.basicConfig(level=logging.WARNING)

# Setup slightly more verbose configuration for logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class HST_MAST_Query:
    def __init__(self):
        self.list_products_url = "https://mast.stsci.edu/search/hst/api/v0.1/list_products"
        self.retrieve_product_url = "https://mast.stsci.edu/search/hst/api/v0.1/retrieve_product?product_name="

    def query_and_list_products(self, target_name, radius=1*u.arcmin, product_type="SCIENCE",
                                instruments=None, min_exposure=1000):
        logging.info(f"Querying for target: {target_name} with radius: {radius}")
        missions = MastMissions(mission='hst')
        results = missions.query_object(
            target_name,
            radius=str(radius.to(u.arcmin).value),
            radius_units='arcminutes',
            sci_actual_duration=f'>= {min_exposure}',
            sci_aec='S',
            sci_instrume=','.join(instruments) if instruments else 'acs,wfc3,wfpc,wfpc2'
        )
        logging.info(f"Number of observations found: {len(results)}")
        if len(results) == 0:
            print("No observations found with the specified criteria.")
            return None
        return results

    def download_file(self, url, output_path):
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded {output_path}")
        else:
            print(f"Failed to download {output_path}. Status code: {response.status_code}")

    def download_selected_products(self, products, selected_indices):
        patterns = [r'_flt\.fits$', r'_flc\.fits$', r'_drz\.fits$', r'_drc\.fits$']
        for index in selected_indices:
            product = products[index]
            dataset_id = product['sci_data_set_name']
            response = requests.get(f"{self.list_products_url}?dataset_ids={dataset_id}")
            if response.status_code == 200:
                product_list = response.json()
                if 'products' in product_list:
                    for file_info in product_list['products']:
                        file_name = file_info['filename']
                        if not file_name.startswith('hst_') and any(re.search(pattern, file_name) for pattern in patterns):
                            file_url = f"{self.retrieve_product_url}{urllib.parse.quote(file_name)}"
                            output_path = f"./downloads/{file_name}"
                            self.download_file(file_url, output_path)
                else:
                    print("No 'products' key in response. Check API response structure.")
            else:
                print(f"Failed to list products for dataset {dataset_id}. Status code: {response.status_code}")

def main():
    parser = argparse.ArgumentParser(description="Query and download data from MAST.")
    parser.add_argument('--hst_download', action='store_true', help='Activate download from HST MAST')
    args = parser.parse_args()

    if args.hst_download:
        query = HST_MAST_Query()
        target = input("Enter the target name: ")
        products = query.query_and_list_products(target)
        if products is not None:
            print("Available products:")
            for i, product in enumerate(products):
                print(f"{i}: Target Name: {product['sci_targname']}, RA: {product['sci_ra']}, DEC: {product['sci_dec']}, "
                      f"Duration: {product['sci_actual_duration']}, Instrument: {product['sci_instrume']}, "
                      f"Spectral Characteristics: {product['sci_spec_1234']}, Dataset Name: {product['sci_data_set_name']}")
            selected_indices = input("Enter the indices of products to download (comma-separated): ")
            selected_indices = list(map(int, selected_indices.split(',')))
            query.download_selected_products(products, selected_indices)
        else:
            print("No products available for download.")
    else:
        print("Usage: python MAST_query.py --hst_download")

if __name__ == "__main__":
    main()