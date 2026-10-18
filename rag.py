"""Runbook search (RAG): store runbook sections as embeddings in PostgreSQL + pgvector.

Run `python rag.py` to (re)build the index after changing anything in runbooks/.
"""

import os
from pathlib import Path

import truststore

# Trust the operating system's certificate list (needed where antivirus or a company
# proxy inspects HTTPS, e.g. for the one-time embedding model download).
truststore.inject_into_ssl()

import psycopg
from fastembed import TextEmbedding
from pgvector.psycopg import register_vector

RUNBOOK_DIR = Path(__file__).parent / "runbooks"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # small local model: 384 numbers per text
EMBEDDING_SIZE = 384

_model = None


def get_model() -> TextEmbedding:
    """Load the embedding model once (downloads it the first time)."""
    global _model
    if _model is None:
        _model = TextEmbedding(EMBEDDING_MODEL)
    return _model


def connect() -> psycopg.Connection:
    # The database address (including its password) comes from the environment, never from code.
    database_url = os.environ.get("RUNBOOKS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("RUNBOOKS_DATABASE_URL is not set. See 'How to run' in the README.")
    conn = psycopg.connect(database_url, autocommit=True)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def split_into_sections(text: str) -> list[str]:
    """Cut a runbook into its '## ' sections.

    Everything before the first '## ' (the title and owner line) is repeated at the
    top of every section, so each search result says which runbook it is and who owns it.
    """
    intro, *sections = text.split("\n## ")
    return [f"{intro.strip()}\n\n## {section.strip()}" for section in sections]


def index_runbooks() -> int:
    """Rebuild the runbook index from scratch. Returns the number of sections stored."""
    rows = []
    for path in sorted(RUNBOOK_DIR.glob("*.md")):
        for section in split_into_sections(path.read_text(encoding="utf-8")):
            rows.append((path.name, section))

    embeddings = list(get_model().passage_embed([content for _, content in rows]))

    with connect() as conn:
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS runbook_sections (
                    id serial PRIMARY KEY,
                    source text NOT NULL,
                    content text NOT NULL,
                    embedding vector({EMBEDDING_SIZE}) NOT NULL
                )"""
        )
        conn.execute("TRUNCATE runbook_sections")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO runbook_sections (source, content, embedding) VALUES (%s, %s, %s)",
                [(source, content, emb) for (source, content), emb in zip(rows, embeddings, strict=True)],
            )
    return len(rows)


def search(query: str, limit: int = 3) -> list[tuple[str, str, float]]:
    """Return the `limit` runbook sections closest in meaning to `query`, as (source, content, distance)."""
    query_embedding = next(iter(get_model().query_embed(query)))
    with connect() as conn:
        return conn.execute(
            """SELECT source, content, embedding <=> %s AS distance
               FROM runbook_sections
               ORDER BY distance
               LIMIT %s""",
            (query_embedding, limit),
        ).fetchall()


if __name__ == "__main__":
    count = index_runbooks()
    print(f"Indexed {count} runbook sections from {RUNBOOK_DIR}")
