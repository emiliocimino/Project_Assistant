# Wiki Structure and Schema (v3)

> Wiki about all European projects followed by a single enterprise. Multi-project.
> Read by LLM agents and by colleagues (wiki explorer). Maintained by LLM agents from chat text and uploaded documents.
> This document is the single source of truth. It is stored as /wiki/schema.md and injected into the agent prompts.

Design principles:
1. Entities (organizations, people, assets, studies, concepts) are global. Projects hold only the project-specific facet.
2. Every file has frontmatter with a stable ID, type, status and provenance.
3. Every fact is traceable to a source. Sources live outside the wiki and are never modified.
4. Relations are typed and always written on both ends.
5. Authored notes and sourced facts are never mixed in the same file.

---

## 1. Locations

- `/sources/` (outside the wiki, read-only): original documents. Each document has a source ID, and its pages are split in `/sources/pages/<SOURCE_ID>/`. A manifest (maintained by the application, not by agents) lists for each source: id, original filename, title, document_date, type, hash, ingestion status.
- `/wiki/` (read-write for the writer agent only): everything described below. Base folder for all wiki links.

External material (a GitHub repository, a web page) is also a source: it gets a source ID, with URL, retrieval date and, for repositories, commit hash or release.

---

## 2. Conventions

### 2.1 Naming and IDs
- File name = ID + `.md`. ASCII slugs only: no spaces, brackets or special characters. Names with special characters use the plain acronym (TU/e becomes TUE).
- The original name goes in the `title` field. The wiki explorer displays `title`.
- ID patterns:
  - project: `<ACRONYM>` (example `euroFMX`)
  - project-scoped nodes: `<ACRONYM>_WP3`, `<ACRONYM>_T3-2`, `<ACRONYM>_D3-1`, `<ACRONYM>_MS3`
  - organization: `org_<ACRONYM>`; person: `person_name-surname`
  - `asset_<slug>`, `study_<slug>`, `concept_<slug>`, `synergy_<slug>`, `note_<slug>`, `todo_<slug>`
- Dates are ISO: `YYYY-MM-DD`. Meeting files: `YYYY-MM-DD_<title>_minutes.md`.
- Language of the wiki: English.

### 2.2 Frontmatter (mandatory on every file)
```yaml
id: euroFMX_T3-2
type: task
title: Full readable title
aliases:
  - other spellings or names
status: active
source: official
confidence: high
confidentiality: SEN
last_updated: 2026-01-01
tags:
  - concept_example
sources:
  - SRC-0007
relations:
  part_of:
    - euroFMX_WP3
```
- `type`: project, wp, task, deliverable, milestone, review, meeting, risk, participation, organization, person, asset, study, concept, synergy, note, todo.
- `status`: draft, active, completed, deprecated, change_suspected (for facts whose update is not yet confirmed, see 2.6).
- `source`: official, meeting, study, external, note (authored note).
- `confidence`: high, medium, low. Inferences are always low.
- `confidentiality`: PU, SEN, enterprise-internal. Informational for readers.
- `tags`: only concepts from the controlled vocabulary (2.8).
- Notes also carry `author` (a person ID or `unknown`) and `created`.

### 2.3 Typed relations (always on both ends)
A relation is never written on one file only. When adding or removing a relation, update both files.

| Written on A | Mirror written on B |
|---|---|
| task `part_of` wp | wp `has_task` task |
| wp `part_of` project | project `has_wp` wp |
| deliverable or milestone `part_of` project | project `has_deliverable`, `has_milestone` |
| deliverable `from_task` task | task `produces_deliverable` deliverable |
| task `depends_on` task | task `required_by` task |
| wp `depends_on` wp | wp `required_by` wp |
| task `produces` asset | asset `produced_in` task |
| task `uses` asset | asset `used_in` task |
| task `supported_by` study | study `supports` task |
| participation `of_org` org | org `participates_via` participation |
| participation `in_project` project | project `has_participant` participation |
| participation `works_on` task | task `involves` participation |
| person `member_of` org | org `has_member` person |
| person `plays_role_in` participation | participation `has_person` person |
| asset `owned_by` org | org `owns` asset |
| any node `tagged` concept (tags) | concept `tagged_by` node |
| synergy `connects` any node | node `in_synergy` synergy |
| todo `concerns` any node | node `has_todo` todo |
| `related_to` | `related_to` |

### 2.4 Relation lists in the body
Human-readable lists mirroring relations (for example "Tasks of this partner") sit in marked blocks, maintained by the writer:
```
<!-- relations-list:start -->
- [[euroFMX_T3-2]] short role description
<!-- relations-list:end -->
```
The writer updates them every time a relation changes. They are derived from the frontmatter, which stays the reference.

### 2.5 Citations
- Every fact carries `[src: SRC-0007, p.12]` inline, and the file lists its source IDs in `sources`.
- Information given in chat without a document: `[src: chat, YYYY-MM-DD]`.
- External sources: `[src: SRC-0042]`, the manifest holds URL, date and revision.

### 2.6 Edit and conflict policy
- Read a file before editing it. Never delete files or content that is still valid.
- New fact: add it with its citation.
- Correction of an error: replace in place, record the change in `log.md`, update `last_updated`.
- Contradiction between sources: classify, using the document_date of each source (not the ingestion date).
  - Evolution: a later source describes something different. Keep the earlier statement with its dates in the section `## History and conflicts` ("until DATE: X; from DATE: Y"), update the current state. Mark `status: change_suspected` after a single later source. Promote to the new state after a second consistent source or confirmation from the user.
  - Perspective: sources of the same period disagree. Keep both, attributed to their sources and dates, in `## History and conflicts`. Do not pick one unless the authority ranking decides it.
  - Authority ranking: amendment > Grant Agreement and DoA > submitted deliverable > review report > meeting minutes > informal note or chat. Higher authority wins a perspective conflict. Record the reasoning in the entry.
  - If none applies, the writer does not decide: it reports the conflict (see the writer prompt).
