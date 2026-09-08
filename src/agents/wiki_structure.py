WIKI_STRUCTURE = """
# Index.md
> An updated index of the wiki, with relevant information to be sourced

# Partners
> Folder containing all project partners.

## Partner_Name [SHORT]
> Folder containing all information related to a specific partner.
> Partner_name is the full name. In brackets its acronym.

### Role.md
> A fair summary of the partner's role in the project.
> Contains links to the relevant Work Packages (WPs) with allocated resources (Person Months), Tasks, and its team (PMs / Techincal People).

### People
> Folder containing profiles of people belonging to the partner.

#### Name(s)_Surname(s).md
> Personal profile of a person, structured as follows:
> Background and Competences (if available)
> Psychological Profile (if available)
> Role in project (living part)

# WPs
> Folder containing all Work Packages (WPs) in the project.

## WPX
> Folder containing all information related to a specific Work Package.

### Summary.md
> Description of WP including its objective in the project
> Overview of its Tasks and Deliverables (links)
> Collaborative Dependencies with other WPs
> Link to results (when available)

### Task_X.Y
> Folder containing all information related to a specific Task. X.Y are names related to Task number. For instance T1.1 is Task_1.1

#### Summary.md
> Description of the Task, its Task Leader, and other Partners involved.
> Dependencies with other tasks
> Records of progresses and relevant updates concerning the Task.

#### Asset_name.md
> Documentation and references for a specific developed within the Task for the Partners. Structure as follows:
> Asset Description
> Involved partners
> Version updates and description

#### Studies.md
> References to relevant studies, research papers, articles, and other scientific or technical material related to the Task.

#### Synergies.md
> Documents connections and synergies between this Task and other Tasks.
> Contains links and a description of how the Tasks are related.

#### TODOs
> Folder containing ongoing TODO items related to the Task.

##### [date_start - date_end] TodoX.md
> File describing an ongoing TODO.
> The filename specifies the expected start and end dates.

#### Completed
> Folder containing TODOs that have been completed.

##### [date_start - date_end] TodoX.md
> A completed TODO moved from the TODOs folder after completion.

# Results
> Folder containing project results

## Milestones
> Folder containing Milestones

### Milestone_X.md
> File containing milestone objective, linked with tasks, partners and assets

## Reviews 
> Folder containing review meetings 

### Review_M_X.md
> Review meeting file, containing partner's contribution, updatable with review results and suggestions. Links with partners, assets, tasks, milestones.

## Meetings
> Folder containing internal project meeting

### [DD-MM-YYYY]_[TITLE]_minutes.md
> Minutes of the meeting, including Participants, discussed topics, key points, solved issues, next steps. Link with tasks and partners

"""