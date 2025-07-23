from typing import List, Union, Generator, Iterator, Optional
from pydantic import BaseModel
import requests
import json
from ragflow_client.api import RAGflowClient
from ragflow_client.exceptions import RAGflowAPIError
import os

class ChatAPIPipeline:
    class Valves(BaseModel):
        API_KEY: str
        HOST: str
        PORT: str
        DATASET_ID: Optional[str] = None  # Optional dataset ID for file uploads

    def __init__(self):
        self.chat_id=None
        self.debug=True
        self.sessionKV={}
        self.client = None
        self.valves = self.Valves(
            **{
                "API_KEY": os.getenv("RAGFLOW_API_KEY", "ragflow-ZkMWI3NjcwNjM3MzExZjA4ZWNiMDI0Mm"),
                "HOST": os.getenv("RAGFLOW_HOST", "http://localhost"),
                "PORT": os.getenv("RAGFLOW_PORT", "8000"),
                # "DATASET_ID": "",  # Optional: Set default dataset ID
            }
        )
        self._initialize_client()

    def _initialize_client(self):
        """Initialize RAGflow client with configuration from valves"""
        if self.valves.API_KEY and self.valves.HOST and self.valves.PORT:
            base_url = f"{self.valves.HOST}:{self.valves.PORT}"
            self.client = RAGflowClient(base_url=base_url, api_key=self.valves.API_KEY)
            if self.debug:
                print(f"RAGflow client initialized with base URL: {base_url}")
        else:
            if self.debug:
                print("RAGflow client not initialized - missing configuration")

    async def on_startup(self):
        pass

    async def on_shutdown(self):
        """Clean up resources on server shutdown"""
        pass

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        # This function is called before the OpenAI API request is made. You can modify the form data before it is sent to the OpenAI API.
        print(f"inlet: {__name__}")
        if self.debug:
            chat_id=body['metadata']['chat_id']
            print(f"inlet: {__name__} - chat_id:{chat_id}")
            if self.sessionKV.get(chat_id):
                self.chat_id=self.sessionKV.get(chat_id)
                print(f"cache ragflow's chat_id is : {self.chat_id}")
            else:
                #创建session
                session_url = f"{self.valves.HOST}:{self.valves.PORT}/api/v1/agents/{self.valves.AGENT_ID}/sessions"
                session_headers = {
                    'content-Type': 'application/json',
                    'Authorization': 'Bearer '+self.valves.API_KEY
                }
                session_data={}
                session_response = requests.post(session_url, headers=session_headers, json=session_data)
                json_res=json.loads(session_response.text)
                self.session_id=json_res['data']['id']
                self.sessionKV[chat_id]=self.session_id
                print(f"new ragflow's session_id is : {json_res['data']['id']}")
            try:
                # 创建chat
                chat_url = f"{self.valves.HOST}:{self.valves.PORT}/api/v1/chats"
                chat_headers = {
                    'content-Type': 'application/json',
                    'Authorization': 'Bearer '+self.valves.API_KEY
                }
                chat_data={'name': 'Chat Pipeline', 'dataset_ids': []}
                chat_response = requests.post(chat_url, headers=chat_headers, json=chat_data)
                chat_response.raise_for_status()
                json_res=json.loads(chat_response.text)
                self.chat_id=json_res['data']['id']
                self.sessionKV[chat_id]=self.chat_id 
                print(f"new ragflow's chat_id is : {self.chat_id}")
            except requests.exceptions.RequestException as e:
                print(f"Error creating chat: {str(e)}")
                self.chat_id = None
            print(f"inlet: {__name__} - user:")
            print(user)
        # if 'files' in body and self.client and self.valves.DATASET_ID:
        #     uploaded_files = await self._handle_file_upload(body['files'])
        #     body['uploaded_files'] = uploaded_files
        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Process response after receiving from API"""
        if self.debug:
            print(f"outlet: response={body}, user={user}")
        return body

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """Process user message through chat pipeline"""
        if not self.client or not self.chat_id:
            error_msg = "Chat pipeline not properly initialized - missing client or chat ID"
            if self.debug:
                print(error_msg)
            return error_msg

        try:
            question_url = f"{self.valves.HOST}:{self.valves.PORT}/api/v1/chats/{self.chat_id}/completions"
            question_headers = {
                'content-Type': 'application/json',
                'Authorization': 'Bearer '+self.valves.API_KEY
            }
            question_data={'question': user_message, 'stream': True, 'session_id': self.session_id, 'lang': 'Chinese'}
            question_response = requests.post(question_url, headers=question_headers, stream=True, json=question_data)
            if question_response.status_code == 200:
                step=0
                for line in question_response.iter_lines():
                    if line:
                        try:
                            json_data = json.loads(line.decode('utf-8')[5:])
                            if 'data' in json_data and json_data['data'] is not True and 'answer' in json_data['data'] and '* is running...' not in json_data['data']['answer']:
                                if 'chunks' in json_data['data']['reference']:
                                    referenceStr="\n\n### references\n\n"
                                    filesList=[]
                                    for chunk in json_data['data']['reference']['chunks']:
                                        if chunk['document_id'] not in filesList:
                                            filename = chunk['document_name']
                                            parts = filename.split('.')
                                            last_part = parts[-1].strip() if parts else ''
                                            ext= last_part.lower() if last_part else ''
                                            referenceStr+=f"\n\n - [{chunk['document_name']}]({self.valves.HOST}:{self.valves.PORT}/document/{chunk['document_id']}?ext={ext}&prefix=document)"
                                            filesList.append(chunk['document_id'])
                                    yield referenceStr
                                else:
                                    yield json_data['data']['answer'][step:]
                                    step=len(json_data['data']['answer'])
                        except json.JSONDecodeError:
                            print(f"Failed to parse JSON: {line}")
            else:
                yield f"Request failed with status code: {question_response.status_code}"
            return

        except RAGflowAPIError as e:
            error_msg = f"Chat API error: {str(e)}"
            if self.debug:
                print(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error in chat pipeline: {str(e)}"
            if self.debug:
                print(error_msg)
            return error_msg