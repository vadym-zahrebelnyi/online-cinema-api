from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from redis.asyncio import Redis

from src.cart.crud import CartCRUD
from src.cart.services import CartService
from src.cart.models import CartDB, CartItemDB
from src.movies.models import MovieDB
from src.cart.exceptions import (
    CartLimitExceededError,
    MovieAlreadyInCartError,
    MovieAlreadyOwnedError,
    MovieNotFoundError,
)
from src.cart.schemas import CartReadSchema


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock(spec=CartCRUD)


@pytest.fixture
def redis() -> AsyncMock:
    return AsyncMock(spec=Redis)


@pytest.fixture
def movie_a() -> MovieDB:
    return MovieDB(id=1, name="Film A", price=Decimal("10.00"))


@pytest.fixture
def movie_b() -> MovieDB:
    return MovieDB(id=2, name="Film B", price=Decimal("20.00"))


@pytest.fixture
def cart_item_a(movie_a: MovieDB) -> CartItemDB:
    return CartItemDB(id=101, movie=movie_a, added_at=datetime.utcnow())


@pytest.fixture
def cart_item_b(movie_b: MovieDB) -> CartItemDB:
    return CartItemDB(id=102, movie=movie_b, added_at=datetime.utcnow())


@pytest.fixture
def mock_db_session_begin(repo: AsyncMock):
    mock_db_session = AsyncMock()
    mock_db_session.begin.return_value.__aenter__.return_value = None
    repo.db = mock_db_session
    return mock_db_session


@pytest.fixture
def cart_service_instance(repo: AsyncMock, redis: AsyncMock) -> CartService:
    return CartService(repo, redis)


