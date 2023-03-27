from app.database import Base, engine


def test_database_engine():
    assert str(engine.url) == "sqlite:///./iou_app.db"


def test_database_base():
    assert Base.metadata.tables.keys() == {'entries'}
