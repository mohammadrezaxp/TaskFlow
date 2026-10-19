# TaskFlow

**An evolving Django application for organizations, projects, tasks, and team collaboration.**

[Routes](config/urls.py) · [Organization logic](apps/organizations/views.py) · [Task API](apps/tasks/views.py) · [Tests](tests/) · [MIT license](LICENSE)

TaskFlow models work as **organization → project → task → comment**. It combines Django pages with REST endpoints for account management and work resources. The codebase is under active development: the core APIs exist, while several presentation modules remain scaffolding.

## Implementation status

| Area | Current state |
| --- | --- |
| Accounts | Custom user, registration, profile endpoints, and login/register pages |
| Organizations | Organization API, owner membership creation, and member-scoped queries |
| Projects | Project API with organization-membership filtering |
| Tasks | Task/comment APIs, assignee validation, task positioning, and Kanban view |
| Tokens | JWT issue and refresh routes exist |
| API authentication | Default DRF authentication is session-based; JWT routes do not by themselves enable bearer authentication on every view |
| Interface | Account/organization pages and task views coexist with template-only screens |
| Other modules | Notifications, activity, analytics, calendar, messages, and settings screens are not evidence of completed backend workflows |
| Tests | Account, organization, project, tenant-isolation, UI, and smoke test modules |

## Stack

Python 3.12+ · Django 5.2 · Django REST Framework · django-environ · SQLite/PostgreSQL · pytest

See [requirements.txt](requirements.txt) for dependency versions. drf-spectacular is configured, but the root URL configuration currently does not expose a Swagger/schema route.

## Local setup

```bash
git clone https://github.com/mohammadrezaxp/TaskFlow.git
cd TaskFlow
python -m venv .venv
```

| Shell | Activate environment |
| --- | --- |
| macOS/Linux | `source .venv/bin/activate` |
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` (`cp` in Bash or `Copy-Item` in PowerShell), replace the example `SECRET_KEY`, and leave `DATABASE_URL=sqlite:///db.sqlite3` for a local database.

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open the [dashboard](http://127.0.0.1:8000/), [registration page](http://127.0.0.1:8000/accounts/register/), or [health endpoint](http://127.0.0.1:8000/health/).

## Routes and first exploration

| Route | Purpose |
| --- | --- |
| `/accounts/register/`, `/accounts/login/` | Browser account flows |
| `/accounts/profile/` | Current browser profile |
| `/accounts/api/register/` | API registration |
| `/accounts/api/token/`, `/accounts/api/token/refresh/` | JWT token endpoints |
| `/accounts/api/me/` | Current-user API |
| `/api/v1/organizations/` | Organization API |
| `/api/v1/projects/` | Project API |
| `/api/v1/tasks/` | Task API |
| `/api/v1/task-comments/` | Comment API |
| `/api/v1/tasks/{id}/reorder/` | PATCH task position |
| `/organizations/`, `/projects/`, `/tasks/kanban/` | Browser work views |
| `/health/` | Application response check |

Authenticate through the browser login before using session-protected APIs in DRF's browsable interface. Unsafe session-authenticated requests require a CSRF token.

1. Register and log in.
2. Create an organization; the creator receives an owner membership.
3. Inspect organization and project resources in the browsable API.
4. Create tasks for an accessible project and inspect the Kanban view.

The health endpoint returns:

```json
{"status":"ok","app":"TaskFlow"}
```

This is an application response check, not a database or dependency readiness probe.

## Architecture

```text
apps/accounts/       User model, forms, serializers, and account routes
apps/organizations/  Organizations, memberships, and organization views
apps/projects/       Project models and REST endpoints
apps/tasks/          Task/comment models, endpoints, and Kanban view
apps/core/           Shared application utilities
apps/notifications/  Module reserved for notification implementation
apps/activity/       Module reserved for activity implementation
config/settings/    Base, development, and production settings
tests/              Automated test modules
templates/          Application screens
static/taskflow/    CSS and browser behavior
```

## Validation

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
pytest -v
```

The existence of tenant-isolation tests does not establish that every write path is fully isolated. Changes to organization/project/task relationships should include cross-organization create and update tests.

## Configuration and next steps

`.env` is loaded by `django-environ`. Configure `SECRET_KEY`, `DATABASE_URL`, and `ALLOWED_HOSTS` for your environment. `manage.py` defaults to `config.settings.development`, which forces debug mode and local hosts; deployment requires an explicit production settings module.

The next implementation work is to finish template-backed workflows, audit membership/role authorization on all writes, consistently enable the chosen API authentication scheme, and expose the configured OpenAPI documentation. These are development tasks, not currently guaranteed features.

## Contributing and license

Include reproduction steps and tests with fixes, particularly for authorization and tenant isolation. Report security concerns privately to [the maintainer](mailto:m.mahmoudi.xp@gmail.com). Licensed under [MIT](LICENSE).
