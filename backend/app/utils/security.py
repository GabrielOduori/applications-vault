import secrets
import base64
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_passphrase(passphrase: str) -> str:
    return ph.hash(passphrase)


def verify_passphrase(stored_hash: str, passphrase: str) -> bool:
    try:
        return ph.verify(stored_hash, passphrase)
    except VerifyMismatchError:
        return False


def generate_token() -> str:
    return secrets.token_hex(32)


def generate_recovery_key() -> str:
    raw = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(raw).decode("ascii")
