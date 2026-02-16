# 🎬 Online Cinema API

A production-ready **Online Cinema backend platform** built with **FastAPI**, designed to provide a full movie marketplace experience including authentication, movie catalog management, shopping cart, ordering system, and Stripe-based payments.

The project follows clean architecture principles, role-based access control, token-based authentication (JWT), background task processing with Celery, and containerized deployment using Docker.

---

# 📌 Table of Contents

* [Overview](#overview)
* [Architecture](#architecture)
* [Core Features](#core-features)
* [Tech Stack](#tech-stack)
* [Project Structure](#project-structure)
* [Authentication & Authorization](#authentication--authorization)
* [Movies Module](#movies-module)
* [Cart Module](#cart-module)
* [Orders Module](#orders-module)
* [Payments Module](#payments-module)
* [Background Tasks (Celery)](#background-tasks-celery)
* [Docker Setup](#docker-setup)
* [Poetry Dependency Management](#poetry-dependency-management)
* [Database & Migrations](#database--migrations)
* [Testing](#testing)
* [CI/CD](#cicd)
* [API Documentation](#api-documentation)

---

# 📖 Overview

Online Cinema is a backend service that allows users to:

* Register and activate accounts via email
* Authenticate using JWT tokens
* Browse and search movies
* Like, comment, and rate movies
* Add movies to cart and purchase them
* Pay via Stripe
* Receive email notifications
* Manage roles (User, Moderator, Admin)

The system enforces strict business logic and validation to ensure data consistency and secure transactions.

---

# 🏗 Architecture

The project follows a modular architecture with separation of concerns:

* `accounts` — Authentication, profiles, roles, tokens
* `movies` — Movie catalog, filtering, ratings
* `cart` — Shopping cart logic
* `orders` — Order creation & management
* `payments` — Stripe integration
* `security` — JWT handling and password hashing
* `core` — Database, configuration, shared utilities

It uses:

* Service layer pattern
* Dependency injection
* Pydantic schemas
* SQLAlchemy ORM
* Async support where applicable

---

# 🚀 Core Features

## 👤 Authentication & Account Management

* Email-based registration
* Email activation (24h expiration)
* Resend activation link
* Password reset via email token
* JWT authentication (access + refresh)
* Secure logout (refresh token revocation)
* Password complexity validation
* Celery-beat cleanup of expired tokens

### User Roles

* **USER** – Basic access to platform
* **MODERATOR** – Manage movies & content
* **ADMIN** – Full access, manage users & roles

---

## 🎥 Movies Module

Users can:

* Browse movies (pagination)
* View detailed descriptions
* Search (title, description, actor, director)
* Filter (year, IMDb rating, genre)
* Sort (price, popularity, release date)
* Like / dislike movies
* Rate movies (10-point scale)
* Comment and reply
* Add/remove favorites

Moderators can:

* Create / Update / Delete movies
* Manage genres, stars, directors
* Prevent deletion of purchased movies

---

## 🛒 Cart Module

* Add movies (only if not purchased)
* Prevent duplicate entries
* Remove movies
* Clear cart
* View cart details
* Validate purchase availability

Each user has exactly one cart.

---

## 📦 Orders Module

* Create order from cart
* Prevent duplicate pending orders
* Validate movie availability
* Cancel order before payment
* Track order status:

  * `pending`
  * `paid`
  * `canceled`

Each order stores historical price snapshots.

---

## 💳 Payments Module

Integrated with **Stripe**.

Features:

* Secure payment processing
* Webhook validation
* Store external payment ID
* Payment status tracking:

  * `successful`
  * `canceled`
  * `refunded`
* Email confirmation after payment
* Payment history per user

All financial records preserve historical pricing.

---

# ⚙ Tech Stack

* **FastAPI**
* **SQLAlchemy**
* **PostgreSQL**
* **Redis**
* **Celery + Celery Beat**
* **Stripe**
* **MinIO (S3 compatible storage)**
* **Poetry**
* **Docker & Docker Compose**
* **GitHub Actions**
* **Pytest**
* **Alembic**
* **JWT (Access + Refresh)**

---

# 📁 Project Structure

```
src/
│
├── accounts/
├── movies/
├── cart/
├── orders/
├── payments/
├── security/
├── core/
│
docker/
alembic/
commands/
configs/
```

The project is organized into domain-based modules for scalability and maintainability.

---

# 🐳 Docker Setup

Run the entire system with one command:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Services include:

* FastAPI application
* PostgreSQL
* Redis
* Celery worker
* Celery beat
* MinIO

For production:

```bash
docker compose -f docker-compose.prod.yml up -d
```

---

# 📦 Poetry Dependency Management

Install dependencies:

```bash
poetry install
```

Activate virtual environment:

```bash
poetry shell
```

Add dependency:

```bash
poetry add package-name
```

Dependencies are defined in:

```
pyproject.toml
```

---

# 🗄 Database & Migrations

The project uses **Alembic** for migrations.

Create migration:

```bash
alembic revision --autogenerate -m "message"
```

Apply migrations:

```bash
alembic upgrade head
```

---

# 🔁 Background Tasks (Celery)

Used for:

* Email sending
* Token cleanup
* Scheduled tasks (celery-beat)

Run worker:

```bash
celery -A src.storages.celery_app worker --loglevel=info
```

Run beat scheduler:

```bash
celery -A src.storages.celery_app beat --loglevel=info
```

---

# 🧪 Testing

The project includes:

### Unit Tests

* Validation logic
* Utility functions
* Business rules

### Integration Tests

* DB interaction
* JWT workflows
* Authentication

### Functional Tests

* Registration flow
* Movie browsing
* Cart → Order → Payment flow

Run tests:

```bash
pytest
```

---

# 🔄 CI/CD

GitHub Actions pipeline includes:

* flake8 / black (linting)
* mypy (type checking)
* pytest (tests)
* coverage report
* Deployment to AWS EC2 (after merge)

---

# 📚 API Documentation

* Built using **OpenAPI 3**
* Swagger UI available at:

```
/docs
```

* ReDoc available at:

```
/redoc
```

Access can be restricted to authorized users.

---

# 🔐 Security

* Password hashing
* JWT authentication
* Token revocation
* Role-based access control
* Stripe webhook verification
* Strong validation rules
* Unique constraints and DB-level integrity

---

# 📌 Future Improvements

* Recommendation system
* Watch history tracking
* Subscription plans
* Partial payments
* Caching layer optimization
* Performance profiling

---

# 👨‍💻 Author

Backend project for an Online Cinema platform.
Designed for production-level architecture, scalability, and clean separation of concerns.

---

If you'd like, I can now:

* Make it **more enterprise-style**
* Make it **simpler (for portfolio)**
* Add **architecture diagram**
* Or format it specifically for GitHub with badges**

