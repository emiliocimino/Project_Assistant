# LLM Wiki Structure for European Projects

> Wiki covering all European projects followed by a single enterprise.
> Design principles:
> 1. Entities (organizations, people, assets, studies, concepts) are global. Projects hold only the project-specific facet.
> 2. Every file is typed, has a stable ID and provenance, and links to others through typed relations.
> 3. Official facts (sourced) and personal content (interpretations, notes) are never mixed in the same file.
> 4. Derived views (backlinks, synergy lists, TODO boards) are generated, not hand-written.

---

## Conventions (apply to every file)

### Naming
> Slugs only: ASCII, no spaces, no brackets. Dates in ISO format (YYYY-MM-DD) so they sort.
> File name = ID, globally unique. Project-scoped IDs carry the project acronym.
> Examples: `euroFMX`, `euroFMX_WP3`, `euroFMX_T3-2`, `euroFMX_D3-1`, `euroFMX_MS3`, `org_ENG`, `person_name-surname`, `asset_<slug>`, `study_<slug>`, `concept_<slug>`.
> Folder names use the project acronym, never the full name. Full names live in frontmatter.

### Frontmatter (mandatory)
```yaml
---
id: euroFMX_T3-2
type: task            # project | wp | task | deliverable | milestone | review | meeting | organization | person | asset | study | concept | synergy | note | todo
status: active        # draft | active | completed | deprecated
source: official      # official | meeting | study | personal
confidence: high      # high | medium | low (how well sourced)
confidentiality: SEN  # PU | SEN | enterprise-internal | personal
last_updated: 2026-01-01
tags: []              # only from the controlled vocabulary in /entities/concepts
relations:            # typed links, stored on ONE side only (reverse is derived)
  part_of: [euroFMX_WP3]
  depends_on: []
  produces: []
  uses: []
  owned_by: []
  related_to: []
---
```

### Deprecation
> No trash bin. Set `status: deprecated` and add a `superseded_by` relation. History is kept by version control.

---

## schema.md
> Instructions for the LLM, read first at every session.
> Contains: folder map, naming rules, frontmatter spec, controlled relation types, controlled tag vocabulary, and the three procedures: ingest (new source -> wiki update), query (how to answer and cite), lint (find orphans, broken links, stale files, contradictions).
> Rule: never write personal content into official files, never invent facts, cite the file ID or raw source for every claim.

## index.md
> Top-level, extra summarised map of the wiki: list of projects with one-line purpose and status, list of global entity folders, link to open cross-project synergies.

## log.md
> Append-only chronological log of wiki changes (date, file IDs touched, reason, source ingested).


## entities/
> Global, cross-project knowledge. One file per entity, never duplicated under a project.

### organizations/
> One file per organization (partner or not), named `org_<ACRONYM>.md`.
> Content: full name, type, country, general competences, history across projects.
> Project-specific information is NOT here, it lives in `projects/<ACRONYM>/participation/`.

### people/
> One file per person, named `person_name-surname.md`. Organization and project roles are relations.
> Structure:
> - Background and competences (if available and shared)
> - Responsibilities and expertise areas relevant to project work
> - Preferred working and contact channel (optional)
> Not included: psychological or personality profiles (GDPR profiling risk, unverifiable, and an LLM would over-generalize from them). Any note about working with a person goes in `notes/` with `confidentiality: personal`, after checking with the DPO.

### assets/
> One file per developed asset (software, dataset, model, methodology, demonstrator), named `asset_<slug>.md`. Assets often span several tasks, projects and partners, so they are global.
> Structure:
> - Asset description
> - Owner and involved partners (relations `owned_by`, `contributed_by`)
> - Projects and tasks where it is developed or used (relations `produced_in`, `used_in`)
> - Version history and updates
> - License and IPR notes
> - Reuse potential (feeds cross-project synergies)

### studies/
> One file per study, paper, article or technical report, named `study_<slug>.md`. Reused across tasks and projects.
> Structure: citation, link to the file in `raw/`, short summary in own words, key findings, limits, relations to concepts, tasks and assets that it supports.

