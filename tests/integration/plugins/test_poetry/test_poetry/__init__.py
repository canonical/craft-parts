import distro


def main() -> int:
    # Check that we installed the correct version of `distro`.
    assert distro.__version__ == "1.8.0"
    print("Test succeeded!")
    return 0
