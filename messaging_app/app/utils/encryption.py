from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import os
import base64
import logging

logger = logging.getLogger(__name__)

class MessageEncryptor:
    """Encrypt/decrypt messages using AES-256-GCM."""
    
    def __init__(self, master_key: str):
        """Initialize with master encryption key."""
        # Derive a 256-bit key from the master key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'messaging_app_salt',
            iterations=100000,
            backend=default_backend()
        )
        self.key = kdf.derive(master_key.encode())
    
    def encrypt(self, plaintext: str) -> dict:
        """
        Encrypt plaintext message.
        Returns: {encrypted_content, iv, tag}
        """
        try:
            # Generate random IV (96 bits for GCM)
            iv = os.urandom(12)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Encrypt
            ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
            
            return {
                "encrypted_content": base64.b64encode(ciphertext).decode(),
                "iv": base64.b64encode(iv).decode(),
                "tag": base64.b64encode(encryptor.tag).decode()
            }
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt(self, encrypted_content: str, iv: str, tag: str) -> str:
        """
        Decrypt encrypted message.
        """
        try:
            # Decode from base64
            ciphertext = base64.b64decode(encrypted_content)
            iv_bytes = base64.b64decode(iv)
            tag_bytes = base64.b64decode(tag)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.GCM(iv_bytes, tag_bytes),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise
