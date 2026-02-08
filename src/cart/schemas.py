from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MovieCartReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    price: Decimal
    year: int
    genres: list[str]

    @field_validator("genres", mode="before")
    @classmethod
    def parse_genres(cls, v):
        if v and isinstance(v[0], object) and hasattr(v[0], "name"):
            return [g.name for g in v]
        return v


class CartItemReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    movie: MovieCartReadSchema
    added_at: datetime


class CartReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    items: Annotated[list[CartItemReadSchema], Field(default_factory=list)]
    total_price: Decimal = Decimal(0)
    total_items: int = 0


class CartItemCreateSchema(BaseModel):
    movie_id: Annotated[int, Field(gt=0)]


class CartItemRemoveSchema(BaseModel):
    id: Annotated[int, Field(gt=0)]
