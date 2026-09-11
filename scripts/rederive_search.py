"""إعادة اشتقاق نسخ text_search/text_embedding من النص الأصلي بعد أي تغيير في قواعد التطبيع.

لا يلمس text_original إطلاقاً — المصدر الثابت.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.arabic import to_embedding_text, to_search_text
from shared.db.models import Issue
from shared.db.session import create_db_engine


def rederive(engine) -> int:
    updated = 0
    with Session(engine) as session:
        issues = session.scalars(select(Issue)).all()
        for issue in issues:
            new_search = to_search_text(issue.text_original)
            new_embedding = to_embedding_text(issue.text_original)
            if issue.text_search != new_search or issue.text_embedding != new_embedding:
                issue.text_search = new_search
                issue.text_embedding = new_embedding
                updated += 1
        session.commit()
    return updated


if __name__ == "__main__":
    from shared.db import fts

    engine = create_db_engine()
    count = rederive(engine)
    fts.rebuild_sqlite_fts(engine)
    print(f"rederived {count} issues; fts rebuilt")
