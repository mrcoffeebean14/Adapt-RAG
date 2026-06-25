import requests

url = "http://127.0.0.1:8000/rag/query"
payload = {"query": "What are RNN models?", "session_id": "test_session_123"}
response = requests.post(url, json=payload)
data = response.json()
print("FULL JSON:", data)
print("EXTRACTED CONTENT:", data.get("result", {}).get("content"))
