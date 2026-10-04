from typing import List, Dict, Any
from app.db import fetch_all, is_postgres

async def search_knowledge(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Full-text knowledge search across company policies, rubrics, and scheduling rules."""
    query = query.strip()
    if not query:
        return []

    if is_postgres():
        sql = """
            SELECT id, title, body,
                   ts_rank(tsv, plainto_tsquery('english', %s)) AS rank
            FROM knowledge_docs
            WHERE tsv @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
        """
        rows = await fetch_all(sql, (query, query, limit))
        if not rows:
            # Fallback to ILIKE if tsquery matched nothing
            like_sql = """
                SELECT id, title, body, 0.5 as rank
                FROM knowledge_docs
                WHERE title ILIKE %s OR body ILIKE %s
                LIMIT %s
            """
            rows = await fetch_all(like_sql, (f"%{query}%", f"%{query}%", limit))
        return rows
    else:
        # SQLite fallback: search title and body with words
        terms = [t.lower() for t in query.split() if len(t) > 2]
        if not terms:
            terms = [query.lower()]
        
        where_clauses = []
        params = []
        for term in terms:
            where_clauses.append("(LOWER(title) LIKE %s OR LOWER(body) LIKE %s)")
            params.extend([f"%{term}%", f"%{term}%"])
        
        sql = f"""
            SELECT id, title, body
            FROM knowledge_docs
            WHERE {' OR '.join(where_clauses)}
            LIMIT %s
        """
        params.append(limit)
        return await fetch_all(sql, tuple(params))
