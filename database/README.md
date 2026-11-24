# Database Module

## Overview
This folder contains the database schema definitions, SQL migration files, and initial seeding scripts for **Research Commons**.

- **Primary Database:** PostgreSQL (with `pgvector` extension for vector indexing)
- **Object Storage:** MinIO (for raw paper harvest payloads)
- **Lead Maintainer:** Mokshith (coordinated with Suhas for vector/indexing needs)

---

## Folder Contents (Planned)
- `schema.sql`: Core relational DDL script creating tables for users, profiles, papers, posts, comments, follows, collections, and activity logs.
- `seed.sql`: Initial mock data for development testing across all modules.
- `migrations/`: Versioned migration scripts as the schema evolves.

---

## Setup Guidelines
1. Ensure PostgreSQL is installed and running locally on port `5432`.
2. Create the project database:
   ```sql
   CREATE DATABASE research_commons;
   ```
3. Enable pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Run schema scripts against `research_commons`.
