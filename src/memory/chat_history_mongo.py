"""
Chat history storage using MongoDB backend.
"""

from datetime import datetime, timezone
from typing import List

from langchain_core.messages import BaseMessage, messages_from_dict

from src.db.mongo_client import db

collection = db["chat_history"]

# Only the most recent turns go to the LLM; older ones stay stored.
HISTORY_WINDOW = 20


class MongoDBChatMessageHistory:
    """Chat history for one user, stored in MongoDB."""

    def __init__(self, session_id: str):
        self.session_id = session_id

    async def add_message(self, message: BaseMessage) -> None:
        await collection.insert_one({
            "session_id": self.session_id,
            "type": message.type,
            "content": message.content,
            "additional_kwargs": message.additional_kwargs,
            "timestamp": datetime.now(timezone.utc),
        })

    async def get_messages(self) -> List[BaseMessage]:
        """The last HISTORY_WINDOW messages, oldest first."""
        cursor = (
            collection.find({"session_id": self.session_id})
            .sort("timestamp", -1)
            .limit(HISTORY_WINDOW)
        )
        docs = (await cursor.to_list(length=HISTORY_WINDOW))[::-1]
        return messages_from_dict([
            {
                "type": d["type"],
                "data": {"content": d["content"], "additional_kwargs": d.get("additional_kwargs", {})},
            }
            for d in docs
        ])

    async def clear(self) -> None:
        await collection.delete_many({"session_id": self.session_id})
