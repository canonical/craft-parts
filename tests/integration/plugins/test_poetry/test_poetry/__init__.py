import distro  # type: ignore[import-not-found]


def main() -> int:
    # Check that we installed the correct version of `distro`.
    assert distro.__version__ == "1.8.0"  # pyright: ignore[reportPrivateImportUsage]
    print("Test succeeded!")
    return 0
