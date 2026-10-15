# TaskFlow

TaskFlow is a professional task management and project collaboration backend built with Django 5.2 LTS and Django REST Framework.

## Architecture

TaskFlow follows a modular Django app structure:
- `apps/accounts`: Custom User model and authentication management.
- `apps/organizations`: Multi-tenant organization and team management.
- `apps/projects`: Project planning and organization.
- `apps/tasks`: Task tracking, assignment, and status workflows.
- `apps/notifications`: Notification dispatch and management.
- `apps/activity`: Activity logging and auditing.
- `apps/core`: Core utilities and shared base models.

## Tech Stack

- **Python 3.12+**
- **Django 5.2 LTS**
- **Django REST Framework**
- **PostgreSQL / SQLite** (SQLite fallback for local development)
- **django-environ**
- **drf-spectacular**
- **pytest & pytest-django**

## Installation & Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/mohammadrezaxp/TaskFlow.git
   cd TaskFlow
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows Git Bash
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   Copy `.env.example` to `.env` and set appropriate values.
   ```bash
   cp .env.example .env
   ```

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Run tests:
   ```bash
   pytest -v
   ```

## Current Implementation Status (Phase 1)
- Project initialization and modular app structure completed.
- Custom User model configured.
- Database and environment settings configured.
- Health check endpoint implemented at `/health/`.
- Smoke tests configured and passing.
