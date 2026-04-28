import hashlib
import os
import hmac

def hash_password(password: str) -> str:
    """
    Génère un hash sécurisé pour un mot de passe.
    Format stocké : salt_hex:hash_hex
    """
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        100_000
    )
    return salt.hex() + ":" + pwd_hash.hex()

def verify_password(password: str, stored: str) -> bool:
    """
    Vérifie qu'un mot de passe correspond au hash stocké.
    """
    try:
        salt_hex, hash_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        stored_hash = bytes.fromhex(hash_hex)

        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            100_000
        )

        return hmac.compare_digest(pwd_hash, stored_hash)
    except Exception:
        return False

