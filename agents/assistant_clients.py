from typing import Dict, List
import requests

class AssistantClient:
    def __init__(self, api_key, base_url, model):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
    def chat(self, messages, **kwargs):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            #"messages": [{"role": "user", "content": prompt}],
            **kwargs
        }
        print("Debug - Request Payload:", payload) 

        try:
          response = requests.post(f"{self.base_url}/v1/chat/completions", headers=headers, json=payload)
          response.raise_for_status()
          data = response.json()
          message = data["choices"][0]["message"]["content"]
          return message
        except requests.exceptions.HTTPError as e:
             print("HTTP Error Details:", e.response.text)
             raise   
    
    def __call__(self, prompt, *args, **kwargs):
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list):
            messages = prompt
        else:
            raise ValueError("prompt must be str or list of messages")       
        return self.chat(messages, **kwargs)
