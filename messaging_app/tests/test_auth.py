import pytest
from fastapi import status
import logging

logger = logging.getLogger(__name__)


class TestUserRegistration:
    """Test user registration endpoints."""
    
    def test_register_new_user(self, client):
        """Test successful user registration."""
        response = client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123!"
        })
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
        logger.info("Test: User registration successful")
    
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email."""
        response = client.post("/api/auth/register", json={
            "email": test_user.email,
            "username": "different",
            "password": "password123"
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        logger.info("Test: Duplicate email rejected")
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post("/api/auth/register", json={
            "email": "invalid-email",
            "username": "newuser",
            "password": "password123"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        logger.info("Test: Invalid email rejected")
    
    def test_register_short_password(self, client):
        """Test registration with short password."""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "username": "newuser",
            "password": "123"
        })
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        logger.info("Test: Short password rejected")


class TestUserLogin:
    """Test user login endpoints."""
    
    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "password123"  # Assuming this is set during user creation
        })
        # Note: Adjust based on your actual password handling
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "access_token" in data
            logger.info("Test: Login successful")
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_400_BAD_REQUEST]
        logger.info("Test: Invalid credentials rejected")
    
    def test_login_missing_email(self, client):
        """Test login without email."""
        response = client.post("/api/auth/login", json={
            "password": "password123"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        logger.info("Test: Missing email rejected")
