<<<<<<< HEAD
import distro  # type: ignore[import-not-found]
=======
import distro
>>>>>>> 21870800 (test: require root for whiteout tests on Ubuntu 20.04 (#1748))


def main() -> int:
    # Check that we installed the correct version of `distro`.
    assert distro.__version__ == "1.8.0"  # pyright: ignore[reportPrivateImportUsage]
    print("Test succeeded!")
    return 0
