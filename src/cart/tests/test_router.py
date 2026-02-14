from unittest.mock import AsyncMock
from decimal import Decimal

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.accounts.dependencies import get_current_user_optional
from src.accounts.models import UserDB
from src.cart.dependencies import get_anon_cart_id, get_cart_service
from src.cart.exceptions import (
    CartLimitExceededError,
    MovieAlreadyInCartError,
    MovieAlreadyOwnedError,
    MovieNotFoundError,
)
from src.cart.router import router as cart_router
from src.cart.schemas import CartReadSchema
from src.cart.services import CartService


@pytest.fixture
def mock_get_cart_service():
    """Mocks the get_cart_service dependency."""
    return AsyncMock(spec=CartService)


@pytest.fixture
def mock_get_anon_cart_id():
    """Mocks get_anon_cart_id to return a fixed anonymous ID."""
    return "test-anon-id"


@pytest.fixture
def mock_get_current_user_optional():
    """Mocks the get_current_user_optional dependency."""
    return AsyncMock(spec=get_current_user_optional)


@pytest.fixture
def app(
    mock_get_cart_service: AsyncMock,
    mock_get_anon_cart_id: str,
    mock_get_current_user_optional: AsyncMock,
):
    """Fixture to set up a FastAPI app with mocked dependencies."""
    _app = FastAPI()
    _app.include_router(cart_router)
    _app.dependency_overrides[get_cart_service] = lambda: mock_get_cart_service
    _app.dependency_overrides[get_anon_cart_id] = lambda: mock_get_anon_cart_id
    _app.dependency_overrides[get_current_user_optional] = mock_get_current_user_optional
    return _app


@pytest.fixture
def client(app: FastAPI):
    """Fixture for TestClient."""
    return TestClient(app)


@pytest.fixture
def authenticated_user_id() -> int:
    """Fixture for a common authenticated user ID."""
    return 1


@pytest.fixture
def authenticated_user_db(authenticated_user_id: int) -> UserDB:
    """Fixture for a mock authenticated UserDB object."""
    return UserDB(id=authenticated_user_id, email="test@example.com")


@pytest.fixture(autouse=True)
def setup_user_mocker(mock_get_current_user_optional: AsyncMock):
    """Sets default return for get_current_user_optional to None (anonymous)."""
    mock_get_current_user_optional.return_value = None


@pytest.fixture
def authenticated_client(
    client: TestClient,
    mock_get_current_user_optional: AsyncMock,
    authenticated_user_db: UserDB,
) -> TestClient:
    """Fixture to return a TestClient with an authenticated user."""
    mock_get_current_user_optional.return_value = authenticated_user_db
    return client


@pytest.mark.asyncio
async def test_get_my_cart_authenticated(
    authenticated_client: TestClient,
    mock_get_cart_service: AsyncMock,
    authenticated_user_id: int,
    mock_get_anon_cart_id: str,
):
    """
    Test retrieving cart for an authenticated user.
    """
    mock_cart_data = CartReadSchema(id=10, items=[], total_items=0, total_price=Decimal("0.00"))
    mock_get_cart_service.get_cart.return_value = mock_cart_data

    response = authenticated_client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_cart_data.model_dump(by_alias=True)
    mock_get_cart_service.get_cart.assert_awaited_once_with(authenticated_user_id, mock_get_anon_cart_id)


@pytest.mark.asyncio
async def test_get_my_cart_anonymous(client: TestClient, mock_get_cart_service: AsyncMock, mock_get_anon_cart_id: str):
    """
    Test retrieving cart for an anonymous user.
    """
    mock_cart_data = CartReadSchema(id=None, items=[], total_items=0, total_price=Decimal("0.00"))
    mock_get_cart_service.get_cart.return_value = mock_cart_data

    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_cart_data.model_dump(by_alias=True)
    mock_get_cart_service.get_cart.assert_awaited_once_with(None, mock_get_anon_cart_id)


@pytest.mark.asyncio
async def test_add_to_cart_success_authenticated(
    authenticated_client: TestClient,
    mock_get_cart_service: AsyncMock,
    authenticated_user_id: int,
    mock_get_anon_cart_id: str,
):
    """
    Test adding a movie to cart for an authenticated user successfully.
    """
    movie_id = 10
    mock_get_cart_service.add_movie.return_value = None

    response = authenticated_client.post(f"/items/{movie_id}")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"status": "ok", "message": "Movie added to cart"}
    mock_get_cart_service.add_movie.assert_awaited_once_with(movie_id, authenticated_user_id, mock_get_anon_cart_id)


