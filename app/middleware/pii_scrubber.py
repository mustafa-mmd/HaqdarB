# app/middleware/pii_scrubber.py
"""
HaqDar AI — PII Scrubbing Middleware
Regex-based utility to redact sensitive personally identifiable information (PII) 
such as Pakistani CNICs, phone numbers, email addresses, and home/street addresses.
"""
import re

# Regex for CNIC: e.g., 35201-1234567-1
CNIC_PATTERN = re.compile(r'\b\d{5}-\d{7}-\d\b')

# Regex for Pakistani mobile and landline numbers
# e.g., +92-300-1234567, 03001234567, +923001234567, 042-35876543, 04235876543
PHONE_PATTERN = re.compile(
    r'\b(?:\+?92[-\s]?)?(?:0?3\d{2}|0?[2456789]\d{1})[-\s]?\d{7,8}\b'
)

# Regex for common street/home addresses in Pakistan
# Matches "House/H/Flat/Plot No. 123", "Street/St. 4", "Sector/Block/Phase X", "Mohallah X"
ADDRESS_PATTERN = re.compile(
    r'\b(?:House|H|Flat|Plot|St|Street|Sector|Block|Phase|Mohallah)\s+(?:No\.?\s*)?\w+(?:\s+(?:No\.?\s*)?\w+)*(?:\s*(?:Street|St|Sector|Block|Phase|Mohallah)\s+\w+)*',
    re.IGNORECASE
)

# Email address pattern just in case
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')


def scrub_pii(text: str) -> str:
    """
    Scrub PII from text before passing to third-party LLMs or saving to logs.
    """
    if not text:
        return text

    # Redact CNIC
    text = CNIC_PATTERN.sub("[CNIC_REDACTED]", text)

    # Redact Email
    text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)

    # Redact Phone numbers
    text = PHONE_PATTERN.sub("[PHONE_REDACTED]", text)

    # Redact Addresses
    text = ADDRESS_PATTERN.sub("[ADDRESS_REDACTED]", text)

    return text
