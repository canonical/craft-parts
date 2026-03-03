import subprocess
from pathlib import Path

import pytest

from craft_parts.packages.deb import Ubuntu


def test_get_installed_packages_does_not_use_aptcache(monkeypatch):
    # If AptCache were used, this would fail the test immediately.
    class Boom:
        def __init__(self, *a, **kw):
            raise AssertionError("AptCache must not be used by get_installed_packages()")

    monkeypatch.setattr("craft_parts.packages.deb.AptCache", Boom, raising=False)

    # call the method: if it tries to instantiate AptCache -> 💥
    pkgs = Ubuntu.get_installed_packages()
    assert isinstance(pkgs, list)


def test_get_installed_packages_uses_dpkg_query_when_available(monkeypatch):
    def fake_check_output(cmd, text=False, stderr=None):  # noqa: ANN001
        assert cmd[:2] == ["dpkg-query", "-W"]
        return "bash\ncoreutils\nbash\n\n"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    pkgs = Ubuntu.get_installed_packages()
    assert isinstance(pkgs, list)
    assert all("=" not in p for p in pkgs)
    assert pkgs == ["bash", "coreutils"]


def test_get_installed_packages_fallback_parses_dpkg_status_and_flushes_last_stanza(monkeypatch, tmp_path):
    # Force dpkg-query path to fail
    def boom(*a, **kw):  # noqa: ANN001
        raise subprocess.CalledProcessError(1, "dpkg-query")

    monkeypatch.setattr(subprocess, "check_output", boom)

    # Create a fake /var/lib/dpkg/status with NO trailing blank line
    status = (
        "Package: aaa\n"
        "Status: install ok installed\n"
        "\n"
        "Package: zzz\n"
        "Status: install ok installed\n"
    )
    fake_status = tmp_path / "status"
    fake_status.write_text(status, encoding="utf-8")

    # Redirect Path('/var/lib/dpkg/status') to our temp file
    real_path = Path

    def fake_path(p):  # noqa: ANN001
        if p == "/var/lib/dpkg/status":
            return fake_status
        return real_path(p)

    monkeypatch.setattr("craft_parts.packages.deb.Path", fake_path)

    pkgs = Ubuntu.get_installed_packages()
    assert pkgs == ["aaa", "zzz"]