- Deprecation: `status: deprecated` plus relation `superseded_by`. No trash folder. Version control keeps history.

### 2.7 People and notes
- Person files hold: background and competences, responsibilities, role in each project (living part), preferred contact channel (optional). Only sourced facts.
- No personality, attitude or psychological labels. Observable, sourced facts only (for example participation in meetings, with citation).
- Notes are shared. They record the author when known, otherwise `author: unknown`. Readers must present them as notes by an author, never as established facts.

### 2.8 Controlled concept vocabulary
- Tags and concept files use a fixed list, defined once and stored in `entities/concepts/`.
- Agents never invent concepts. A new concept is proposed to the user and added only after confirmation.
- Bootstrap: after the first project documents are ingested, an extraction pass proposes candidates (technologies, standards, methods, domains) with frequency. The user curates 10 to 15 concepts, with aliases.
- Current list: to be defined.

### 2.9 Bootstrapping a project
The first source ingested for a new project is its Grant Agreement or DoA. It creates the skeleton: project, WPs, tasks, deliverables, milestones, participations, organizations. Later documents attach to it. If a project does not exist yet, other documents are not ingested before asking.

---

## 3. Tree

```
/wiki/
  schema.md          this document
  index.md           top-level map: projects (one line each), global entity folders, open synergies
  log.md             append-only: date, files touched, reason, sources ingested (by SRC ID)
  entities/
    organizations/   org_<ACRONYM>.md
    people/          person_<name-surname>.md
    assets/          asset_<slug>.md
    studies/         study_<slug>.md
    concepts/        concept_<slug>.md
  projects/
    <ACRONYM>/
      <ACRONYM>.md
      participation/ <ACRONYM>_org_<ACRONYM-ORG>.md
      plan/
        wps/          <ACRONYM>_WPX.md
        tasks/        <ACRONYM>_TX-Y.md
        deliverables/ <ACRONYM>_DX-Y.md
        milestones/   <ACRONYM>_MSX.md
      governance/
        reviews/      <ACRONYM>_review_<period>.md
        meetings/     YYYY-MM-DD_<title>_minutes.md
      risks/          <ACRONYM>_risk_<slug>.md
      results/        <ACRONYM>_result_<slug>.md
  synergies/         synergy_<slug>.md
  notes/             note_<slug>.md
  todos/             todo_<slug>.md
```

---

## 4. Node descriptions

### index.md and project index
> index.md: map of the wiki. `<ACRONYM>.md`: full name, call, grant number, dates, reporting periods, objectives, consortium overview, links to WPs and key milestones, status.

### entities/organizations
> Full name, type, country, general competences, list of projects (via participations), owned assets. Project-specific information lives in the participation files.

### entities/people
> Background and competences, organization, responsibilities. Role in each project through participation relations. See 2.7.

### entities/assets
> Software, dataset, model, methodology, demonstrator, repository.
> Description, owner and involved partners, tasks and projects where produced or used, version history, license and IPR notes, reuse potential, external links (as sources).

### entities/studies
> Papers, articles, technical reports. Citation, link to the source ID, short summary in own words, key findings, limits, supported tasks and related concepts.

### entities/concepts
> Hub nodes from the controlled vocabulary: definition, aliases, why it matters for the enterprise, nodes tagged with it (relation list).

### projects/<ACRONYM>/participation
> One file per partner in this project. Role summary, WPs and tasks with allocated Person Months, team (project managers and technical people), deliverables and assets led or contributed. This is the main source for "which activities does ORG have in project X".

### plan/wps, tasks, deliverables, milestones
> WP: objective, tasks and deliverables, dependencies, lead and partners, link to results.
> Task: description, leader, partners, dependencies, assets produced or used, supporting studies, dated progress log with citations.
> Deliverable: title, type, dissemination level, due month, lead, contributors, status, linked tasks and milestones, link to the source of the submitted document.
> Milestone: objective, verification means, due month, linked tasks, deliverables, partners, status.
> Plan items change only through amendments (see conflict policy).

### governance
> Reviews: named by reporting period, with review date in frontmatter. Partner contributions, results and recommendations, follow-ups, links to the related nodes.
> Meetings: scope (internal, WP, consortium), participants, topics, key points, decisions, next steps. Action items become todo files.

### risks and results
> Risks: description, probability, impact, mitigation, owner, linked tasks, status.
> Results: achieved outputs: key exploitable results, dissemination outputs, KPIs. Linked to the producing assets, deliverables and tasks.

### synergies
> Cross-project synergy. Connected nodes (tasks, assets, concepts, organizations), the reason (shared asset, technology, partner, standard or use case), `perspective` (the organization ID whose viewpoint it takes, if any), expected benefit, action needed, owner. New synergies start as `status: draft`. The reader may propose hypotheses in answers without writing them.

### notes
> Shared authored notes. Author when available, otherwise unknown. Relations to any node.

### todos
> One file per action item. Frontmatter holds `status` (open, in-progress, done, blocked), `start`, `due`, `owner` and a relation to the concerned node. Completion changes `status`, the file does not move.