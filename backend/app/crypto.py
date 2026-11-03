"""Field-level encryption for stored document text (Fernet). Legacy plaintext rows still read fine."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from .config import settings

PREFIX = "enc1:"


def fernet() -> Fernet:
    key = settings.token_key
    if not key:  # stable dev key derived from the JWT secret; set TOKEN_ENCRYPTION_KEY in production
        key = base64.urlsafe_b64encode(hashlib.sha256(("tok:" + settings.jwt_secret).encode()).digest()).decode()
    return Fernet(key.encode())


class EncryptedText(TypeDecorator):
    """Text stored encrypted at rest; transparent to the rest of the code."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or value.startswith(PREFIX):
            return value
        return PREFIX + fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None or not value.startswith(PREFIX):
            return value
        try:
            return fernet().decrypt(value[len(PREFIX):].encode()).decode()
        except InvalidToken:
            raise ValueError("Stored text could not be decrypted; check the encryption key and data integrity") from None


class EncryptedJSON(EncryptedText):
    """Encrypted JSON with backward-compatible reads of legacy JSON text."""
    cache_ok = True

    def process_bind_param(self, value, dialect):
        import json
        if value is None:
            return None
        return super().process_bind_param(json.dumps(value, sort_keys=True), dialect)

    def process_result_value(self, value, dialect):
        import json
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        return json.loads(super().process_result_value(value, dialect))
