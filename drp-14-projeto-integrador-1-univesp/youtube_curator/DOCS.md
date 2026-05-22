YouTube Curator — Architecture \& Run Guide

What It Is

A Django web application that lets store employees (vendedores) watch and track curated YouTube training videos, organized into thematic modules for a Minas Gerais artisan products retailer.



Architecture Decisions

Framework \& Language

Django 5.2.1 — chosen for batteries-included auth, ORM, admin panel, and migrations with minimal boilerplate.

Python with python-decouple for 12-factor-style environment variable management (no hardcoded secrets).

Project Structure: Two Django Apps

App	Responsibility

accounts	Authentication only — login/logout via Django's built-in auth\_views. No custom User model needed.

curator	All business logic — modules, videos, progress tracking, YouTube search.

The accounts app is intentionally thin. Django's contrib.auth User model is used directly; no custom model was created because the default fields were sufficient.



Database: SQLite

SQLite (db.sqlite3) was chosen for zero-configuration local development. The ORM abstraction means swapping to Postgres for production requires only a one-line DATABASES change in settings.



Three Core Models (curator/models.py)



TrainingModule  ──< CuratedVideo >── UserProgress >── User

TrainingModule — A category/playlist (e.g., "Técnicas de Venda"). Has a slug for clean URLs and default\_keywords for pre-filling search queries.

CuratedVideo — A YouTube video saved to a module. Stores youtube\_id (unique), metadata (title, thumbnail, channel, duration). Has computed properties youtube\_url and embed\_url to keep templates clean.

UserProgress — A through-table with unique\_together(user, video). Tracks whether each user has watched each video. toggle\_progress flips the boolean and stamps watched\_at.

YouTube Integration: Thin Service Layer (curator/services/youtube.py)

A plain Python module (not a class) with two public functions:



search\_videos(query, max\_results, language) — calls the YouTube Data API v3 /search endpoint, then enriches results with durations via a second call to /videos?part=contentDetails.

\_fetch\_durations(api\_key, video\_ids) — internal helper that batch-fetches ISO 8601 durations and converts them to human-readable M:SS / H:MM:SS via \_parse\_iso8601\_duration.

Two API calls per search was an intentional trade-off: the /search endpoint does not return duration, so a second batch call to /videos is required. It's batched (all IDs in one request) to stay quota-efficient.



Custom exception YouTubeAPIError is raised on any HTTP or config failure and caught in the view to show a user-facing messages.error.



Views: All Login-Required (curator/views.py)

All views are decorated with @login\_required. The flow:



URL	View	Purpose

/dashboard/	dashboard	Shows all modules with watched/total counts per user

/modulo/<slug>/	module\_detail	Lists videos in a module with per-user watch status

/buscar/	search	YouTube search form + results

/salvar-video/	save\_video	POST — saves a video from search results to a module

/progresso/<id>/	toggle\_progress	POST — toggles watched state

/remover/<id>/	remove\_video	POST — deletes a video from a module

save\_video uses get\_or\_create to prevent duplicate entries — saving the same video twice is a no-op that shows an info message instead of an error.



Seed Command (curator/management/commands/seed\_modules.py)

Three fixed training modules are pre-defined and created via manage.py seed\_modules. Uses get\_or\_create so it's idempotent — safe to run multiple times. The three modules are:



Conhecimento do Produto — artisan products of Minas Gerais

Técnicas de Venda — sales skills

Atendimento ao Cliente — customer service

Admin Panel (curator/admin.py)

All three models are registered with customized ModelAdmin classes:



TrainingModuleAdmin — shows video count per module (computed column).

CuratedVideoAdmin — filterable by module, searchable by title/channel.

UserProgressAdmin — filterable by watched status.

Testing

pytest-django with pytest.ini — tests live in tests/ (not inside apps).

conftest.py provides shared fixtures: user, staff\_user, module, video.

Test files: test\_models.py, test\_youtube\_service.py, test\_views.py.

pytest-cov for coverage reports.

Settings Highlights (youtube\_curator/settings.py)

