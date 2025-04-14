from pydantic import BaseModel, ConfigDict, Field


class BookBase(BaseModel):
    title: str = Field(max_length=50)
    author: str = Field(max_length=50)
    year: str | None = Field(None, max_length=4)
    publisher: str | None = Field(None, max_length=50)
    isbn: str = Field(max_length=20)
    description: str | None = Field(None, max_length=1023)
    cover: str | None = Field(None, max_length=255)
    language: str | None = Field(None, max_length=50)
    file_url: str = Field(max_length=255)


class BookCreate(BookBase):
    categories: list[int] = []
    tags: list[int] | None = []


class BookUpdate(BookCreate):
    pass


class BookPartial(BookUpdate):
    title: str | None = Field(None, max_length=50)
    author: str | None = Field(None, max_length=50)
    isbn: str | None = Field(None, max_length=20)
    file_url: str | None = Field(None, max_length=255)


class Book(BookBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    categories: list["Category"] = Field(default_factory=list)
    tags: list["Tag"] | None = Field(default_factory=list)


# class BookResource(BaseModel):


class CategoryBase(BaseModel):
    name_categories: str = Field(max_length=50, nullable=False)
    description: str | None = Field(None, max_length=255)


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    books: list["Book"] = Field(default_factory=list)


class TagBase(BaseModel):
    name_tag: str = Field(max_length=50, nullable=False)


class TagCreate(TagBase):
    pass


class Tag(TagBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    books: list["Book"] = Field(default_factory=list)
