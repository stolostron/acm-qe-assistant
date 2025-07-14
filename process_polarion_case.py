
import os
from tools.get_test_steps import login_to_polarion, get_test_case_by_id
from dotenv import load_dotenv
load_dotenv()
polarion_endpoint = "https://polarion.engineering.redhat.com/polarion"
polarion_user = os.getenv("POLARION_USER")
polarion_password = os.getenv("POLARION_PASSWORD")
project_id = "RHACM4K"
case_id = "RHACM4K-58327"

if not polarion_user or not polarion_password:
    print("Error: POLARION_USER and POLARION_PASSWORD environment variables must be set.")
else:
    client = login_to_polarion(polarion_endpoint, polarion_user, polarion_password)
    if client:
        case, steps, componment = get_test_case_by_id(client, project_id, case_id)
        if case:
            print("Successfully retrieved test case details.")
