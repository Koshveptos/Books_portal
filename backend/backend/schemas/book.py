
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BookCreate(BaseModel):
    title: str = Field(max_length=50)
    author: str = Field(max_length=50)
    year: Optional[str] = Field(None, max_length=4)
    publisher:  Optional[str] = Field(None, max_length=4)
    isbn: str = Field(max_length=20)
    description: Optional[str] = Field(None, max_length=1023)
    cover: Optional[str] = Field(None, max_length=255)
    language: Optional[str] = Field(None, max_length=50)
    file_url: str = Field(max_length=255)
