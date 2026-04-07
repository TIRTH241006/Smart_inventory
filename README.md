# Smart Inventory Management System

A full-stack Django + DRF inventory platform with secure authentication, Google OAuth, analytics dashboard, and complete CRUD for products, suppliers, and stock transactions.

## Features

- User registration, login, logout
- Google OAuth login via django-allauth
- Protected dashboard and API routes
- Product management: create, update, delete, search, pagination
- Supplier management: create, update, delete
- Stock transactions (IN/OUT) with automatic product quantity updates
- Low stock alerts in dashboard
- CSV export for products and transactions
- Django admin support for all core entities
- Responsive Tailwind-based modern UI with animations

## Stack

- Backend: Django, Django REST Framework
- Database: MySQL (with SQLite fallback for local quick run)
- Frontend: Django Templates + Tailwind CSS + Vanilla JS + Chart.js
- Auth: Django Auth + django-allauth (Google)

## Setup

1. Create and activate virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` values into your environment.
4. Configure Google OAuth App in Django Admin under Social Applications.
5. Run migrations:

```bash
python manage.py migrate
```

6. Create superuser:

```bash
python manage.py createsuperuser
```

7. Start server:

```bash
python manage.py runserver
```

## Key Routes

- Home: `/`
- Login: `/login/`
- Register: `/register/`
- Dashboard: `/dashboard/`
- Inventory: `/inventory/`
- Suppliers: `/suppliers/`
- Transactions: `/transactions/`
- Admin: `/admin/`
- Google OAuth: `/accounts/google/login/`

## API Routes

- `/api/products/`
- `/api/suppliers/`
- `/api/transactions/`
- `/api/low-stock/`
- `/api/dashboard/summary/`

## Notes

- Session authentication and CSRF protection are enabled.
- ORM usage protects against SQL injection when using provided APIs.
- For deployment, set `DJANGO_DEBUG=False` and use secure host/origin values.
