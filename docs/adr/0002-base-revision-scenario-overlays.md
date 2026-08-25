# ADR 0002: Base revisions with scenario overlays

- Status: accepted
- Date: 2026-08-21

## Decision

Shared project content is versioned as an immutable Base Revision. A Scenario Revision stores only field overrides, visibility, and ordering differences and points to one Base Revision.

## Consequences

Sales, corporate, internal, and client outputs share one body of evidence without copy drift. Restoring history creates a new Draft. Published revisions and overrides are never rewritten.

