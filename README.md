# 🎬 Online Cinema API

A backend service for an Online Cinema platform built with **FastAPI**.

The system provides a complete movie marketplace workflow including authentication, movie catalog management, shopping cart functionality, order processing, and Stripe-based payments.
The application is modular, Dockerized, and uses Celery for background processing.

---

# 🚀 Technology Stack

* **FastAPI**
* **SQLAlchemy**
* **PostgreSQL**
* **Redis**
* **Celery + Celery Beat**
* **Stripe**
* **MinIO (S3-compatible storage)**
* **Alembic (database migrations)**
* **uv (dependency management)**
* **Docker & Docker Compose**

---

# 🏗 Project Architecture

The project follows a modular, domain-based structure:

```
src/
├── accounts/
├── movies/
├── cart/
├── orders/
├── payments/
├── security/
├── core/
```

Each module encapsulates its models, schemas, services, and routes to ensure scalability and maintainability.

---

# ⚙ Installation & Running

## Using uv

Install dependencies:

```bash
uv sync
```

Run the application:

```bash
uv run python -m src.main
```

---

## Using Docker (Recommended)

Development:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Production:

```bash
docker compose -f docker-compose.prod.yml up -d
```

The environment includes:

* FastAPI application
* PostgreSQL
* Redis
* Celery Worker
* Celery Beat
* MinIO

---

# 🗄 Database

Apply migrations:

```bash
alembic upgrade head
```

Database management commands:

```bash
# Seed roles, dummy users, and movies
uv run -m src.db_manager.run --all

# Seed only movies
uv run -m src.db_manager.run --movies

# Create roles and superuser
uv run -m src.db_manager.run --su
```

---

# 👤 Authentication & Authorization

## Features

* Email-based registration
* Account activation via token (expires in 24 hours)
* Resend activation link
* Password reset via email token
* JWT authentication (access & refresh tokens)
* Refresh token storage and revocation
* Secure logout
* Role-based access control

## User Roles

* **USER** – Standard platform access
* **MODERATOR** – Manage movies and catalog data
* **ADMIN** – Full access including user management

---

# 🔐 Access Control Rules

### Public Access (No Authentication Required)

* Browse movie catalog
* View movie details
* Search, filter, and sort movies
* View genres

### Authentication Required

* Add movies to cart
* Manage cart
* Write comments
* Rate movies
* Add to favorites
* Create orders
* Make payments
* View order and payment history

If a protected endpoint is accessed without a valid JWT token, the system returns:

```
401 Unauthorized
```

---

# 🛒 Shopping Cart

* Each authenticated user has exactly **one cart**
* Cart is created automatically:

  * after registration
  * or lazily on the first add-to-cart action
* Guest carts are **not supported**

### Cart Validation Rules

* The same movie cannot be added twice
* Purchased movies cannot be added again
* Cart operations require authentication

---

# 📦 Orders

Users can:

* Create an order from the cart
* View order history
* Cancel an order before payment

Order statuses:

* `pending`
* `paid`
* `canceled`

### Order Guarantees

* Cart must not be empty
* Purchased movies are excluded
* Total amount is revalidated before payment
* Historical pricing is stored in order items

---

# 💳 Payments

Integrated with **Stripe**.

Features:

* Payment session creation
* Stripe webhook validation
* Payment status tracking:

  * `successful`
  * `canceled`
  * `refunded`
* External payment ID storage
* Email confirmation after successful payment

All payments preserve historical pricing data.

---

# 🔁 Background Tasks

Celery is used for:

* Sending emails
* Removing expired activation tokens
* Removing expired password reset tokens
* Scheduled background jobs (Celery Beat)

Run manually:

```bash
celery -A src.storages.celery_app worker --loglevel=info
```

```bash
celery -A src.storages.celery_app beat --loglevel=info
```

---

# 🧪 Testing

Run tests:

```bash
pytest
```

The test suite includes:

* Unit tests
* Integration tests
* Functional scenarios

---

# 📚 API Documentation

Available at:

* Swagger UI → `/docs`
* ReDoc → `/redoc`

---

# 🔐 Security Considerations

* Password hashing
* JWT authentication
* Refresh token revocation
* Role-based authorization
* Stripe webhook validation
* Token expiration enforcement
* Database-level integrity constraints