@pytest.mark.asyncio
async def test_get_cart_user_authenticated(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    movie_a: MovieDB,
    movie_b: MovieDB,
):
    user_id = 1
    cart_item1 = CartItemDB(id=101, movie=movie_a, added_at=datetime.utcnow())
    cart_item2 = CartItemDB(id=102, movie=movie_b, added_at=datetime.utcnow())
    mock_cart_db = CartDB(id=10, user_id=user_id, items=[cart_item1, cart_item2])

    repo.get_cart_by_user.return_value = mock_cart_db

    result = await cart_service_instance.get_cart(user_id=user_id, anon_id=None)

    assert isinstance(result, CartReadSchema)
    assert result.id == mock_cart_db.id
    assert result.total_items == 2
    assert result.total_price == Decimal("30.00")
    assert len(result.items) == 2
    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    redis.smembers.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_cart_user_authenticated_empty(
    repo: AsyncMock, redis: AsyncMock, cart_service_instance: CartService
):
    user_id = 1
    repo.get_cart_by_user.return_value = CartDB(id=10, user_id=user_id, items=[])

    result = await cart_service_instance.get_cart(user_id=user_id, anon_id=None)

    assert isinstance(result, CartReadSchema)
    assert result.id == 10
    assert result.total_items == 0
    assert result.total_price == Decimal("0.00")
    assert len(result.items) == 0
    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    redis.smembers.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_cart_user_authenticated_no_cart_in_db(
    repo: AsyncMock, redis: AsyncMock, cart_service_instance: CartService
):
    user_id = 1
    repo.get_cart_by_user.return_value = None

    result = await cart_service_instance.get_cart(user_id=user_id, anon_id=None)

    assert isinstance(result, CartReadSchema)
    assert result.id is None
    assert result.total_items == 0
    assert result.total_price == Decimal("0.00")
    assert len(result.items) == 0
    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    redis.smembers.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_cart_anonymous(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    movie_a: MovieDB,
    movie_b: MovieDB,
):
    anon_id = "test-anon-id"

    redis.smembers.return_value = {b'1', b'2'}
    repo.get_movies_by_ids.return_value = [movie_a, movie_b]

    result = await cart_service_instance.get_cart(user_id=None, anon_id=anon_id)

    assert isinstance(result, CartReadSchema)
    assert result.id is None
    assert result.total_items == 2
    assert result.total_price == Decimal("30.00")
    assert len(result.items) == 2
    repo.get_movies_by_ids.assert_awaited_once_with([1, 2])
    redis.smembers.assert_awaited_once_with(f"cart:{anon_id}")
    repo.get_cart_by_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_cart_anonymous_empty_redis(
    repo: AsyncMock, redis: AsyncMock, cart_service_instance: CartService
):
    anon_id = "test-anon-id"
    redis.smembers.return_value = set()

    result = await cart_service_instance.get_cart(user_id=None, anon_id=anon_id)

    assert isinstance(result, CartReadSchema)
    assert result.id is None
    assert result.total_items == 0
    assert result.total_price == Decimal("0.00")
    assert len(result.items) == 0
    repo.get_movies_by_ids.assert_not_awaited()
    redis.smembers.assert_awaited_once_with(f"cart:{anon_id}")
    repo.get_cart_by_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_movie_user_success(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
    movie_a: MovieDB,
):
    user_id = 1
    movie_id = movie_a.id
    mock_cart = CartDB(id=1, user_id=user_id, items=[])

    repo.get_movie.return_value = movie_a
    repo.is_movie_available_to_buy.return_value = False
    repo.get_cart_by_user.return_value = mock_cart
    repo.item_exists.return_value = False
    repo.add_item.return_value = None

    await cart_service_instance.add_movie(movie_id, user_id, anon_id=None)

    repo.get_movie.assert_awaited_once_with(movie_id)
    repo.is_movie_available_to_buy.assert_awaited_once_with(user_id, movie_id)
    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    repo.item_exists.assert_awaited_once_with(mock_cart.id, movie_id)
    repo.add_item.assert_awaited_once_with(mock_cart.id, movie_id)
    mock_db_session_begin.begin.assert_awaited_once()
    redis.sadd.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_movie_user_create_cart_success(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
    movie_a: MovieDB,
):
    user_id = 1
    movie_id = movie_a.id
    mock_new_cart = CartDB(id=2, user_id=user_id, items=[])

    repo.get_movie.return_value = movie_a
    repo.is_movie_available_to_buy.return_value = False
    repo.get_cart_by_user.return_value = None
    repo.create_cart.return_value = mock_new_cart
    repo.item_exists.return_value = False
    repo.add_item.return_value = None

    await cart_service_instance.add_movie(movie_id, user_id, anon_id=None)

    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    repo.create_cart.assert_awaited_once_with(user_id)
    repo.item_exists.assert_awaited_once_with(mock_new_cart.id, movie_id)
    repo.add_item.assert_awaited_once_with(mock_new_cart.id, movie_id)
    mock_db_session_begin.begin.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_movie_user_movie_not_found(
    repo: AsyncMock, redis: AsyncMock, cart_service_instance: CartService
):
    movie_id = 999
    repo.get_movie.return_value = None

    with pytest.raises(MovieNotFoundError):
        await cart_service_instance.add_movie(movie_id, user_id=1, anon_id=None)
    repo.get_movie.assert_awaited_once_with(movie_id)
    repo.db.begin.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_movie_user_already_owned(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
    movie_a: MovieDB,
):
    user_id = 1
    movie_id = movie_a.id
    repo.get_movie.return_value = movie_a
    repo.is_movie_available_to_buy.return_value = True

    with pytest.raises(MovieAlreadyOwnedError):
        await cart_service_instance.add_movie(movie_id, user_id, anon_id=None)
    repo.is_movie_available_to_buy.assert_awaited_once_with(user_id, movie_id)
    mock_db_session_begin.begin.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_movie_user_already_in_cart(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
    movie_a: MovieDB,
):
    user_id = 1
    movie_id = movie_a.id
    mock_cart = CartDB(id=1, user_id=user_id, items=[])

    repo.get_movie.return_value = movie_a
    repo.is_movie_available_to_buy.return_value = False
    repo.get_cart_by_user.return_value = mock_cart
    repo.item_exists.return_value = True

    with pytest.raises(MovieAlreadyInCartError):
        await cart_service_instance.add_movie(movie_id, user_id, anon_id=None)
    repo.item_exists.assert_awaited_once_with(mock_cart.id, movie_id)
    mock_db_session_begin.begin.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_movie_user_cart_limit_exceeded(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
    movie_a: MovieDB,
):
    user_id = 1
    movie_id = movie_a.id
    full_cart_items = []
    for i in range(CartService.MAX_CART_ITEMS):
        item = CartItemDB(id=i+1, movie=MovieDB(id=i+1, name=f"Movie {i+1}"))
        full_cart_items.append(item)

    full_cart = CartDB(id=1, user_id=user_id, items=full_cart_items)

    repo.get_movie.return_value = movie_a
    repo.is_movie_available_to_buy.return_value = False
    repo.get_cart_by_user.return_value = full_cart
    repo.item_exists.return_value = False

    with pytest.raises(CartLimitExceededError):
        await cart_service_instance.add_movie(movie_id, user_id, anon_id=None)
    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    repo.item_exists.assert_awaited_once_with(full_cart.id, movie_id)
    mock_db_session_begin.begin.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_movie_anonymous_success(
    repo: AsyncMock, redis: AsyncMock, cart_service_instance: CartService, movie_a: MovieDB
):
    anon_id = "test-anon-id"
    movie_id = movie_a.id
    
    repo.get_movie.return_value = movie_a
    redis.sismember.return_value = False
    redis.sadd.return_value = None
    redis.expire.return_value = None

    await cart_service_instance.add_movie(movie_id, user_id=None, anon_id=anon_id)

    repo.get_movie.assert_awaited_once_with(movie_id)
    redis.sismember.assert_awaited_once_with(f"cart:{anon_id}", str(movie_id))
    redis.sadd.assert_awaited_once_with(f"cart:{anon_id}", str(movie_id))
    redis.expire.assert_awaited_once_with(f"cart:{anon_id}", 604800)
    repo.db.begin.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_movie_anonymous_already_in_cart(
    repo: AsyncMock, redis: AsyncMock, cart_service_instance: CartService, movie_a: MovieDB
):
    anon_id = "test-anon-id"
    movie_id = movie_a.id
    
    repo.get_movie.return_value = movie_a
    redis.sismember.return_value = True

    with pytest.raises(MovieAlreadyInCartError):
        await cart_service_instance.add_movie(movie_id, user_id=None, anon_id=anon_id)
    
    redis.sismember.assert_awaited_once_with(f"cart:{anon_id}", str(movie_id))
    redis.sadd.assert_not_awaited()


