"""Type stubs for craft_parts._rs."""

__version__: str

def get_craft_parts_version() -> str:
    """Get the package version, derived from `git describe` at compile time.

    :returns: A PEP 440 version string.
    """
