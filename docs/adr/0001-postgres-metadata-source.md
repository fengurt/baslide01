# ADR 0001: Postgres is the metadata source of truth

- Status: accepted
- Date: 2026-08-21

## Decision

Postgres 18.4 owns project identity, revisions, fields, source and asset versions, artifact definitions, builds, history, and active pointers. Files are content-addressed by SHA-256; their metadata and active version are selected by Postgres.

## Consequences

Published pages do not read copy from hand-maintained JSON or HTML. Legacy catalogs and offline pages are generated compatibility artifacts. Database migrations and backups are required before schema changes.

