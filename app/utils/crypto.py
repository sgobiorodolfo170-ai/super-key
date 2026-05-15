import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

_fernet_instance: Fernet | None = None
_fernet_lock: bool = False


def _get_fernet() -> Fernet:
    global _fernet_instance, _fernet_lock
    if _fernet_instance is not None:
        return _fernet_instance

    from app.config import settings

    key_material = settings.encryption_key.encode()
    if len(key_material) < 32:
        key_material = key_material.ljust(32, b"0")

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"super-key-salt", iterations=100000)
    derived_key = base64.urlsafe_b64encode(kdf.derive(key_material))
    _fernet_instance = Fernet(derived_key)
    _fernet_lock = True

    logger.info("Fernet encryption key derived and cached (PBKDF2-100000 iterations)")
    return _fernet_instance


def reset_key_cache():
    global _fernet_instance, _fernet_lock
    _fernet_instance = None
    _fernet_lock = False


def encrypt_api_key(plain_text: str) -> str:
    if not plain_text:
        return ""
    f = _get_fernet()
    return f.encrypt(plain_text.encode()).decode()


def decrypt_api_key(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    try:
        f = _get_fernet()
        decrypted = f.decrypt(cipher_text.encode()).decode()
        return decrypted
    except Exception:
        logger.warning("API key decryption failed, returning empty string", exc_info=True)
        return ""
