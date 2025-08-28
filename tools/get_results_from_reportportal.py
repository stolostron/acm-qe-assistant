import logging
import os
import certifi
from dotenv import load_dotenv
import requests
load_dotenv()

#LOG_FORMAT = '%(asctime)s | %(levelname)7s | %(name)s | line:%(lineno)4s | %(message)s)'
#logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)

base_url = os.getenv("RP_ENDPOINT")
rp_api_token = os.getenv("RP_APITOKEN")
project = os.getenv("RP_PROJECT")
headers = {'Authorization': 'Bearer ' + rp_api_token, "Content-Type": "application/json"}

try:
       cwd = os.getcwd()
       logging.info('Checking connection to Report Portal...')
       params = {
        'filter.eq.name': "any_report"
      }
       response = requests.get(f"{base_url}/api/v1/{project}/launch/latest", params=params, headers=headers).json()
       logging.info('Connection to Report Portal OK.')
except Exception:
       logging.info('SSL Error. Adding custom certs to Certifi store...')
       cafile = certifi.where()
       with open(f"{cwd}/certificates/cert1.pem", 'rb') as infile:
        customca = infile.read()
       with open(cafile, 'ab') as outfile:
        outfile.write(customca)
       logging.info('That might have worked.')

def get_launch_id_by_name(launch):
    url = f"{base_url}/api/v1/{project}/launch"
    page = 1
    page_size = 50

    if '#' in launch:
       launch_name, launch_number = launch.rsplit('#', 1)
       launch_name = launch_name.strip()
       launch_number = int(launch_number.strip())
    else:
      raise ValueError("launch format is 'name #number'")

    while True:
        params = {
            "filter.eq.name": launch_name,
            "filter.eq.number": launch_number,
            "page.page": page,
            "page.size": page_size
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        launches = data.get('content', [])
        for launch in launches:
            return launch['id']

        if data['page']['number'] + 1 >= data['page']['totalPages']:
            break
        page += 1

    print(f"Launch is not found: {launch}")
    return None

def get_failed_test_items(launch_id):
    url = f"{base_url}/api/v1/{project}/item"
    page = 1
    page_size = 100
    failed_items = []

    while True:
        params = {
            "filter.eq.launchId": launch_id,
            "filter.eq.hasChildren": "false",
            "filter.eq.status": "FAILED",
            "page.page": page,
            "page.size": page_size
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        items = data.get('content', [])
        for item in items:
             failed_items.append({
                "id": item["id"],
                "name": item["name"],
            })
        if data['page']['number'] + 1 >= data['page']['totalPages']:
            break
        page += 1

    return failed_items


def get_logs_for_test_item(item_id):
    url = f"{base_url}/api/v1/{project}/log"
    logs = []
    page = 1
    page_size = 100
    while True:
        params = {
            "filter.eq.item": item_id,
            "filter.eq.level": "ERROR",
            "page.page": page,
            "page.size": page_size
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        entries = data.get('content', [])

        for entry in entries:
            logs.append({
                "time": entry['time'],
                "level": entry['level'],
                "message": entry['message']
            })
        if data['page']['number'] + 1 >= data['page']['totalPages']:
            break
        page += 1

    return logs


def main(launch):
    launch_id=get_launch_id_by_name(launch)
    failed_items=get_failed_test_items(launch_id)

    if not failed_items:
        print("No failed test cases found.")
        return

    print(f"Total failed cases: {len(failed_items)}\n")

    for item in failed_items:
        print(f"Component: {item['name']}")
        print("Log:")
        logs = get_logs_for_test_item(item['id'])
        if logs:
            for line in logs:
                print(f"  {line}")
        else:
            print("  (No logs found)")
        print("\n" + "=" * 100 + "\n")

import argparse
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get failed test cases from Report Portal.')
    parser.add_argument('launch')
    args = parser.parse_args()
    main(args.launch)
    