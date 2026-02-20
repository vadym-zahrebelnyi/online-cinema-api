from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MovieCartReadSchema(BaseModel):
    """
    Simplified movie representation for cart display.

    Contains only the essential information needed for the checkout summary,
    avoiding full movie details to reduce payload size.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str
    price: Decimal
    year: int
    genres: list[str]

    @field_validator("genres", mode="before")
    @classmethod
    def parse_genres(cls, v):
        """
        Flatten the list of GenreDB objects into a list of strings.

        This validator ensures that the API response contains a simple list
        of genre names (e.g., ["Action", "Sci-Fi"]) instead of nested objects,
        making it easier for the frontend to consume.
        """
        if v and isinstance(v[0], object) and hasattr(v[0], "name"):
            return [g.name for g in v]
        return v


class CartItemReadSchema(BaseModel):
    """
    Represents a single line item within the shopping cart.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    movie: MovieCartReadSchema
    added_at: datetime


class CartReadSchema(BaseModel):
    """
    Complete representation of a shopping cart state.

    Includes calculated totals and a list of items. This schema unifies data
    from both persistent storage (Database) and temporary storage (Redis).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    items: Annotated[list[CartItemReadSchema], Field(default_factory=list)]
    total_price: Decimal = Decimal(0)
    total_items: int = 0


class CartItemCreateSchema(BaseModel):
    """
    Schema for adding an item to the cart via request body.
    """

    movie_id: Annotated[int, Field(gt=0)]


class CartItemRemoveSchema(BaseModel):
    """
    Schema for removing an item from the cart via request body.
    """

    id: Annotated[int, Field(gt=0)]
