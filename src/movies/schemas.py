from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CertificationRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class GenreRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class StarRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class DirectorRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class MovieCreate(BaseModel):
    name: str
    year: int = Field(..., ge=1900)
    time: int = Field(..., gt=0)

    imdb: Decimal = Field(..., ge=0, le=10)
    votes: int = Field(..., ge=0)

    meta_score: Optional[Decimal] = Field(None, ge=0, le=100)
    gross: Optional[Decimal] = Field(None, ge=0)

    price: Decimal = Field(..., ge=0)

    description: str
    certification_id: int

    genre_ids: List[int] = Field(default_factory=list)
    star_ids: List[int] = Field(default_factory=list)
    director_ids: List[int] = Field(default_factory=list)


class MovieUpdate(BaseModel):
    """
    PATCH schema.

    None → field unchanged
    [] → clear relations
    """

    name: Optional[str] = None
    year: Optional[int] = Field(None, ge=1800)
    time: Optional[int] = Field(None, gt=0)

    imdb: Optional[Decimal] = Field(None, ge=0, le=10)
    votes: Optional[int] = Field(None, ge=0)

    meta_score: Optional[Decimal] = Field(None, ge=0, le=100)
    gross: Optional[Decimal] = Field(None, ge=0)

    price: Optional[Decimal] = Field(None, ge=0)

    description: Optional[str] = None
    certification_id: Optional[int] = None

    genre_ids: Optional[List[int]] = None
    star_ids: Optional[List[int]] = None
    director_ids: Optional[List[int]] = None


class MovieListItem(BaseModel):
    """
    Lightweight movie view for catalog listing.
    """

    id: int
    uuid: UUID

    name: str
    year: int
    imdb: Decimal
    price: Decimal

    model_config = {"from_attributes": True}


class MovieDetail(BaseModel):
    """
    Full movie detail view.
    """

    id: int
    uuid: UUID

    name: str
    year: int
    time: int

    imdb: Decimal
    votes: int

    meta_score: Optional[Decimal]
    gross: Optional[Decimal]
    price: Decimal

    description: str

    certification: CertificationRead
    genres: List[GenreRead]
    stars: List[StarRead]
    directors: List[DirectorRead]

    model_config = {"from_attributes": True}


class MoviePagination(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


class MovieFilters(BaseModel):
    """
    Catalog filtering schema.
    """

    year_from: Optional[int] = None
    year_to: Optional[int] = None

    imdb_min: Optional[Decimal] = None
    imdb_max: Optional[Decimal] = None

    price_min: Optional[Decimal] = None
    price_max: Optional[Decimal] = None

    genre_id: Optional[int] = None
    star_id: Optional[int] = None
    director_id: Optional[int] = None


class MovieSearch(BaseModel):
    """
    Full-text style search.
    """

    query: str = Field(..., min_length=1)


class MovieListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[MovieListItem]
