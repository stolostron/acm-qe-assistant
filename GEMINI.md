
## Analyse the failures

- Use the tools/process_failed_case.py jenkins_url to get the failed cases when input the jenkins job link.
- Get the componment name from jenkins job link and following the component-keywords file to analyse these failed cases if it's product bug, automation bug or system issue.
- Present the results for all failed cases in a clear and structured in list format and generate html format.
- if it's automation bug, search code location in relevant code repo and clone code repo, then try to fix it, but not commit it and not delete the code repo.
  - for alc componment, the code repo is https://github.com/stolostron/application-ui-test.git
  - for clc componment, the code repo is https://github.com/stolostron/clc-ui-e2e.git

## Generate automation scripts

- Use the tools/process_polarion_case.py fucntion to get the test steps when give the polarion case id.
- Use the env get the polarion username and password, then generate the automation scripts following the prompt.
 -  if the componment name is `hoh`, use the common functions firstly in the https://github.com/stolostron/acmqe-hoh-e2e 
 -  if the component name is `grc`, use the common functions firstly in the https://github.com/stolostron/acmqe-grc-test 
