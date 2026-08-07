"""Phase 3, Chunk 1: behavioral tests for get_user_profile read model.

These are unit tests against the model layer (no HTTP client). They drive the
contract for the new `get_user_profile(user_id: int) -> dict | None` function
in `models.py`:

  * returns exactly {"username", "email", "full_name", "address"} for a known
    user (seeded `demo` user, id=1),
  * returns None for an unknown user,
  * the `address` value is a non-empty string.

The function does not exist yet, so every test is expected to fail for the
*behavioral* reason captured by the assertion message -- the `getattr` guard
turns the absence into an AssertionError rather than an ImportError.
"""

import pytest

import models

pytestmark = pytest.mark.models


def test_profile_returns_contract_keys():
    fn = getattr(models, "get_user_profile", None)
    assert fn is not None, (
        "get_user_profile not implemented: profile key-set equals contract"
    )
    result = fn(1)
    assert set(result.keys()) == {
        "username",
        "email",
        "full_name",
        "address",
    }, "profile key-set equals contract"


def test_profile_returns_none_for_unknown_user():
    fn = getattr(models, "get_user_profile", None)
    assert fn is not None, (
        "get_user_profile not implemented: profile returns None for unknown user"
    )
    result = fn(99999)
    assert result is None, "profile returns None for unknown user"


def test_profile_address_non_empty():
    fn = getattr(models, "get_user_profile", None)
    assert fn is not None, (
        "get_user_profile not implemented: profile address is non-empty"
    )
    result = fn(1)
    assert result is not None, "profile address is non-empty"
    assert bool(result["address"]), "profile address is non-empty"
