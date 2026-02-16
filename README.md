# 🎬 Online Cinema API

Online Cinema API is a backend service built with **FastAPI** that provides a movie marketplace workflow including authentication, movie catalog management, shopping cart functionality, order processing, and Stripe-based payments.

The application follows a modular architecture, uses Celery for background processing, and is containerized with Docker.

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

# 🏗 Architecture

The project follows a domain-based modular structure:

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

Each module encapsulates its models, schemas, services, and routes.

---

# ⚙ Running the Project

The supported way to run the project is via Docker.

### Development

```bash
docker compose -f docker-compose.dev.yml up --build
```

### Production

```bash
docker compose -f docker-compose.prod.yml up -d
```

The Docker environment includes:

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

Seed database:

```bash
uv run -m src.db_manager.run --all
```

Available management commands:

```bash
# seed only movies
uv run -m src.db_manager.run --movies

# create roles and superuser
uv run -m src.db_manager.run --su
```

---

# 👤 Authentication & Authorization

## Features

* Email-based registration
* Account activation via token (24-hour expiration)
* Resend activation link
* Password reset via email token
* JWT authentication (access & refresh tokens)
* Refresh token storage and revocation
* Logout invalidates refresh token
* Role-based access control

## Roles

* **USER**
* **MODERATOR**
* **ADMIN**

Moderators can manage movie catalog data.
Admins can manage users and change roles.

---

# 🎥 Movies Module

Users can:

* Browse movies (pagination)
* View movie details
* Search by title, description, actor, or director
* Filter and sort movies
* Add movies to favorites
* Remove movies from favorites
* Rate movies (1–10 scale)

Moderators can:

* Create, update, delete movies
* Manage genres, directors, and actors
* Prevent deletion of purchased movies

---

# 🛒 Shopping Cart

The cart is strictly bound to authenticated users.

* Each user has exactly **one cart**
* Cart is created automatically (after registration or on first add action)

If a non-authenticated user attempts to access cart endpoints:

```
401 Unauthorized
```

### Cart Rules

* The same movie cannot be added twice
* Already purchased movies cannot be added
* Cart must not be empty to create an order

---

# 📦 Orders

Users can:

* Create an order from their cart
* View order history
* Cancel an order before payment

Order statuses:

* `pending`
* `paid`
* `canceled`

### Business Rules

* Purchased movies are excluded
* Total amount is validated before payment
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
* External Stripe transaction ID storage
* Email confirmation after successful payment

Payment records preserve historical pricing.

---

# 🔁 Background Tasks

Celery is used for:

* Sending activation emails
* Sending password reset emails
* Removing expired activation tokens
* Removing expired reset tokens (via Celery Beat)

---

# 🧪 Testing

Run tests:

```bash
pytest
```

Includes:

* Unit tests
* Integration tests
* Functional tests

---

# 📚 API Documentation

Available at:

* `/docs` (Swagger UI)

---

# 🔐 Security

* Password hashing
* JWT authentication
* Refresh token revocation
* Role-based authorization
* Token expiration validation
* Stripe webhook verification
* Database-level integrity constraints
