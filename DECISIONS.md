# Architecture Decisions

## 0001. Use repository root as the CardOps AI monorepo root

The requested tree names the root folder `cardops-ai/`, but the existing Git repository is already checked out as `D:\WORK\GitRepos\PERSONAL\cardops`. Creating a nested `cardops-ai` folder would make the working tree awkward and hide scripts from the repository root. The monorepo structure is therefore implemented at the current repository root.

## 0002. SQLite-first backend with PostgreSQL-compatible ORM models

The local MVP uses SQLite through SQLAlchemy 2 and Alembic. Models avoid SQLite-only assumptions where practical so PostgreSQL can be introduced later.

## 0003. Database-backed local job queue

Directory scans and future OCR/AI/eBay jobs use a durable `jobs` table. The worker claims queued rows transactionally and records result/error metadata. This avoids requiring Redis for local setup while leaving the job interface replaceable.

## 0004. Provider capability system before live integrations

External systems are represented through provider capability records. Mock/local providers can operate without credentials, while restricted providers report missing credentials or disabled features instead of disabling the whole app.

## 0005. Demo fixtures are generated locally

Demo card photos are generated placeholder PNGs under `data/demo/images`. This avoids copyrighted marketplace photos while exercising the same ingestion service used for user-selected folders.