# --- Tests for remove_item ---

@pytest.mark.asyncio
async def test_remove_item_user_success(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
):
    user_id = 1
    movie_id = 10
    mock_cart = CartDB(id=1, user_id=user_id)

    repo.get_cart_by_user.return_value = mock_cart
    repo.remove_item.return_value = None

    await cart_service_instance.remove_item(movie_id, user_id, anon_id=None)

    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    repo.remove_item.assert_awaited_once_with(mock_cart.id, movie_id)
    mock_db_session_begin.begin.assert_awaited_once()
    redis.srem.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_item_user_cart_not_found(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
):
    user_id = 1
    movie_id = 10

    repo.get_cart_by_user.return_value = None

    await cart_service_instance.remove_item(movie_id, user_id, anon_id=None)

    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    repo.remove_item.assert_not_awaited()
    mock_db_session_begin.begin.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_item_anonymous_success(
    repo: AsyncMock, redis: AsyncMock, cart_service_instance: CartService
):
    anon_id = "test-anon-id"
    movie_id = 10

    redis.srem.return_value = None

    await cart_service_instance.remove_item(movie_id, user_id=None, anon_id=anon_id)

    redis.srem.assert_awaited_once_with(f"cart:{anon_id}", str(movie_id))
    repo.remove_item.assert_not_awaited()



@pytest.mark.asyncio
async def test_clear_cart_user_success(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
):
    user_id = 1
    mock_cart = CartDB(id=1, user_id=user_id)

    repo.get_cart_by_user.return_value = mock_cart
    repo.clear_cart.return_value = None

    await cart_service_instance.clear_cart(user_id, anon_id=None)

    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    repo.clear_cart.assert_awaited_once_with(mock_cart.id)
    mock_db_session_begin.begin.assert_awaited_once()
    redis.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_clear_cart_user_cart_not_found(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
):
    user_id = 1

    repo.get_cart_by_user.return_value = None

    await cart_service_instance.clear_cart(user_id, anon_id=None)

    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    repo.clear_cart.assert_not_awaited()
    mock_db_session_begin.begin.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_cart_anonymous_success(
    repo: AsyncMock, redis: AsyncMock, cart_service_instance: CartService
):
    anon_id = "test-anon-id"

    redis.delete.return_value = None

    await cart_service_instance.clear_cart(user_id=None, anon_id=anon_id)

    redis.delete.assert_awaited_once_with(f"cart:{anon_id}")
    repo.clear_cart.assert_not_awaited()


