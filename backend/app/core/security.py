"""
Security utilities for Greppa

Provides:
1. Rate limiting middleware
2. Input validation and sanitization
3. API key validation
4. Request context tracking
"""
import re
import hashlib
import logging
from typing import Optional, Callable
from functools import wraps
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger("greppa.security")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


def validate_api_key(api_key: Optional[str]) -> bool:
    """
    Validates an API key format.
    For Gemini keys, should start with 'AIza' and be 39 chars.
    """
    if not api_key:
        return False
    
    # Basic format validation
    if len(api_key) < 20:
        return False
    
    # Check for obviously fake or test keys
    fake_patterns = [
        r'^(test|demo|fake|invalid|placeholder)',
        r'(your[-_]?key|api[-_]?key[-_]?here)',
    ]
    
    for pattern in fake_patterns:
        if re.search(pattern, api_key, re.IGNORECASE):
            logger.warning(f"Rejected suspicious API key pattern: {pattern}")
            return False
    
    return True


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitizes user input to prevent injection attacks.
    
    Rules:
    1. Limit length
    2. Remove null bytes
    3. Normalize whitespace
    4. No control characters except newlines and tabs
    """
    if not text:
        return ""
    
    # Truncate
    text = text[:max_length]
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Remove other control characters except \n, \r, \t
    sanitized = []
    for char in text:
        code = ord(char)
        if code >= 32 or char in '\n\r\t':
            sanitized.append(char)
    
    return ''.join(sanitized)


def sanitize_file_path(path: str) -> str:
    """
    Sanitizes file paths to prevent directory traversal attacks.
    
    Rules:
    1. No parent directory references (..)
    2. No absolute paths
    3. No null bytes
    4. Only alphanumeric, dash, underscore, slash, dot
    """
    if not path:
        return ""
    
    # Remove null bytes
    path = path.replace('\x00', '')
    
    # Normalize path separators
    path = path.replace('\\', '/')
    
    # Remove leading slash (no absolute paths)
    path = path.lstrip('/')
    
    # Check for directory traversal
    if '..' in path:
        logger.warning(f"Rejected path with parent directory reference: {path}")
        raise ValueError("Path contains invalid parent directory reference")
    
    # Validate characters
    if not re.match(r'^[a-zA-Z0-9/_.\-]+$', path):
        logger.warning(f"Rejected path with invalid characters: {path}")
        raise ValueError("Path contains invalid characters")
    
    return path


def validate_repo_url(url: str) -> bool:
    """
    Validates repository URL to prevent SSRF attacks.
    
    Only allows:
    - GitHub URLs (https://github.com/...)
    - GitLab URLs (https://gitlab.com/...)
    - Bitbucket URLs (https://bitbucket.org/...)
    - Local file paths (for development)
    """
    if not url:
        return False
    
    # Allow local paths
    if not url.startswith('http'):
        return True
    
    # Only allow HTTPS (except localhost for development)
    if not url.startswith('https://') and 'localhost' not in url:
        logger.warning(f"Rejected non-HTTPS URL: {url}")
        return False
    
    # Whitelist of allowed domains
    allowed_domains = [
        'github.com',
        'gitlab.com',
        'bitbucket.org',
        'localhost',
        '127.0.0.1'
    ]
    
    for domain in allowed_domains:
        if domain in url:
            return True
    
    logger.warning(f"Rejected URL from non-whitelisted domain: {url}")
    return False


def check_content_for_prompt_injection(content: str, max_check_length: int = 2000) -> bool:
    """
    Checks if content contains potential prompt injection attempts.
    
    Returns True if suspicious patterns detected.
    """
    if not content:
        return False
    
    # Only check first portion to avoid performance issues
    check_content = content[:max_check_length].lower()
    
    # Suspicious patterns that might be prompt injection
    suspicious_patterns = [
        r'ignore\s+(previous|above|prior)\s+(instructions|prompt|rules)',
        r'you\s+are\s+now\s+a\s+(different|new)',
        r'disregard\s+(previous|above|all)',
        r'system\s*:\s*you\s+are',
        r'forget\s+(everything|all\s+previous)',
        r'\[system\]',
        r'<\|im_start\|>',
        r'###\s*instruction',
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, check_content, re.IGNORECASE):
            logger.warning(f"Potential prompt injection detected: pattern '{pattern}'")
            return True
    
    return False


class RateLimitConfig:
    """Rate limit configurations for different endpoint types"""
    
    # General API endpoints
    DEFAULT = "60/minute"
    
    # Search and retrieval (more expensive)
    SEARCH = "30/minute"
    
    # LLM-heavy operations (tour generation, issue matching)
    LLM_OPERATIONS = "10/minute"
    
    # Repository ingestion (very expensive)
    INGESTION = "5/hour"
    
    # Authentication attempts
    AUTH = "10/minute"


def require_valid_api_key(func: Callable) -> Callable:
    """
    Decorator to require a valid API key in headers.
    Checks X-Gemini-API-Key header.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request from kwargs
        request = kwargs.get('request')
        api_key = None
        
        if request:
            api_key = request.headers.get('X-Gemini-API-Key')
        
        # For development, allow without key if GEMINI_API_KEY is in env
        import os
        if not api_key:
            api_key = os.environ.get('GEMINI_API_KEY')
        
        if not api_key or not validate_api_key(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid API key required. Provide X-Gemini-API-Key header."
            )
        
        return await func(*args, **kwargs)
    
    return wrapper


async def security_headers_middleware(request: Request, call_next):
    """
    Adds security headers to all responses.
    """
    response = await call_next(request)
    
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response


class RequestLogger:
    """Logs all requests for security auditing"""
    
    @staticmethod
    async def log_request(request: Request, call_next):
        """
        Logs request details for security auditing.
        """
        client_ip = get_remote_address(request)
        method = request.method
        path = request.url.path
        
        # Log request
        logger.info(f"Request: {method} {path} from {client_ip}")
        
        # Check for suspicious patterns in path
        if '..' in path or 'system' in path.lower():
            logger.warning(f"Suspicious path detected: {path} from {client_ip}")
        
        response = await call_next(request)
        
        # Log response status
        logger.info(f"Response: {method} {path} -> {response.status_code}")
        
        return response


def get_client_identifier(request: Request) -> str:
    """
    Gets a unique identifier for rate limiting.
    Uses IP address and optional API key.
    """
    ip = get_remote_address(request)
    api_key = request.headers.get('X-Gemini-API-Key', '')
    
    # Hash API key if present to avoid logging sensitive data
    if api_key:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f"{ip}:{key_hash}"
    
    return ip


# Custom rate limit exceeded handler
def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    """
    logger.warning(f"Rate limit exceeded for {get_remote_address(request)}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down and try again later.",
            "detail": str(exc)
        }
    )
