# app.py
import os
import re
from dotenv import load_dotenv
import streamlit as st
from agents import AssistantClient
from tools import get_error_message
from tools import (
    extract_component_from_url,
    load_rules,
    analyze_failed_case,
    generate_test_script
)
from tools import login_to_polarion, get_test_case_by_id
import truststore 

truststore.inject_into_ssl()
load_dotenv()
MODEL_API=os.getenv("API_MODLE")
MODEL_ID=os.getenv("API_ID")
ACCESS_TOKEN=os.getenv("API_KEY")
POLARION_API=os.getenv("POLARION_API")
POLARION_USER=os.getenv("POLARION_USER")
POLARION_PASSWD=os.getenv("POLARION_PASSWD")
client = AssistantClient(
    base_url=MODEL_API, model=MODEL_ID, api_key=ACCESS_TOKEN)

# Streamlit 
def run_streamlit_app():

    # Init chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.set_page_config(
     page_title="🛠️ AI Assistant System",
     layout="wide",
     initial_sidebar_state="expanded"
)
    st.title("🛠️ AI Assistant System")
    st.markdown("""
Generate the automation scripts and analyse the failed case.
""")
    # Sidebar configuration
    #with st.sidebar:
   #  st.header("Configuration")
   #  rules_file = st.selectbox(
   #     "guidelines",
   #     ["rules/component-keywords.md"],
   #     format_func=lambda x: x.split('/')[-1]
   #  )
    
   #  st.divider()
     
    # manage chat states 
    if "messages" not in st.session_state:
      st.session_state.messages = []

    if "last_intent" not in st.session_state:
      st.session_state.last_intent = None

    if "last_suite_url" not in st.session_state:
     st.session_state.last_suite_url = None
 
    # Initial chat records
    if "messages" not in st.session_state:
     st.session_state.messages = [
        {"role": "system", "content": "You are a QA automation assistant."}
    ]
    # show chat history
    for msg in st.session_state.messages:
       with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

    #def regenerate_analysis():
    #    if "last_suite_url" in st.session_state and st.session_state.last_suite_url:
    #        prompt = f"{st.session_state.last_suite_url}"
    #        st.session_state.messages.append({"role": "user", "content": prompt})
    #        st.session_state.rerun_trigger = True 
            #st.experimental_rerun()
    #if "rerun_trigger" in st.session_state and st.session_state.rerun_trigger:
    # Reset the rerun trigger flag
    #  st.session_state.rerun_trigger = False
    # Trigger the rerun here
    #  st.rerun()
   
    if prompt := st.chat_input("Ask your question, for example, generate the automation scripts or analyse the failed case"):
      # save user input
      st.session_state.messages.append({"role": "user", "content": prompt})
      with st.chat_message("user"):
        st.markdown(prompt)
      # Judge the intention
      intent = None
      if "generate" in prompt.lower() or "RHACM4K-" in prompt.lower():
                   intent = "generate_test_script"
      elif "re-generate" in prompt.lower() or "generate again" in prompt.lower():
                   intent = st.session_state.last_intent
      elif "analyse" in prompt.lower() or "http" in prompt.lower():
                   intent = "analyze_failure_url"
      elif "analyse" in prompt.lower() or "re-analyse" in prompt.lower():
                   intent = st.session_state.last_intent
      else:
            intent = None
      # answer logic
      with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = ""    
            if intent == "generate_test_script":
                    # the logic for generating automation scripts
                     match = re.search(r"RHACM4K-\d+", prompt, re.IGNORECASE)
                     if match:
                      ploarion_client = login_to_polarion(polarion_endpoint=POLARION_API,polarion_user=POLARION_USER,polarion_password=POLARION_PASSWD)  
                      polarion_id = match.group(0)
                      _, steps = get_test_case_by_id(ploarion_client, "RHACM4K", polarion_id)
                      feature_description = steps
                     else:
                       feature_description = re.sub(r"generate( automation)? scripts", "", prompt, flags=re.IGNORECASE).strip()  
                     if feature_description:
                            test_script = generate_test_script(client, feature_description)
                            reply = f"**Automation scripts:**\n\n```\n{test_script}\n```"     
                     else:
                            reply = f"**No steps.**"
                     st.markdown(reply)
            elif intent == "analyze_failure_url":
                 # if not st.session_state.get("generated"):
                    # URL 
                    url_match = re.match(r"^(.*?/\d+)/", prompt)
                    #match = re.match(r"^(.*?/\d+)/", url)
                
                    url_name = url_match.group(1) if url_match else st.session_state.last_suite_url
                    if not url_name:
                        reply = "Please provide the correct job URL. For example: https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/view/Global%20Hub/job/globalhub-e2e/819"
                    else:
                        st.session_state.last_suite_url = url_name
                        component = extract_component_from_url(url_name)
                        if not component:
                           reply = f"Not find the component name"
                        else:   
                           failed_cases = get_error_message(url_name)
                           st.session_state['failed_cases'] = failed_cases
                        if not failed_cases:
                            reply = f"No found failed cases for url `{url_name}`."
                        else:
                            results = []
                            guideline = load_rules("runbooks/component-keywords.md")     
                            analysis = analyze_failed_case(client, component, failed_cases, guidelines_dict=guideline)
                            #results.append(f"{analysis}")
                            #reply = "\n\n---\n\n".join(results)
                            reply = analysis
                            st.session_state.last_intent = "analyze_failure_url" 
                           # st.session_state.generated = True
                    st.markdown(reply)
                    col1, col2 = st.columns([1,1])
                    with col1:
                              if st.session_state.last_suite_url:
                                  st.markdown(
                                        f"[🔗 Link to Jenkins Job]({st.session_state.last_suite_url})",
                                        unsafe_allow_html=True,
                                     )
                    #with col2:
                             # if st.button("🔄 Regenerate", key="regenerate_btn"):
                             #      st.session_state.pending_regeneration = True
                             #      st.session_state.messages.append({"role": "user", "content": "re-analyse"})
                             #      st.rerun()
                             #  st.button("🔄 Regenerate", key="regenerate_btn", on_click=regenerate_analysis)
                            #   pass
                            #if st.button("🔄 Regenerate", key="regenerate_btn"):
                            #     st.session_state.need_rerun = True
                             #     st.session_state.rerun_prompt = f"re-analyze {st.session_state.last_suite_url}"               
            else:
              # AI chat by default
              # parse AI response
              response = client.chat(st.session_state.messages)
              if isinstance(response, str):
                reply = response
              elif isinstance(response, dict) and "choices" in response:
                reply = response["choices"][0]["message"]["content"]
              else:
                 reply = "Unexpected AI response"
            # show reply
              st.markdown(reply)
            # save chat record
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.session_state.last_intent = intent
                
if __name__ == "__main__":
    run_streamlit_app()