from __future__ import annotations

import base64

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import Settings
from app.services.github.auth import GitHubAppAuth, GitHubConfigError


def _make_keypair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def test_create_app_jwt_is_valid_and_signed():
    private_pem, public_pem = _make_keypair()
    settings = Settings(
        _env_file=None,
        github_app_id="123456",
        github_app_private_key_base64=base64.b64encode(private_pem.encode()).decode(),
    )
    auth = GitHubAppAuth(settings)

    token = auth.create_app_jwt(now=1_000_000)
    decoded = jwt.decode(
        token, public_pem, algorithms=["RS256"], options={"verify_exp": False}
    )

    assert decoded["iss"] == "123456"
    assert decoded["iat"] == 1_000_000 - 60
    assert decoded["exp"] == 1_000_000 + 9 * 60


def test_private_key_accepts_raw_pem_in_base64_var():
    # A PEM pasted directly into the *_BASE64 var (a common mistake) is used as-is.
    private_pem, public_pem = _make_keypair()
    settings = Settings(
        _env_file=None,
        github_app_id="123456",
        github_app_private_key_base64=private_pem,
    )
    auth = GitHubAppAuth(settings)
    token = auth.create_app_jwt(now=1_000_000)
    assert jwt.decode(token, public_pem, algorithms=["RS256"], options={"verify_exp": False})


def test_private_key_tolerates_whitespace_and_lost_padding():
    # Env editors can inject newlines and drop trailing "=" padding.
    private_pem, public_pem = _make_keypair()
    b64 = base64.b64encode(private_pem.encode()).decode()
    mangled = "\n".join(b64[i : i + 64] for i in range(0, len(b64), 64)).rstrip("=")
    settings = Settings(
        _env_file=None,
        github_app_id="123456",
        github_app_private_key_base64=mangled,
    )
    auth = GitHubAppAuth(settings)
    token = auth.create_app_jwt(now=1_000_000)
    assert jwt.decode(token, public_pem, algorithms=["RS256"], options={"verify_exp": False})


def test_corrupt_base64_private_key_raises_clear_error():
    settings = Settings(
        _env_file=None,
        github_app_id="123456",
        github_app_private_key_base64="not-a-real-key-@@@",
    )
    auth = GitHubAppAuth(settings)
    with pytest.raises(GitHubConfigError, match="GITHUB_APP_PRIVATE_KEY_BASE64"):
        auth.create_app_jwt()


def test_missing_private_key_raises():
    # Point the key path at a definitely-absent file so the test is hermetic
    # regardless of any real key that may exist at the default path on disk.
    settings = Settings(
        _env_file=None,
        github_app_id="123456",
        github_app_private_key_path="/nonexistent/variorum-no-such-key.pem",
    )
    auth = GitHubAppAuth(settings)
    with pytest.raises(GitHubConfigError):
        auth.create_app_jwt()


def test_missing_app_id_raises():
    private_pem, _ = _make_keypair()
    settings = Settings(
        _env_file=None,
        github_app_private_key_base64=base64.b64encode(private_pem.encode()).decode(),
    )
    auth = GitHubAppAuth(settings)
    with pytest.raises(GitHubConfigError):
        auth.create_app_jwt()
