
import os
from get_test_steps import login_to_polarion, get_test_case_by_id
#from tools.get_test_steps import login_to_polarion, get_test_case_by_id
from dotenv import load_dotenv
load_dotenv()
polarion_endpoint = "https://polarion.engineering.redhat.com/polarion"
polarion_user = os.getenv("POLARION_USER")
polarion_password = os.getenv("POLARION_PASSWORD")
polarion_token = os.getenv("POLARION_TOKEN")
project_id = "RHACM4K"
case_id = "RHACM4K-58327"

if not (polarion_token or (polarion_user and polarion_password)):
    print("Either polarion_token or both polarion_user and polarion_password must be provided.")
else:
    client = login_to_polarion(polarion_endpoint, polarion_user, polarion_password, polarion_token)
    if client:
        case, steps, componment = get_test_case_by_id(client, project_id, case_id)
        if case:
            print("Successfully retrieved test case details.")