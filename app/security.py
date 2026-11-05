"""Password policy checker, used by the security checks of the project."""

import string

# fmt: off
COMMON_PASSWORDS = {
    "password", "password1", "password123", "123456", "12345678", "123456789",
    "qwerty", "qwerty123", "admin", "admin123", "letmein", "welcome", "welcome1",
    "iloveyou", "monkey", "dragon", "football", "abc123", "111111", "postgres",
    "mysql", "root", "changeme", "secret", "passw0rd", "p@ssw0rd", "narxoz",
}
# fmt: on


def check_password(password: str, min_length: int = 12) -> dict:
    rules = {
        "min_length": len(password) >= min_length,
        "has_upper": any(c.isupper() for c in password),
        "has_lower": any(c.islower() for c in password),
        "has_digit": any(c.isdigit() for c in password),
        "has_symbol": any(c in string.punctuation for c in password),
        "not_common": password.lower() not in COMMON_PASSWORDS,
    }
    return {"ok": all(rules.values()), "min_length": min_length, "rules": rules}
