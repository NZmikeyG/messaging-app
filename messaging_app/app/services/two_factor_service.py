import pyotp
import qrcode
from io import BytesIO
import base64
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class TwoFactorService:
    """Handle 2FA setup and verification."""
    
    @staticmethod
    def generate_secret(username: str) -> Tuple[str, str]:
        """Generate TOTP secret and QR code."""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=username,
            issuer_name='Messaging App'
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        qr_code_b64 = base64.b64encode(img_bytes.getvalue()).decode()
        
        logger.info(f"2FA secret generated for user {username}")
        return secret, qr_code_b64
    
    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """Verify TOTP code."""
        totp = pyotp.TOTP(secret)
        is_valid = totp.verify(code)
        logger.info(f"2FA verification: {'success' if is_valid else 'failed'}")
        return is_valid
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> list:
        """Generate backup codes."""
        codes = [pyotp.random_base32()[:8] for _ in range(count)]
        logger.info(f"Generated {count} backup codes")
        return codes
