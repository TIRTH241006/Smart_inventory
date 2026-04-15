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

## Planned Features

- PDF upload integration for invoices in stock transactions (record supplier info and item origin)
- Barcode scanning integration
- Mobile app companion
- Advanced reporting and analytics
- Multi-location warehouse support
- API rate limiting and caching
- Email notifications for low stock
- Bulk import/export functionality

## Technical Improvements

- GraphQL API alongside REST
- Real-time updates with WebSockets
- Containerization with Docker
- CI/CD pipeline setup
- Performance optimization and caching

## Deployment Considerations

- Production Setup
- Environment variables for secrets
- Cloud database (AWS RDS, Google Cloud SQL)
- Static file serving (AWS S3, CloudFront)
- SSL/TLS certificates
- Monitoring and logging

## Scaling Strategies

- Database indexing and query optimization
- Caching layer (Redis)
- Load balancing
- Microservices architecture for larger scale

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

## Cloud Database

To keep your data safe even if the project folder is deleted locally, move the database to a managed cloud service and keep only code in Git.

Recommended flow:

1. Create a managed database on a provider such as Neon, Supabase Postgres, Railway Postgres, Aiven, PlanetScale, or a hosted MySQL service.
2. Copy the provider connection string into `.env` as `DATABASE_URL`.
3. Set `DJANGO_DEBUG=False`, update `DJANGO_ALLOWED_HOSTS`, and update `DJANGO_CSRF_TRUSTED_ORIGINS` for your deployed domain.
4. Run migrations against the cloud database:

```bash
python manage.py migrate
```

5. If you already have local data to move, export it first and then import it into the cloud database:

```bash
python manage.py dumpdata --exclude contenttypes --exclude auth.permission > data.json
python manage.py loaddata data.json
```

The app now supports cloud databases using `DATABASE_URL` for PostgreSQL or MySQL. If `DATABASE_URL` is not set, it falls back to the existing local database settings.
