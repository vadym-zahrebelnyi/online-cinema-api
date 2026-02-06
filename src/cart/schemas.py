from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from sqlalchemy.sql.annotation import Annotated


class MovieCartReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    price: Decimal
    year: int
    genres: list[str]



class CartItemReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie: MovieCartReadSchema
    added_at: datetime


class CartReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    items: Annotated[list[CartItemReadSchema], Field(default_factory=list)]


class CartItemCreateSchema(BaseModel):
    movie_id: Annotated[int, Field(gt=0)]


class CartItemRemoveSchema(BaseModel):
    id: Annotated[int, Field(gt=0)]