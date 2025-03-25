from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Tuple

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
#sys.path.append(str(Path(__file__).parent.parent)) 

from tools.get_result import get_error_message, get_failed_case_summary

from agent import Agent
from client import BedRockClient, GroqClient
from agent.chat.streamlit_chat import StreamlitChat
from client.config import ClientConfig

from dotenv import load_dotenv
import httpx
load_dotenv()


@dataclass
class AssistantMessage:
    content: str
    role: str = "assistant"
    function_call: Optional[Dict[str, Any]] = None 
class DeepSeekClient:
   def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url)

   def __call__(self, *args, **kwargs) -> AssistantMessage:
        timeout= httpx.Timeout(60.0, read=60.0)
        if args and isinstance(args[0], str):  
            messages = [{"role": "user", "content": args[0]}]
            model = args[2] if len(args) > 2 else kwargs.get("model", "deepseek-r1-distill-qwen-14b")
        else:  
            messages = args[0] if args else kwargs.get("messages", [])
            model = kwargs.get("model", "deepseek-r1-distill-qwen-14b")
        # call API
            response = self.client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=timeout,
            json={
                "messages": messages,
                "model": model,
                **{k: v for k, v in kwargs.items() if k not in ["messages", "model"]}
            }
        )
        data = response.json()
        msg_data = data["choices"][0]["message"]
        return AssistantMessage(
                content=msg_data["content"],
                function_call=msg_data.get("function_call")  
            )
    
        
deepseek_client = DeepSeekClient(
    base_url = "https://deepseek-r1-distill-qwen-14b-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443",
    api_key = os.getenv("GROQ_API_KEY")    
)

StreamlitChat.context(
    {
        "page_title": "QE Assistant",
        "page_icon": "🚀",
        "layout": "wide",
        "initial_sidebar_state": "auto",
        "menu_items": {
            "Get Help": "https://www.extremelycoolapp.com/help",
            "Report a bug": "https://www.extremelycoolapp.com/bug",
            "About": "# This is a header. This is an *extremely* cool app!",
        },
    }
)

if not StreamlitChat.is_init_session():
    file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        "runbooks",
        "component-keywords.md",
    )
    #print(file)  # This will print the constructed file path
    with open(file, "r") as f:
        instruction = f.read()
    
    StreamlitChat.init_session(
        
        Agent(
            #client=GroqClient(
            #    ClientConfig(
            #        model="llama3-70b-8192",
           #         temperature=0.2,
            #       api_key=os.getenv("GROQ_API_KEY"),
           #     )
            
           # ),
            client=deepseek_client,
               
            name="QE Test Assistant",
            system=f"""
            You are the **QE Test Assistant**, responsible for identifying and asserting failure types based on the link to error messages.  

            1. **When provided with a link**:  
              - Use the `get_error_message` function to retrieve error details from the URL. 
               

            2. **Asserting the failure type**: 
              - Based on the component and the provided guidelines, analyze the error message and determine the failure type.  
              - The link might contain the information of which component for the error message.
              - Present the results in a clear and structured markdown table format as shown below:
                The analysis result for this jenkins job as below:  
              | Case ID    | Case Title |Failure Type With High Possibility  | Assert Reason        | Link|
              |------------|------------------|------------------------------------------|-----|----|
        
             - The Assert Reason should contains the component like "<component-name>: <reason-message>", when <reason-message> is very long, move to the next line automaticlly.
             - The Link is [Rerun](the user provide the link).
             - Then give suggestion or note:
             - If the faliure type is Automation bug, sugget to re-run it.
             - If the failure type is System issue, suggest to check the test envirnoment and then re-run it.
             - If the failure type is Product bug, suggest to be investigated further. 
             
            **Guidelines**
            
            {instruction}
            
            Try to make your answer clearly and easy to read! 
            
            """,
            tools=[get_error_message],
            chat_console=StreamlitChat("QE Test Assistant"),
        )
     
    )

StreamlitChat.input_message()

# python -m streamlit run agents/qe_assistant.py
