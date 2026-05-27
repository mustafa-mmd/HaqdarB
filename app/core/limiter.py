# app/core/limiter.py
"""
HaqDar AI — Rate Limiting Configuration
Uses slowapi for request rate limiting.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
