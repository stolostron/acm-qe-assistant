from collections import defaultdict
import re
from typing import Dict, List
from urllib.parse import urlparse

from streamlit import html

def extract_component_from_url(url: str) -> str | None:
    try:
        path = urlparse(url).path  # e.g. /job/qe-acm/job/grc-e2e-test-execution/2532/
        parts = path.strip("/").split("/")
        # find all job/...，collect the job name from last job
        job_names = [parts[i+1] for i in range(len(parts)-1) if parts[i] == "job"]
        if job_names:
            # grc-e2e-test-execution
            last_job = job_names[-1]  
            # extract grc
            component = last_job.split("-")[0]  
            return component
        print (f"Component name is: {component}")
    except Exception as e:
        print("extract_component_from_url error:", e)
    return None
    

def load_rules(md_file: str) -> dict:
        component_guidelines = defaultdict(str)
        current_component = None
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                for line in f:
                 if line.startswith("## Component Name "):
                  current_component = line.replace("## Component Name", "").strip()
                 elif current_component:
                   component_guidelines[current_component] += line
        except Exception as e:
            raise ValueError(f"can not load the file: {str(e)}")
        
#def generate_test_script(ai_client, feature_description):
 #       prompt = f"Please generate an automated test scripts for the following feature: {feature_description}"
 #       return ai_client.chat([{"role": "user", "content": prompt}])

def generate_test_script(ai_client, feature_description):
    keywords = ["policy", "page", "browser"]
    if any(
    kw in item.get("step", "").lower()
    for item in feature_description
    for kw in keywords
):
        framework = "cypress"
        language = "JavaScript"
        description = "You are a QA automation engineer experienced with Cypress, the JavaScript end-to-end testing framework."
        style_guide = "Write realistic Cypress test code using JavaScript to automate browser interactions and validate UI behavior."
    else:
        framework = "ginkgo"
        language = "Go"
        description = "You are a QA automation engineer experienced with Ginkgo, the BDD testing framework for Go."
        style_guide = "Write clean and idiomatic Go code using Ginkgo for BDD-style testing. Use Gomega for assertions."
    prompt = f"""
 {description}
Please generate an automated test script using **{framework}** for the following feature. Follow the standard practices and style conventions of the {framework} framework.


### Feature Description:
{feature_description}

### Requirements:
- Use {language} for writing the test script
- Use the {framework} framework
- {style_guide}
- Follow best practices for structuring tests
- Use mocks or stubs as needed
- Add comments to explain each step
- Return only the test code inside a markdown code block
"""

    # Send prompt to AI and return response
    response=ai_client.chat([{"role": "user", "content": prompt}])
    #print("Raw AI response:", response)
    return response
    



def analyze_failed_case(ai_client, component, failed_cases, guidelines_dict):
       guidelines_dict = guidelines_dict or {}
       guideline = guidelines_dict.get(component, "")
       prompt = _build_prompt(failed_cases, guideline)
       return ai_client.chat([{"role": "user", "content": prompt}])

def _build_prompt(cases: List[Dict], rules_md: str) -> Dict:
        
    """prompt"""
    cases_str = "\n".join(
            f"### Total cases {idx+1}\n"
            f"- Case ID: {case['ID']}\n"
            f"- Case Title: {case['Title']}\n"
            f"- Assert Reason: {case['Error Message']}\n"
            for idx, case in enumerate(cases)
        )
    return f"""
    ## analysis contents
        
    ### analysis guidelines
        {rules_md}
        
    ### failed cases list
        {cases_str}
        
    ### output
        1. Following the template to generate:
           ```markdown table
           #### Test failure Analysis report
           
           **Analysis summary**
           - Total cases: {len(cases)}
           
           **Detailed Analysis**
            - Based on the component and the provided guidelines, analyze the error message and determine the failure type.  
            - The link might contain the information of which component for the error message.
            - Present the results in a clear and structured markdown table format as shown below:
           | Case ID | Case Title | Failure Type With High Possibility | Assert Reason |Suggestion/Note|
           |--------|--------------------------|----------|----------------------------------|-------------------------|
           
            - Then give suggestion or note:
            - If the faliure type is Automation bug, sugget to re-run it.
            - If the failure type is System issue, suggest to check the test envirnoment and then re-run it.
            - If the failure type is Product bug, suggest to be investigated further. 
            
           ```
        """