@pytest.mark.asyncio
async def test_add_to_cart_success_anonymous(
    client: TestClient, mock_get_cart_service: AsyncMock, mock_get_anon_cart_id: str
):
    """
    Test adding a movie to cart for an anonymous user successfully.
    """
    movie_id = 10
    mock_get_cart_service.add_movie.return_value = None

    response = client.post(f"/items/{movie_id}")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"status": "ok", "message": "Movie added to cart"}
    mock_get_cart_service.add_movie.assert_awaited_once_with(movie_id, None, mock_get_anon_cart_id)


@pytest.mark.asyncio
async def test_add_to_cart_movie_not_found(client: TestClient, mock_get_cart_service: AsyncMock):
    """
    Test adding a non-existent movie to cart.
    """
    movie_id = 999
    mock_get_cart_service.add_movie.side_effect = MovieNotFoundError("Movie not found.")

    response = client.post(f"/items/{movie_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Movie not found."}


@pytest.mark.asyncio
async def test_add_to_cart_movie_already_owned(
    authenticated_client: TestClient,
    mock_get_cart_service: AsyncMock,
    authenticated_user_id: int,
    mock_get_anon_cart_id: str,
):
    """
    Test adding an already owned movie to cart.
    """
    movie_id = 10
    mock_get_cart_service.add_movie.side_effect = MovieAlreadyOwnedError("You have already purchased this movie.")

    response = authenticated_client.post(f"/items/{movie_id}")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "You have already purchased this movie."}


@pytest.mark.asyncio
async def test_add_to_cart_movie_already_in_cart(
    authenticated_client: TestClient,
    mock_get_cart_service: AsyncMock,
    authenticated_user_id: int,
    mock_get_anon_cart_id: str,
):
    """
    Test adding a movie already in cart.
    """
    movie_id = 10
    mock_get_cart_service.add_movie.side_effect = MovieAlreadyInCartError("Movie is already in your cart.")

    response = authenticated_client.post(f"/items/{movie_id}")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Movie is already in your cart."}


@pytest.mark.asyncio
async def test_add_to_cart_cart_limit_exceeded(
    authenticated_client: TestClient,
    mock_get_cart_service: AsyncMock,
    authenticated_user_id: int,
    mock_get_anon_cart_id: str,
):
    """
    Test adding a movie when cart limit is exceeded.
    """
    movie_id = 10
    mock_get_cart_service.add_movie.side_effect = CartLimitExceededError(limit=50)

    response = authenticated_client.post(f"/items/{movie_id}")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Cart limit of 50 unique items exceeded."}


@pytest.mark.asyncio
async def test_add_to_cart_unexpected_error(client: TestClient, mock_get_cart_service: AsyncMock):
    """
    Test handling of unexpected errors during add to cart.
    """
    movie_id = 10
    mock_get_cart_service.add_movie.side_effect = Exception("Something went wrong")

    response = client.post(f"/items/{movie_id}")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "An unexpected error occurred."}


@pytest.mark.asyncio
async def test_remove_from_cart_authenticated(
    authenticated_client: TestClient,
    mock_get_cart_service: AsyncMock,
    authenticated_user_id: int,
    mock_get_anon_cart_id: str,
):
    """
    Test removing a movie from cart for an authenticated user.
    """
    movie_id = 10
    mock_get_cart_service.remove_item.return_value = None

    response = authenticated_client.delete(f"/items/{movie_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "message": "Item removed from cart"}
    mock_get_cart_service.remove_item.assert_awaited_once_with(movie_id, authenticated_user_id, mock_get_anon_cart_id)


@pytest.mark.asyncio
async def test_remove_from_cart_anonymous(
    client: TestClient, mock_get_cart_service: AsyncMock, mock_get_anon_cart_id: str
):
    """
    Test removing a movie from cart for an anonymous user.
    """
    movie_id = 10
    mock_get_cart_service.remove_item.return_value = None

    response = client.delete(f"/items/{movie_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "message": "Item removed from cart"}
    mock_get_cart_service.remove_item.assert_awaited_once_with(movie_id, None, mock_get_anon_cart_id)


@pytest.mark.asyncio
async def test_clear_cart_authenticated(
    authenticated_client: TestClient,
    mock_get_cart_service: AsyncMock,
    authenticated_user_id: int,
    mock_get_anon_cart_id: str,
):
    """
    Test clearing cart for an authenticated user.
    """
    mock_get_cart_service.clear_cart.return_value = None

    response = authenticated_client.delete("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "message": "Cart cleared"}
    mock_get_cart_service.clear_cart.assert_awaited_once_with(authenticated_user_id, mock_get_anon_cart_id)


@pytest.mark.asyncio
async def test_clear_cart_anonymous(
    client: TestClient, mock_get_cart_service: AsyncMock, mock_get_anon_cart_id: str
):
    """
    Test clearing cart for an anonymous user.
    """
    mock_get_cart_service.clear_cart.return_value = None

    response = client.delete("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "message": "Cart cleared"}
    mock_get_cart_service.clear_cart.assert_awaited_once_with(None, mock_get_anon_cart_id)
