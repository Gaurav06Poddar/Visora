from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional, List


def create_analyzer(db: Session, analyzer: schemas.AnalyzerCreate) -> models.Analyzer:
    db_analyzer = models.Analyzer(
        name=analyzer.name,
        stream_url=analyzer.stream_url,
        schema_fields=analyzer.schema_fields,
    )
    db.add(db_analyzer)
    db.commit()
    db.refresh(db_analyzer)
    return db_analyzer


def get_analyzer(db: Session, analyzer_id: int) -> Optional[models.Analyzer]:
    return db.query(models.Analyzer).filter(models.Analyzer.id == analyzer_id).first()


def get_all_analyzers(db: Session) -> List[models.Analyzer]:
    return db.query(models.Analyzer).all()


def update_analyzer(db: Session, analyzer_id: int, update: schemas.AnalyzerUpdate) -> Optional[models.Analyzer]:
    analyzer = get_analyzer(db, analyzer_id)
    if analyzer:
        analyzer.stream_url = update.stream_url
        analyzer.schema_fields = update.schema_fields
        db.commit()
        db.refresh(analyzer)
    return analyzer


def delete_analyzer(db: Session, analyzer_id: int) -> Optional[models.Analyzer]:
    analyzer = get_analyzer(db, analyzer_id)
    if analyzer:
        db.delete(analyzer)
        db.commit()
    return analyzer
