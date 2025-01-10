import get_result     
urlpath = 'https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/view/Global%20Hub/job/globalhub-e2e/552/testReport/'
#urlpath = 'https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/view/QE%20Pipelines/job/qe-acm-automation-poc/job/alc_e2e_tests/1954/testReport/'
#urlpath = "https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/qe-acm-automation-poc/job/grc-e2e-test-execution/2169/testReport"
#urlpath = 'https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/qe-acm-automation-poc/job/server_foundation_e2e_tests/695/testReport/'
results = get_result.get_case_error_msg(urlpath)