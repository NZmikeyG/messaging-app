import re
from typing import Any
import logging

logger = logging.getLogger(__name__)


class ContentSanitizer:
    """Sanitize user input to prevent XSS and injection attacks."""
    
    # HTML/Script tags to remove
    DANGEROUS_TAGS = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<embed[^>]*>',
        r'<object[^>]*>.*?</object>',
        r'on\w+\s*=\s*["\']?[^"\']*["\']?',  # Event handlers
    ]
    
    @staticmethod
    def sanitize_text(content: str, max_length: int = 5000) -> str:
        """
        Sanitize text content.
        
        Args:
            content: Text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
            
        Raises:
            ValueError: If content is invalid
        """
        if not isinstance(content, str):
            raise ValueError("Content must be a string")
        
        if len(content.strip()) == 0:
            raise ValueError("Content cannot be empty")
        
        if len(content) > max_length:
            raise ValueError(f"Content exceeds maximum length of {max_length}")
        
        # Remove dangerous patterns
        sanitized = content
        for pattern in ContentSanitizer.DANGEROUS_TAGS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        logger.debug(f"Text sanitized, original length: {len(content)}, sanitized length: {len(sanitized)}")
        return sanitized.strip()
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 255) -> str:
        """
        Sanitize filename.
        
        Args:
            filename: Original filename
            max_length: Maximum allowed length
            
        Returns:
            Sanitized filename
        """
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Remove path separators
        filename = filename.replace('/', '').replace('\\', '')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', '', filename)
        
        # Limit length
        if len(filename) > max_length:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            name = name[:max_length - len(ext) - 1]
            filename = f"{name}.{ext}" if ext else name
        
        logger.debug(f"Filename sanitized: {filename}")
        return filename
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """
        Validate and sanitize email.
        
        Args:
            email: Email address
            
        Returns:
            Sanitized email
            
        Raises:
            ValueError: If email is invalid
        """
        email = email.strip().lower()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")
        
        if len(email) > 255:
            raise ValueError("Email is too long")
        
        return email
    
    @staticmethod
    def sanitize_username(username: str) -> str:
        """
        Validate and sanitize username.
        
        Args:
            username: Username
            
        Returns:
            Sanitized username
            
        Raises:
            ValueError: If username is invalid
        """
        username = username.strip()
        
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        
        if len(username) > 50:
            raise ValueError("Username must be at most 50 characters")
        
        # Only alphanumeric, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValueError("Username can only contain letters, numbers, underscore, and hyphen")
        
        return username


# Singleton instance
sanitizer = ContentSanitizer()
