from backend.security.encryption import decrypt_password, encrypt_password

class CredentialManager:
    @staticmethod
    def get_secret(key: str) -> str:
        try:
            return decrypt_password(key)
        except Exception:
            return key
