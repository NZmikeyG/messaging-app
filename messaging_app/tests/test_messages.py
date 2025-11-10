import pytest
from fastapi import status
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class TestDirectMessages:
    """Test direct messaging endpoints."""
    
    def test_send_dm(self, client, auth_token, test_user, db):
        """Test sending a direct message."""
        from app.models.user import User
        from app.utils.security import hash_password
        
        # Create another user - FIXED: password_hash instead of hashed_password
        other_user = User(
            email="other@example.com",
            username="otheruser",
            password_hash=hash_password("password123")
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)
        
        response = client.post(
            "/api/direct-messages/",
            json={
                "content": "Hello there!",
                "receiver_id": str(other_user.id)
            },
            headers={"Authorization": auth_token}
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"] == "Hello there!"
        logger.info("Test: DM sent successfully")
    
    def test_send_dm_to_self(self, client, auth_token, test_user):
        """Test sending DM to self (should fail)."""
        response = client.post(
            "/api/direct-messages/",
            json={
                "content": "Self message",
                "receiver_id": str(test_user.id)
            },
            headers={"Authorization": auth_token}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        logger.info("Test: Self DM rejected")
    
    def test_send_dm_to_nonexistent_user(self, client, auth_token):
        """Test sending DM to non-existent user."""
        response = client.post(
            "/api/direct-messages/",
            json={
                "content": "Message",
                "receiver_id": str(UUID('00000000-0000-0000-0000-000000000000'))
            },
            headers={"Authorization": auth_token}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        logger.info("Test: DM to non-existent user rejected")
    
    def test_get_dms(self, client, auth_token, test_user, db):
        """Test retrieving direct messages."""
        from app.models.user import User
        from app.models.direct_message import DirectMessage
        from app.utils.security import hash_password
        
        # FIXED: password_hash instead of hashed_password
        other_user = User(
            email="other2@example.com",
            username="otheruser2",
            password_hash=hash_password("password123")
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)
        
        # Create a test message
        dm = DirectMessage(
            content="Test message",
            sender_id=test_user.id,
            receiver_id=other_user.id
        )
        db.add(dm)
        db.commit()
        
        response = client.get(
            f"/api/direct-messages/?other_user_id={str(other_user.id)}",
            headers={"Authorization": auth_token}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        logger.info("Test: DMs retrieved successfully")


class TestMessageValidation:
    """Test message validation."""
    
    def test_empty_message(self, client, auth_token, test_user, db):
        """Test sending empty message."""
        from app.models.user import User
        from app.utils.security import hash_password
        
        # FIXED: password_hash instead of hashed_password
        other_user = User(
            email="other3@example.com",
            username="otheruser3",
            password_hash=hash_password("password123")
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)
        
        response = client.post(
            "/api/direct-messages/",
            json={
                "content": "",
                "receiver_id": str(other_user.id)
            },
            headers={"Authorization": auth_token}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        logger.info("Test: Empty message rejected")
    
    def test_message_too_long(self, client, auth_token, test_user, db):
        """Test sending message exceeding max length."""
        from app.models.user import User
        from app.utils.security import hash_password
        
        # FIXED: password_hash instead of hashed_password
        other_user = User(
            email="other4@example.com",
            username="otheruser4",
            password_hash=hash_password("password123")
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)
        
        long_content = "a" * 10000  # Exceed 5000 char limit
        response = client.post(
            "/api/direct-messages/",
            json={
                "content": long_content,
                "receiver_id": str(other_user.id)
            },
            headers={"Authorization": auth_token}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        logger.info("Test: Too-long message rejected")
