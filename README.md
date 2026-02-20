# 🎬 Online Cinema API

Online Cinema API is a backend service built with **FastAPI** that provides authentication, movie catalog management, shopping cart functionality, order processing, and Stripe-based payments.

The application is containerized and designed to run inside Docker.

---

# 🚀 Technology Stack

* FastAPI
* SQLAlchemy
* PostgreSQL
* Redis
* Celery + Celery Beat
* Stripe
* MinIO
* Nginx (reverse proxy)
* Alembic (via migrator)
* uv
* Docker & Docker Compose

---

# 🏗 Architecture

The project follows an **application-based modular structure**:

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

Each module contains its models, schemas, services, and routes.

---

# ⚙ Running the Project

The project is intended to run **inside Docker only**.

All commands are executed either:

* via Docker Compose wrapper
* or directly inside the running container

Local execution without Docker is not supported.


## 🐳 Docker Environment

The Docker environment differs between development and production configurations.

Development configuration includes services required for local development.

Production configuration includes additional infrastructure components
such as Nginx and other deployment-specific services.

The set of running containers may differ between `docker-compose.dev.yml`
and `docker-compose.prod.yml`.


### Development


```bash
docker compose -f docker-compose.dev.yml up --build
```

### Production

The production configuration is intended for deployment only.
It requires valid SSL certificates and proper server configuration.
It is not designed to be run locally.

---

# 🌍 Environment Configuration

The project requires a `.env` file based on `.env.sample`.

Before running the project:

cp .env.sample .env

Without a properly configured `.env` file,
the development environment will not start.

# 🔁 Reverse Proxy

The application runs behind **Nginx**.

Nginx is configured as a reverse proxy and handles routing for the application.

Production configuration differs from development configuration.

---

# 🗄 Database & Migrations

Migrations are executed through the project migrator inside Docker.

Manual Alembic execution is not required.

Database seeding:

```bash
uv run -m src.db_manager.run --all
```

Other available commands:

```bash
uv run -m src.db_manager.run --movies
uv run -m src.db_manager.run --su
```

---

# 👤 Authentication & Authorization

## Features

* Email registration
* Account activation (24h expiration)
* Resend activation link
* Password reset via email token
* JWT authentication (access & refresh tokens)
* Refresh token revocation on logout
* Role-based access control

## Roles

* USER
* MODERATOR
* ADMIN

Authorization is required only for protected endpoints.
The application does not enforce global authorization at startup.

---

# 🎥 Movies

Users can:

* Browse movies (pagination)
* View movie details
* Search
* Filter
* Sort
* Add to favorites
* Rate movies

Moderators can:

* Create / update / delete movies
* Manage genres, actors, directors
* Prevent deletion of purchased movies

(Comments are not implemented.)

---

# 🛒 Shopping Cart

The cart can be used without immediate authentication.

- Before login, cart data is stored in cookies.
- After successful authentication, the cart is attached to the user account.
- Once attached, it becomes persistent and linked to the user.

Cart operations require authentication only for order creation.

---

# 📦 Orders

Users can:

* Create orders from cart
* View order history
* Cancel orders before payment

Order statuses:

* pending
* paid
* canceled

Business rules:

* Cart must not be empty
* Purchased movies are excluded
* Order items store historical price

---

# 💳 Payments

Stripe integration includes:

* Payment session creation
* Webhook validation
* Payment status tracking
* External payment ID storage
* Email confirmation after successful payment

---

# 🔁 Background Tasks

Celery is used for:

* Sending activation emails
* Sending password reset emails
* Removing expired tokens

---

# 🧪 Testing

The project includes:

- Unit tests

Integration and end-to-end tests are not implemented.
---

# 📚 API Documentation

Available at:

* `/docs`
* `/redoc`

---

# 🔐 Security

* Password hashing
* JWT authentication
* Refresh token revocation
* Role-based access control
* Stripe webhook verification
* Token expiration validation