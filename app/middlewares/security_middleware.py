from typing import Callable, Dict, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class ProdSecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, custom_headers: Optional[Dict[str, str]] = None):
        super().__init__(app)

        # Default security headers
        self.default_headers = {
            # Prevent clickjacking attacks
            "X-Frame-Options": "DENY",
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            # Strict transport security (HTTPS only)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            # Content Security Policy (restrictive default)
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions policy (disable sensitive features)
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=(), speaker=()",
            # Remove server information
            "Server": "FastAPI",
            # Cross-origin policies
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
        }

        # Merge with custom headers if provided
        if custom_headers:
            self.headers = {**self.default_headers, **custom_headers}
        else:
            self.headers = self.default_headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Process the request
        response = await call_next(request)

        # Add security headers to the response
        for header_name, header_value in self.headers.items():
            response.headers[header_name] = header_value

        return response


class DevSecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, custom_headers: Optional[Dict[str, str]] = None):
        super().__init__(app)

        # More permissive headers for development
        self.default_headers = {
            "X-Frame-Options": "SAMEORIGIN",  # Allow same-origin framing
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Server": "FastAPI",
            # More permissive CSP for development
            "Content-Security-Policy": "default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data: https: http:; font-src 'self' https: data:; connect-src 'self' ws: wss:;",
        }

        if custom_headers:
            self.headers = {**self.default_headers, **custom_headers}
        else:
            self.headers = self.default_headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        for header_name, header_value in self.headers.items():
            response.headers[header_name] = header_value

        return response
