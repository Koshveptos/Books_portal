from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from typing import TypeVar



class BookBase(BaseModel):
    title: str = Field(max_length=50)
    author: str = Field(max_length=50)
    year: Optional[str] = Field(None, max_length=4)
    publisher:  Optional[str] = Field(None, max_length=50)
    isbn: str = Field(max_length=20)
    description: Optional[str] = Field(None, max_length=1023)
    cover: Optional[str] = Field(None, max_length=255)
    language: Optional[str] = Field(None, max_length=50)
    file_url: str = Field(max_length=255)


class BookCreate(BookBase):
    categories: List[int]= []
    tags:  List[int] | None = []


class BookUpdate(BookCreate):
    pass

class BookPartial(BookUpdate):
    title: str  | None = Field(None,max_length=50)
    author: str | None = Field(None,max_length=50)
    isbn: str | None = Field(None,max_length=20)
    file_url: str | None = Field(None,max_length=255)
class Book(BookBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    categories: List["Category"] = Field(default_factory=  list)
    tags: List['Tag'] | None = Field(default_factory=list)




#class BookResource(BaseModel):

class CategoryBase(BaseModel):
    name_categories: str = Field(max_length=50, nullable=False )
    description: str | None = Field(None,max_length=255)


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    books: List["Book"] = Field (default_factory=list)




class TagBase(BaseModel):
    name_tag:str = Field(max_length=50, nullable = False)

class TagCreate(TagBase):
    pass


class Tag(TagBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    books: List["Book"] = Field(default_factory=list)
