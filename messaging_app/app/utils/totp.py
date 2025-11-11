import pyotp
import qrcode
from io import BytesIO
import base64
import logging

logger = logging.getLogger(__name__)

class TOTPManager:
    """Manage Time-based One-Time Passwords (2FA)."""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp(secret: str) -> pyotp.TOTP:
        """Get TOTP object from secret."""
        return pyotp.TOTP(secret)
    
    @staticmethod
    def verify_token(secret: str, token: str) -> bool:
        """Verify a TOTP token."""
        totp = pyotp.TOTP(secret)
        # Allow 30-second window for clock skew
        return totp.verify(token)
    
    @staticmethod
    def generate_qr_code(secret: str, user_email: str, app_name: str = "Messaging App") -> str:
        """
        Generate QR code for TOTP setup.
        Returns base64-encoded QR code image.
        """
        try:
            totp = pyotp.TOTP(secret)
            uri = totp.provisioning_uri(
                name=user_email,
                issuer_name=app_name
            )
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(uri)
            qr.make(fit=True)
            
            # Convert to base64
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return img_base64
        except Exception as e:
            logger.error(f"QR code generation failed: {str(e)}")
            raise
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> list:
        """Generate backup codes for account recovery."""
        return [pyotp.random_base32(length=12) for _ in range(count)]
