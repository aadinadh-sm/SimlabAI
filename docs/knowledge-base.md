# SIMLAB AI: Knowledge Base & RAG Architecture

## Source Authority
The authoritative source for all experiment knowledge is:
`23EEP20B - SIMULATION LAB MANUAL` (Mar Baselios College of Engineering and Technology, affiliated to APJ Abdul Kalam Technological University).

## SQLite FTS5 Schema
The knowledge base is housed entirely in a local SQLite 3 database (`knowledge/manual_db.sqlite`) with Full-Text Search 5 (FTS5).

```sql
CREATE TABLE experiments (
    exp_number INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    software TEXT NOT NULL,
    aim TEXT NOT NULL,
    procedure TEXT NOT NULL,
    result TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    tags TEXT NOT NULL,
    code_sample TEXT,
    diagram_images TEXT NOT NULL
);

CREATE TABLE manual_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exp_number INTEGER NOT NULL,
    section TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    content TEXT NOT NULL,
    source_type TEXT NOT NULL,
    tags TEXT,
    FOREIGN KEY(exp_number) REFERENCES experiments(exp_number)
);

CREATE VIRTUAL TABLE manual_chunks_fts USING fts5(
    section,
    content,
    tags,
    content='manual_chunks',
    content_rowid='id'
);
```

## Grounding & Citations
Every query generates a standardized citation:
`Source: Simulation Lab Manual · Experiment <X> · <Section> · Page <Y>`
Internal SQLite primary keys are never surfaced to the student.
