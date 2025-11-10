from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import os
import base64
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """Handle message encryption/decryption."""
    
    def __init__(self, master_key: str = None):
        if not master_key:
            master_key = os.getenv("ENCRYPTION_MASTER_KEY", "default-key")
        self.master_key = master_key
    
    def generate_key(self, salt: bytes = None) -> tuple:
        """Generate encryption key."""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        
        return key, salt
    
    def encrypt_message(self, content: str, salt: bytes = None) -> tuple:
        """Encrypt message content."""
        try:
            key, salt = self.generate_key(salt)
            cipher_suite = Fernet(key)
            encrypted = cipher_suite.encrypt(content.encode())
            
            logger.debug("Message encrypted successfully")
            return encrypted.decode(), base64.urlsafe_b64encode(salt).decode()
        
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_message(self, encrypted_content: str, salt: str) -> str:
        """Decrypt message content."""
        try:
            salt = base64.urlsafe_b64decode(salt.encode())
            key, _ = self.generate_key(salt)
            cipher_suite = Fernet(key)
            decrypted = cipher_suite.decrypt(encrypted_content.encode())
            
            logger.debug("Message decrypted successfully")
            return decrypted.decode()
        
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise


encryption_service = EncryptionService()
