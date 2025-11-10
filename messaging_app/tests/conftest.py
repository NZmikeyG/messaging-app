import sys
import os
from pathlib import Path

# Add parent directory to Python path so pytest can find 'app'
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db
from app.models.user import User


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a test database."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client."""
    def override_get_db():
        return db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    from app.utils.security import hash_password
    
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=hash_password("password123")  # Correct field name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user



@pytest.fixture
def auth_token(test_user):
    """Generate auth token for test user."""
    from app.utils.jwt_utils import create_access_token
    token = create_access_token(data={"sub": str(test_user.id)})
    return f"Bearer {token}"
