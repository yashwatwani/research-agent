Good call — dedicated file, easier to find. Create POSTGRES.md in the project root:
markdown# Postgres & pgvector Reference

Quick reference for everything we use in this project.

---

## Connecting

```bash
# connect to default postgres db
psql postgres

# connect directly to our project db
psql postgresql://yash.watwani@localhost:5432/research_agent
```

---

## Navigation inside psql

```sql
\l                  -- list all databases on this server
\c research_agent   -- switch to a specific database
\dt                 -- list all tables in current database
\d chunks           -- describe a table (columns, types, indexes)
\di                 -- list all indexes
\x                  -- toggle expanded display (easier to read wide rows)
\timing             -- show how long each query takes
\e                  -- open query in your text editor
\q                  -- quit psql
```

---

## Viewing data

```sql
-- see all rows
SELECT * FROM chunks;

-- count rows
SELECT COUNT(*) FROM chunks;

-- preview content without loading full text
SELECT id, source_title, LEFT(content, 100) AS preview, created_at
FROM chunks;

-- preview the embedding vector
SELECT id, LEFT(embedding::text, 80) AS embedding_preview
FROM chunks;

-- latest rows first
SELECT * FROM chunks ORDER BY created_at DESC LIMIT 5;

-- rows above a similarity threshold
SELECT content, 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM chunks
ORDER BY similarity DESC
LIMIT 5;
```

---

## Editing data

```sql
-- delete one specific row
DELETE FROM chunks WHERE id = 1;

-- delete all rows but keep the table
DELETE FROM chunks;

-- remove duplicate rows, keep the earliest
DELETE FROM chunks WHERE id NOT IN (
    SELECT MIN(id) FROM chunks GROUP BY content
);

-- delete the table entirely
DROP TABLE chunks;

-- delete a specific index
DROP INDEX IF EXISTS chunks_embedding_idx;
```

---

## Setup commands (run once)

```sql
-- create the database
CREATE DATABASE research_agent;

-- switch to it
\c research_agent

-- enable pgvector extension
CREATE EXTENSION vector;
```

---

## Our chunks table

```sql
CREATE TABLE IF NOT EXISTS chunks (
    id          SERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    embedding   vector(1536),
    source_url  TEXT,
    source_title TEXT,
    metadata    JSONB,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

Column by column:

| Column | Type | What it stores |
|--------|------|----------------|
| id | SERIAL | auto incrementing row ID |
| content | TEXT | the raw chunk text |
| embedding | vector(1536) | 1536 floats encoding the meaning of the chunk |
| source_url | TEXT | where the chunk came from |
| source_title | TEXT | human readable source name |
| metadata | JSONB | any extra info as JSON |
| created_at | TIMESTAMP | when the row was inserted |

---

## pgvector operators

```sql
<=>   -- cosine distance (lower = more similar)
   -- euclidean distance
   -- negative inner product
```

We use `<=>` (cosine distance) throughout this project.

Similarity score = `1 - (embedding <=> query_embedding)`
Score of 1.0 = identical meaning. Score of 0.0 = completely unrelated.

---

## Indexes

```sql
-- ivfflat index for approximate nearest neighbour search
-- only add when you have 1000+ rows
CREATE INDEX chunks_embedding_idx
ON chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- drop it
DROP INDEX IF EXISTS chunks_embedding_idx;
```

Why ivfflat needs data: it works by dividing vectors into clusters.
With fewer than ~100 rows it has nothing to cluster and returns nothing.
We removed it early on for this reason. Add it back in production.

---

## Useful diagnostics

```sql
-- check pgvector is installed
SELECT * FROM pg_extension WHERE extname = 'vector';

-- check table size
SELECT pg_size_pretty(pg_total_relation_size('chunks'));

-- check index is being used
EXPLAIN SELECT content FROM chunks
ORDER BY embedding <=> '[0.1, 0.2]'::vector LIMIT 5;
```

---

## Common errors and fixes

| Error | Cause | Fix |
|-------|-------|-----|
| extension "vector" is not available | pgvector not copied to Postgres extension dir | copy files manually (see README) |
| operator does not exist: vector <=> vector | pgvector not enabled in this db | run CREATE EXTENSION vector |
| column "embedding" is of type vector but expression is of type text | missing ::vector cast | add ::vector to the query parameter |
| ivfflat index returns 0 results | not enough rows to cluster | drop the index, use plain scan |