### concepts/
> Hub nodes: technologies, standards, methods, application domains, named `concept_<slug>.md`.
> Defines the controlled tag vocabulary. Semantic synergies emerge here: two tasks pointing to the same concept are candidate synergies.
> Structure: definition, why it matters for the enterprise, list of projects, assets and studies that touch it (derived).

---

## projects/

### <ACRONYM>/
> One folder per European project. Folder name is the acronym.

#### <ACRONYM>.md
> Project index. Full name, call, grant number, dates, reporting periods, objectives, consortium overview, links to WPs, key milestones, current status.

#### participation/
> Project-specific facet of each partner and person (the global entity is in `entities/`).

##### <ACRONYM>_org_<PARTNER>.md
> Partner role in THIS project. A partner is an organization, not a person.
> Structure:
> - Fair summary of its role
> - Work Packages and Tasks with allocated resources (Person Months), as relations
> - Team: project managers and technical people (relations to `entities/people`)
> - Deliverables and assets it leads or contributes to

#### plan/
> What the project committed to do (comes from the DoA). Changes only through amendments.

##### wps/<ACRONYM>_WPX.md
> One file per Work Package.
> Structure:
> - Description and objective
> - Overview of tasks and deliverables (relations)
> - Dependencies with other WPs (relations `depends_on`)
> - Link to results, when available
> - Lead and contributing partners

##### tasks/<ACRONYM>_TX-Y.md
> One file per task. Folder is created only if a task needs supporting files.
> Structure:
> - Description, task leader, partners involved
> - Dependencies with other tasks (relations)
> - Assets produced or used (relations to `entities/assets`)
> - Studies relevant to the task (relations to `entities/studies`)
> - Progress log: dated entries with relevant updates, each with a source
> Synergies are not written here. They are derived from relations and concepts, see `/synergies`.

##### deliverables/<ACRONYM>_DX-Y.md
> One file per deliverable.
> Structure: title, type, dissemination level (PU/SEN), due month, lead partner, contributors, linked tasks and milestones, status, link to the submitted document in `raw/`.

##### milestones/<ACRONYM>_MSX.md
> One file per milestone. Objective, verification means, due month, linked tasks, partners, deliverables and assets, status.

#### governance/
> How the project is run and evaluated.

##### reviews/<ACRONYM>_review_<period>.md
> One file per review, named by reporting period (for example `RP1`) with the actual review date in frontmatter.
> Structure: partner contributions, review results and recommendations (updatable), follow-up actions. Links to partners, assets, tasks, deliverables, milestones.

##### meetings/YYYY-MM-DD_<title>_minutes.md
> Minutes of a meeting (internal, WP, consortium). Meeting scope in frontmatter.
> Structure: participants, topics, key points, solved issues, decisions, next steps. Links to tasks and partners. Action items become `todo` files.

#### risks/
> Risk register entries (one file per risk): description, probability, impact, mitigation, owner, linked tasks, status.

#### results/
> Outputs actually achieved, distinct from the plan.
> Contents: key exploitable results, dissemination outputs (papers, events), exploitation plans, KPI status. Each links to the assets, deliverables and tasks that produced it.

---

## synergies/
> Cross-project synergies as first-class nodes, named `synergy_<slug>.md`.
> Structure: the connected nodes (tasks, assets, concepts, organizations), the reason (shared asset, shared technology, shared partner, shared standard, shared use case), expected benefit, action needed, owner, status.
> Proposed by the LLM from relations and shared concepts, validated by a human before `status: active`.

---

## notes/
> Personal notes, interpretations and ideas. Always `source: personal`.
> Never cited as fact by the LLM without saying it is a personal note. Can be promoted to official files only after verification against a source.

## todos/
> One file per TODO, named `todo_<slug>.md`. No folder move on completion.
> Frontmatter holds `status` (open | in-progress | done | blocked), `start`, `due`, `owner`, and relations to any node (task, project, deliverable, meeting) or none for global TODOs.
> Boards (open, overdue, per project, per task) are generated views.