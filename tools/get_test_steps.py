import os
import certifi
from polarion import polarion
from polarion.record import Record
import logging

#LOG_FORMAT = '%(asctime)s | %(levelname)7s | %(name)s | line:%(lineno)4s | %(message)s)'
#logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)

def login_to_polarion(polarion_endpoint, polarion_user, polarion_password):
    """
    This function logs in to polarion and return the polarion client object
    :param polarion_endpoint: The polarion URL ex: https://polarion.engineering.redhat.com/polarion
    :param polarion_user: The polarion login user
    :param polarion_password: The polarion login password
    :return: The polarion client object after a successful login
    """
    try:
        cwd = os.getcwd()
        print(cwd)
        logging.info('Checking connection to Polarion...')
        polarion_client = polarion.Polarion(polarion_endpoint, polarion_user, polarion_password)
        logging.info('Connection to Polarion OK.')
        return polarion_client
    except Exception:
        logging.info('SSL Error. Adding custom certs to Certifi store...')
        cafile = certifi.where()
        with open(f"{cwd}/redhatcert.pem", 'rb') as infile:
            customca = infile.read()
        with open(cafile, 'ab') as outfile:
            outfile.write(customca)
        logging.info('That might have worked.')
        polarion_client = polarion.Polarion(polarion_endpoint, polarion_user, polarion_password)
        logging.info('Connection to Polarion OK.')
        return polarion_client


def get_test_case_by_id(polarion_client, project_id, case_id):
    """
    polarion_client: Polarion client
    project_id: project ID (ex: RHACM4K)
    case_id: test case ID (ex: RHACM4K-xxx)
    return: tuple: (test_case, test_steps)
    """
    project = polarion_client.getProject(project_id)
    target_case=project.getWorkitem(case_id)
    
    if not target_case:
        print(f"Not find the test case {case_id}")
        return None, []
    test_steps = target_case.getTestSteps()
    test_component = target_case.getCustomField('casecomponent')
    print(f"Test case: \n{target_case.title}")
    print(f"\nTest steps: \n{test_steps}")
    print(f"\nTest component: \n{test_component}")

    return target_case, test_steps, test_component

