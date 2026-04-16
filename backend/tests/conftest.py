from __future__ import annotations

import os
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import get_db
from app.main import app
from app.models import Base
from app.scripts.seed_data import seed_drills, seed_metric_types, seed_sports


def _resolve_test_database_url() -> str:
    configured_url = os.getenv(
        "TEST_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql://trainup_user:trainup_password@localhost:5432/trainup_db",
        ),
    )
    return configured_url.replace("@db:", "@localhost:")


@pytest.fixture
def db_session_factory() -> Generator[sessionmaker, None, None]:
    database_url = _resolve_test_database_url()
    schema_name = f"test_{uuid4().hex}"

    admin_engine = create_engine(database_url, poolclass=NullPool)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    engine = create_engine(
        database_url,
        poolclass=NullPool,
        connect_args={"options": f"-csearch_path={schema_name}"},
    )
    Base.metadata.create_all(bind=engine)

    testing_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )

    with testing_session_factory() as session:
        with session.begin():
            sports_by_name, _ = seed_sports(session)
            metrics_by_name, _ = seed_metric_types(session)
            seed_drills(session, sports_by_name, set(metrics_by_name.keys()))

    try:
        yield testing_session_factory
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        admin_engine.dispose()


@pytest.fixture
def client(db_session_factory: sessionmaker) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def db_session(db_session_factory: sessionmaker) -> Generator[Session, None, None]:
    session = db_session_factory()
    try:
        yield session
    finally:
        session.close()