@pytest.mark.asyncio
async def test_merge_anon_cart_no_anon_items(
    repo: AsyncMock, redis: AsyncMock, cart_service_instance: CartService
):
    anon_id = "test-anon-id"
    user_id = 1

    redis.smembers.return_value = set()

    await cart_service_instance.merge_anon_cart(anon_id, user_id)

    redis.smembers.assert_awaited_once_with(f"cart:{anon_id}")
    repo.db.begin.assert_not_awaited()
    redis.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_merge_anon_cart_no_valid_movies(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
):
    anon_id = "test-anon-id"
    user_id = 1

    redis.smembers.return_value = {b'1', b'2'}
    repo.get_movies_by_ids.return_value = []

    await cart_service_instance.merge_anon_cart(anon_id, user_id)

    redis.smembers.assert_awaited_once_with(f"cart:{anon_id}")
    repo.get_movies_by_ids.assert_awaited_once_with([1, 2])
    redis.delete.assert_awaited_once_with(f"cart:{anon_id}")
    mock_db_session_begin.begin.assert_awaited_once()


@pytest.mark.asyncio
async def test_merge_anon_cart_success(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
    movie_a: MovieDB,
    movie_b: MovieDB,
):
    anon_id = "test-anon-id"
    user_id = 1
    mock_user_cart = CartDB(id=10, user_id=user_id, items=[])

    redis.smembers.return_value = {b'1', b'2'}
    repo.get_movies_by_ids.return_value = [movie_a, movie_b]
    repo.get_cart_by_user.return_value = mock_user_cart
    repo.is_movie_available_to_buy.return_value = False
    repo.item_exists.return_value = False
    repo.add_item.return_value = None

    await cart_service_instance.merge_anon_cart(anon_id, user_id)

    repo.get_movies_by_ids.assert_awaited_once_with([1, 2])
    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    assert repo.is_movie_available_to_buy.call_count == 2
    assert repo.item_exists.call_count == 2
    assert repo.add_item.call_count == 2
    mock_db_session_begin.begin.assert_awaited_once()
    redis.delete.assert_awaited_once_with(f"cart:{anon_id}")


@pytest.mark.asyncio
async def test_merge_anon_cart_owned_items_skipped(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
    movie_a: MovieDB,
    movie_b: MovieDB,
):
    anon_id = "test-anon-id"
    user_id = 1
    mock_user_cart = CartDB(id=10, user_id=user_id, items=[])

    redis.smembers.return_value = {b'1', b'2'}
    repo.get_movies_by_ids.return_value = [movie_a, movie_b]
    repo.get_cart_by_user.return_value = mock_user_cart
    # Movie 1 is owned, Movie 2 is not
    repo.is_movie_available_to_buy.side_effect = [True, False]
    repo.item_exists.return_value = False
    repo.add_item.return_value = None

    await cart_service_instance.merge_anon_cart(anon_id, user_id)

    repo.get_movies_by_ids.assert_awaited_once_with([1, 2])
    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    assert repo.is_movie_available_to_buy.call_count == 2
    assert repo.item_exists.call_count == 1
    assert repo.add_item.call_count == 1
    mock_db_session_begin.begin.assert_awaited_once()
    redis.delete.assert_awaited_once_with(f"cart:{anon_id}")


@pytest.mark.asyncio
async def test_merge_anon_cart_already_in_user_cart_skipped(
    repo: AsyncMock,
    redis: AsyncMock,
    cart_service_instance: CartService,
    mock_db_session_begin: AsyncMock,
    movie_a: MovieDB,
    movie_b: MovieDB,
):
    anon_id = "test-anon-id"
    user_id = 1
    mock_user_cart = CartDB(id=10, user_id=user_id, items=[])

    redis.smembers.return_value = {b'1', b'2'}
    repo.get_movies_by_ids.return_value = [movie_a, movie_b]
    repo.get_cart_by_user.return_value = mock_user_cart
    repo.is_movie_available_to_buy.return_value = False
    repo.item_exists.side_effect = [True, False]
    repo.add_item.return_value = None

    await cart_service_instance.merge_anon_cart(anon_id, user_id)

    repo.get_movies_by_ids.assert_awaited_once_with([1, 2])
    repo.get_cart_by_user.assert_awaited_once_with(user_id)
    assert repo.is_movie_available_to_buy.call_count == 2
    assert repo.item_exists.call_count == 2
    assert repo.add_item.call_count == 1
    mock_db_session_begin.begin.assert_awaited_once()
    redis.delete.assert_awaited_once_with(f"cart:{anon_id}")
