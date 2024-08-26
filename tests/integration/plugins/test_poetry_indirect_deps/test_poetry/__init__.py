def main() -> int:
    # httplib2 is an indirect dependency of launchpadlib
    # Ignore a gazillion typing issues here because we don't install httplib2
    # in the craft-parts environment.
    import httplib2  # type: ignore[import-untyped]

    print("Test succeeded!")
    return 0
