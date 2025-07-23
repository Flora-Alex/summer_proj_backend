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
        CHAT_ID: Optional[str] = None     # Optional existing chat ID

    def __init__(self):
        self.session_id = None
        self.debug = True
        self.sessionKV = {}
        self.client = None
        self.valves = self.Valves(
            **{
                "API_KEY": os.getenv("RAGFLOW_API_KEY", ""),
                "HOST": os.getenv("RAGFLOW_HOST", "http://localhost"),
                "PORT": os.getenv("RAGFLOW_PORT", "8000"),
                # "DATASET_ID": "",  # Optional: Set default dataset ID
                # "CHAT_ID": ""       # Optional: Set default chat ID
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
        """Initialize resources on server startup"""
        # Create default chat if CHAT_ID not provided
        if not self.valves.CHAT_ID and self.client:
            try:
                chat_name = "Default Chat Pipeline"
                response = self.client.create_chat(name=chat_name)
                self.valves.CHAT_ID = response["data"]["id"]
                if self.debug:
                    print(f"Created new chat with ID: {self.valves.CHAT_ID}")
            except RAGflowAPIError as e:
                print(f"Error creating default chat: {str(e)}")

    async def on_shutdown(self):
        """Clean up resources on server shutdown"""
        pass

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Process request before sending to API"""
        if self.debug:
            chat_id = body.get('metadata', {}).get('chat_id')
            print(f"inlet: chat_id={chat_id}, user={user}")

        # Handle file uploads if present
        if 'files' in body and self.client and self.valves.DATASET_ID:
            uploaded_files = await self._handle_file_upload(body['files'])
            body['uploaded_files'] = uploaded_files

        return body

    async def _handle_file_upload(self, files: List[dict]) -> List[dict]:
        """Handle file uploads to specified dataset"""
        if not files or not self.valves.DATASET_ID:
            return []

        uploaded_files = []
        try:
            # Extract file paths from request
            file_paths = [file['path'] for file in files if 'path' in file]
            if not file_paths:
                return []

            # Upload files using RAGflow client
            response = self.client.upload_documents(
                dataset_id=self.valves.DATASET_ID,
                file_paths=file_paths
            )

            # Parse and return upload results
            for doc in response.get('data', []):
                uploaded_files.append({
                    'id': doc.get('id'),
                    'name': doc.get('name'),
                    'status': doc.get('status')
                })

            if self.debug:
                print(f"Uploaded {len(uploaded_files)} files to dataset {self.valves.DATASET_ID}")

        except RAGflowAPIError as e:
            print(f"File upload error: {str(e)}")
        except Exception as e:
            print(f"Unexpected error during file upload: {str(e)}")

        return uploaded_files

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Process response after receiving from API"""
        if self.debug:
            print(f"outlet: response={body}, user={user}")
        return body

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """Process user message through chat pipeline"""
        if not self.client or not self.valves.CHAT_ID:
            error_msg = "Chat pipeline not properly initialized - missing client or chat ID"
            if self.debug:
                print(error_msg)
            return error_msg

        try:
            # Get or create session
            session_id = self._get_or_create_session()

            # Send message to chat
            response = self.client.converse_with_chat(
                chat_id=self.valves.CHAT_ID,
                question=user_message,
                stream=True,
                session_id=session_id
            )

            # Handle streaming response
            if response and hasattr(response, 'iter_lines'):
                for line in response.iter_lines():
                    if line:
                        try:
                            # Parse and yield response chunks
                            json_data = json.loads(line.decode('utf-8')[5:])
                            if 'data' in json_data and 'answer' in json_data['data']:
                                yield json_data['data']['answer']
                        except json.JSONDecodeError:
                            if self.debug:
                                print(f"Failed to parse response line: {line}")
            else:
                # Return non-streaming response
                answer = response.get('data', {}).get('answer', '')
                return answer

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

    def _get_or_create_session(self) -> Optional[str]:
        """Get existing session or create new one"""
        if self.session_id:
            return self.session_id

        if not self.client or not self.valves.CHAT_ID:
            return None

        try:
            session_name = f"Pipeline Session {hash(self.sessionKV)}"
            response = self.client.create_session(
                chat_id=self.valves.CHAT_ID,
                name=session_name
            )
            self.session_id = response["data"]["id"]
            if self.debug:
                print(f"Created new session with ID: {self.session_id}")
            return self.session_id
        except RAGflowAPIError as e:
            print(f"Error creating session: {str(e)}")
            return None

    def upload_file(self, file_paths: List[str], dataset_id: Optional[str] = None) -> dict:
        """Explicit file upload method"""
        if not self.client:
            return {"status": "error", "message": "RAGflow client not initialized"}

        target_dataset_id = dataset_id or self.valves.DATASET_ID
        if not target_dataset_id:
            return {"status": "error", "message": "No dataset ID specified"}

        try:
            response = self.client.upload_documents(
                dataset_id=target_dataset_id,
                file_paths=file_paths
            )
            return {"status": "success", "data": response["data"]}
        except RAGflowAPIError as e:
            return {"status": "error", "message": str(e)}