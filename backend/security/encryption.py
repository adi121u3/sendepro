import os
import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_UNIQUE_RUNTIME_SECRET = secrets.token_hex(32)

def _get_fernet() -> Fernet:
    secret = os.getenv("CREDENTIAL_SECRET_KEY") or os.getenv("SECRET_KEY")
    if not secret:
        secret = _UNIQUE_RUNTIME_SECRET
        
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"email_sender_pro_secure_salt_v2",
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return Fernet(key)

def encrypt_credential(plaintext: str) -> str:
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")

def decrypt_credential(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        # Fallback if unencrypted legacy data exists
        return ciphertext

# Aliases for password imports
encrypt_password = encrypt_credential
decrypt_password = decrypt_credential
