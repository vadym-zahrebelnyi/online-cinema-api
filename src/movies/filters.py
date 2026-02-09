from typing import Optional, List
from fastapi_filter.contrib.sqlalchemy import Filter
from pydantic import Field

from .models import MovieDB, GenreDB


class MovieFilter(Filter):
    """
    Filtering options for movie catalog.

    Supports:
    - partial case-insensitive title search
    - release year range filtering
    - sorting results
    """

    name__ilike: Optional[str] = Field(
        None,
        description="Case-insensitive partial match for movie title"
    )

    year__gte: Optional[int] = Field(
        None,
        description="Return movies released in or after this year"
    )

    year__lte: Optional[int] = Field(
        None,
        description="Return movies released in or before this year"
    )

    order_by: Optional[List[str]] = Field(
        None,
        description="Sorting fields: name, -name, year, -year"
    )

    class Constants(Filter.Constants):
        model = MovieDB
        fields = {
            "name": ["ilike"],
            "year": ["gte", "lte"],
        }


class GenreFilter(Filter):
    """
    Filtering options for genres.

    Allows partial case-insensitive search and sorting.
    """

    name__ilike: Optional[str] = Field(
        None,
        description="Case-insensitive partial match for genre name"
    )

    order_by: Optional[List[str]] = Field(
        None,
        description="Sorting fields: name, -name"
    )

    class Constants(Filter.Constants):
        model = GenreDB
        fields = {
            "name": ["ilike"],
        }
