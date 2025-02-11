import os
import sys

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.get_result import get_error_message

from agent import Agent
from client import BedRockClient, GroqClient
from agent.chat.streamlit_chat import StreamlitChat
from client.config import ClientConfig

from dotenv import load_dotenv

load_dotenv()

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
    print(file)  # This will print the constructed file path
    with open(file, "r") as f:
        instruction = f.read()
    
    StreamlitChat.init_session(
        Agent(
            client=GroqClient(
                ClientConfig(
                    model="llama3-70b-8192",
                    temperature=0.2,
                    api_key=os.getenv("GROQ_API_KEY"),
                )
            ),
            name="QE Test Assistant",
            system=f"""
            You are the **QE Test Assistant**, responsible for identifying and asserting failure types based on the link to an error message.  

            1. **When provided with a link**:  
              - Use the `get_error_message` function to retrieve error details from the URL.  

            2. **Asserting the failure type**: 
              - Based on the component and the provided guidelines, analyze the error message and determine the failure type.  
              - The link might contain the information of which component for the error message.
              - Present the results in a clear and structured markdown table format as shown below:
                The analysis result for this jenkins job as below:  
              | Case ID    | Failure Type With High Possibility  | Assert Reason        | Link|
              |------------|------------------|------------------------------------------|-----|
        
             - The Assert Reason should contains the component like "<component-name>: <reason-message>", when <reason-message> is very long, move to the next line automaticlly.
             - The Link is [Rerun](the user provide the link).
             - Case ID should use - instead of _
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
