"""
Grade model for relevance scoring.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Grade(BaseModel):
    """Model for grading relevance of retrieved documents."""

    binary_score: Literal["yes", "no"] = Field(description="Is the context relevant to the question?")
