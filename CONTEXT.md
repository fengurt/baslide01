# Baslide Project Publishing

Baslide turns a versioned project knowledge base into consistent public and internal artifacts.

## Language

**Project**:
The highest stable entity, identified by a code such as `P009`, that owns a subject, its sources, scenarios, revisions, and artifacts.
_Avoid_: using a directory, deck number, or output file as the project identity.

**Base Revision**:
An immutable published version of the content shared by every scenario in a project. A mutable draft becomes a new Base Revision when published.
_Avoid_: changing a published revision in place.

**Scenario**:
A named use context such as a sales landing page, corporate profile, internal briefing, or client edition.
_Avoid_: duplicating a project to express audience-specific differences.

**Scenario Revision**:
An immutable set of overrides, visibility, and ordering decisions applied to one Base Revision for one Scenario.
_Avoid_: copying every shared value into a scenario.

**Module**:
A stable semantic block such as Hero, Partners, Reports, Decision Loop, Services, Values, or CTA.
_Avoid_: defining modules by screen coordinates or slide numbers.

**Field**:
The smallest stable, categorized content unit. Every visible string and accessibility string has a Field code that survives revisions.
_Avoid_: anonymous text embedded in templates.

**Source**:
A registered document or data file that explains where a Field or Asset came from.
_Avoid_: referencing an unregistered path as evidence.

**Asset**:
A stable media identity whose versions are stored by SHA-256 in the content-addressed file store.
_Avoid_: storing image or document binaries in Postgres.

**Artifact**:
A declared output form such as Landing, Slides, Subpage, PNG, PDF, or Offline HTML.
_Avoid_: treating a one-off export as a new project.

**Build**:
One deterministic rendering of an Artifact from an exact Base Revision and Scenario Revision, with a coverage manifest and checksums.
_Avoid_: combining outputs from different revisions.

**Draft**:
A mutable working revision. Draft changes refresh previews but do not alter public Artifact builds.
_Avoid_: exposing autosaved draft data on public routes.

**Publish**:
The validated transaction that freezes revisions, builds all required Artifacts, verifies coverage, and switches active pointers together.
_Avoid_: publishing one output at a time.

