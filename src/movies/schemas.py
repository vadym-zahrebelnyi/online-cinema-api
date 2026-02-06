from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CertificationReadSchema(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: int
    name: str


class GenreReadSchema(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: int
    name: str


class StarReadSchema(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: int
    name: str


class DirectorReadSchema(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: int
    name: str


class MovieBaseSchema(BaseModel):
    name: str
    year: int = Field(..., ge=1900)
    time: int = Field(..., gt=0)

    imdb: Decimal = Field(..., ge=0, le=10)
    votes: int = Field(..., ge=0)

    meta_score: Decimal | None = Field(None, ge=0, le=100)
    gross: Decimal | None = Field(None, ge=0)
    price: Decimal = Field(..., ge=0)

    description: str
    certification_id: int


class MovieCreateSchema(MovieBaseSchema):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    genre_ids: list[int] = Field(default_factory=list)
    star_ids: list[int] = Field(default_factory=list)
    director_ids: list[int] = Field(default_factory=list)


class MovieUpdateSchema(BaseModel):
    """
    PATCH schema.
    None → field unchanged
    [] → clear relations
    """
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    name: str | None = None
    year: int | None = Field(None, ge=1800)
    time: int | None = Field(None, gt=0)

    imdb: Decimal | None = Field(None, ge=0, le=10)
    votes: int | None = Field(None, ge=0)

    meta_score: Decimal | None = Field(None, ge=0, le=100)
    gross: Decimal | None = Field(None, ge=0)
    price: Decimal | None = Field(None, ge=0)

    description: str | None = None
    certification_id: int | None = None

    genre_ids: list[int] | None = None
    star_ids: list[int] | None = None
    director_ids: list[int] | None = None


class MovieListItemSchema(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    name: str
    year: int
    imdb: Decimal
    price: Decimal


class MovieDetailSchema(MovieBaseSchema):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID

    certification: CertificationReadSchema
    genres: list[GenreReadSchema]
    stars: list[StarReadSchema]
    directors: list[DirectorReadSchema]


class MoviePaginationSchema(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


class MovieFiltersSchema(BaseModel):
    year_from: int | None = None
    year_to: int | None = None

    imdb_min: Decimal | None = None
    imdb_max: Decimal | None = None

    price_min: Decimal | None = None
    price_max: Decimal | None = None

    genre_id: int | None = None
    star_id: int | None = None
    director_id: int | None = None


class MovieSearchSchema(BaseModel):
    query: str = Field(..., min_length=1)


class MovieListResponseSchema(BaseModel):
    total: int
    page: int
    size: int
    items: list[MovieListItemSchema]
