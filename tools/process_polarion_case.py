
import os
import argparse
from get_test_steps_from_polarion import login_to_polarion, get_test_case_by_id
#from tools.get_test_steps import login_to_polarion, get_test_case_by_id
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Process Polarion test case')
    parser.add_argument('case_id', help='Polarion case ID (e.g., RHACM4K-58327)')
    args = parser.parse_args()
    
    polarion_endpoint = "https://polarion.engineering.redhat.com/polarion"
    polarion_user = os.getenv("POLARION_USER")
    polarion_password = os.getenv("POLARION_PASSWORD")
    polarion_token = os.getenv("POLARION_TOKEN")
    project_id = os.getenv("POLARION_PROJECT")
    case_id = args.case_id

    if not (polarion_token or (polarion_user and polarion_password)):
        print("Either polarion_token or both polarion_user and polarion_password must be provided.")
        return
    
    client = login_to_polarion(polarion_endpoint, polarion_user, polarion_password, polarion_token)
    if client:
        case, steps, componment = get_test_case_by_id(client, project_id, case_id)
        if case:
            print("Successfully retrieved test case details.")
            print(f"Case: {case}")
            print(f"Steps: {steps}")
            print(f"Component: {componment}")
    else:
        print("Failed to connect to Polarion.")

if __name__ == "__main__":
    main()