LANGUAGE\_CODE = "pt-br" and TIME\_ZONE = "America/Sao\_Paulo" — localized for Brazil.

LOGIN\_REDIRECT\_URL = "/dashboard/" — after login, users land on the dashboard.

Templates are in a top-level templates/ directory (not per-app), referenced via BASE\_DIR / "templates".

Run the Tests



pytest

With coverage:





pytest --cov=curator --cov=accounts --cov-report=term-missing

Key File Map



youtube\_curator/

├── .env                          # your secrets (not committed)

├── .env.example                  # template for secrets

├── manage.py

├── requirements.txt

├── pytest.ini

├── db.sqlite3                    # SQLite database (auto-created)

├── templates/

│   ├── base.html

│   ├── accounts/login.html

│   └── curator/

│       ├── dashboard.html

│       ├── module\_detail.html

│       └── search.html

├── accounts/                     # auth app (thin)

│   └── urls.py                   # login + logout only

├── curator/                      # main app

│   ├── models.py                 # TrainingModule, CuratedVideo, UserProgress

│   ├── views.py                  # all 6 views

│   ├── urls.py                   # URL patterns

│   ├── admin.py                  # admin registrations

│   ├── services/youtube.py       # YouTube API wrapper

│   └── management/commands/

│       └── seed\_modules.py       # python manage.py seed\_modules

├── tests/

│   ├── conftest.py               # shared fixtures

│   ├── test\_models.py

│   ├── test\_youtube\_service.py

│   └── test\_views.py

└── youtube\_curator/

&#x20;   ├── settings.py

&#x20;   └── urls.py



What was changed

New features

Registration — /accounts/cadastro/ creates a user account (name, username, password), auto-seeds the 3 training modules for that user, and logs them in immediately.

PostgreSQL — replaced SQLite; config is driven by DB\_\* env vars.

Per-user modules — TrainingModule now has a created\_by FK. Every user sees only their own modules and videos. Two users can save the same YouTube video independently.

Remove button — previously staff-only, now visible to the module owner (any registered user for their own modules).

Files changed

File	Change

requirements.txt	Added psycopg2-binary

.env.example / .env	Added DB\_\* PostgreSQL vars

youtube\_curator/settings.py	Switched DATABASES to PostgreSQL

curator/models.py	TrainingModule + created\_by; CuratedVideo unique moved from global youtube\_id → (youtube\_id, module)

curator/migrations/0002\_per\_user\_modules.py	New migration

curator/services/modules.py	New — shared DEFAULT\_MODULES data + seed\_user\_modules(user)

curator/views.py	All queries scoped to request.user; remove\_video checks module ownership

curator/admin.py	Shows created\_by column

curator/management/commands/seed\_modules.py	Now requires --username arg

accounts/views.py	New RegisterForm + register view

accounts/urls.py	Added /accounts/cadastro/ route

templates/accounts/login.html	Added "Criar conta" button

templates/accounts/register.html	New registration form template

templates/curator/module\_detail.html	Remove button condition: is\_staff → module.created\_by == request.user

tests/conftest.py	module fixture now sets created\_by=user

tests/test\_models.py	Slug uniqueness test updated for per-user semantics

tests/test\_views.py	Tests updated to match new ownership rules

Setup steps (PostgreSQL + first run)

1\. Install/start PostgreSQL

Download from postgresql.org or use Docker:





docker run -d --name pg -e POSTGRES\_PASSWORD=yourpassword -p 5432:5432 postgres:16

2\. Create the database



psql -U postgres -c "CREATE DATABASE youtube\_curator;"

3\. Fill in .env



DB\_PASSWORD=yourpassword

4\. Install dependencies



pip install -r requirements.txt

5\. Run migrations



python manage.py migrate

6\. Create an admin (optional)



python manage.py createsuperuser

\# then seed their modules:

python manage.py seed\_modules --username <your-admin-username>

7\. Start the server



python manage.py runserver

Open http://127.0.0.1:8000 → click "Criar conta" to register. The 3 training modules are created automatically on registration.
