import logging
import os
from textwrap import dedent

import pytest

from craft_parts import errors
from craft_parts.overlays import chroot
from craft_parts.overlays.errors import OverlayChrootExecutionError

test_logger = logging.getLogger("craft_parts.fake_module")


def call_in_chroot():
    test_logger.info("Info message from 'inside' chroot")
    test_logger.debug("Debug message from 'inside' chroot")
    test_logger.warning("Warning message from 'inside' chroot")


def error_in_chroot():
    call_in_chroot()
    raise errors.PartsError("Error from 'inside' chroot")


def complex_in_chroot():
    class C:
        def __str__(self):
            return "<local C>"

    complex_object = C()
    test_logger.info("Log message with local object: %s", complex_object)


@pytest.fixture
def mock_get_pid(mocker):
    """Mock for os.getpid() with a function that returns 0 for the first process
    that calls it, 1 for the second process, etc."""
    pids = {}
    original_get_pid = os.getpid

    def fake_get_pid():
        real_value = original_get_pid()
        return pids.setdefault(real_value, len(pids))

    mocker.patch.object(os, "getpid", new=fake_get_pid)


@pytest.fixture
def mock_chroot(mocker):
    """
    Fixture that mocks chroot-related calls that we don't want to execute as
    they possibly require root.

    Note that the os.chroot() call is mocked, but the multiprocessing
    infrastructure is in place - the callable passed to chroot.chroot() will be
    called in a different process with its own logging.
    """

    # Mock chroot-related calls that we don't want to execute as they possibly
    # require root
    mocker.patch.object(chroot, "_setup_chroot")
    mocker.patch.object(chroot, "_cleanup_chroot")
    mocker.patch.object(os, "chroot")


@pytest.fixture
def logfile(tmp_path, caplog):
    """Fixture that installs a log handler that writes to a file.

    We check the contents of the file instead of the `caplog` records because of
    the multiprocessing aspect of the chroot() call: we want to ensure that
    messages are only logged once, which is hard to do with memory-based log
    handlers. If the logfile has repeated lines, it means that both the "inner"
    chrooted call _and_ the scaffolding code logged it (incorrectly).
    """

    logpath = tmp_path / "log.txt"
    log = logging.getLogger()
    handler = logging.FileHandler(logpath)
    log.addHandler(handler)
    caplog.set_level(logging.DEBUG)

    yield logpath

    log.removeHandler(handler)


def get_expected_log(tmp_path, chroot_callable):
    return dedent(
        f"""\
        [pid=0] parent process
        [pid=0] set up chroot
        [pid=1] child process: target={chroot_callable}
        [pid=1] chroot to {tmp_path}
        Info message from 'inside' chroot
        Debug message from 'inside' chroot
        Warning message from 'inside' chroot
        [pid=0] clean up chroot
        """
    )


def test_chroot_logging_success(tmp_path, mock_get_pid, mock_chroot, logfile):
    """Test that messages logged by the callable passed to chroot() are captured."""
    chroot.chroot(tmp_path, call_in_chroot)
    assert logfile.read_text() == get_expected_log(tmp_path, call_in_chroot)


def test_chroot_logging_error(tmp_path, mock_get_pid, mock_chroot, logfile):
    """Test that messages logged by the callable passed to chroot() are captured,
    even if the call fails."""
    with pytest.raises(OverlayChrootExecutionError, match="Error from 'inside' chroot"):
        chroot.chroot(tmp_path, error_in_chroot)
    assert logfile.read_text() == get_expected_log(tmp_path, error_in_chroot)


def test_chroot_logging_complex_objects(tmp_path, mock_get_pid, mock_chroot, logfile):
    """Test that messages logged by the callable passed to chroot() are captured,
    even if they log objects that are not pickleable."""
    chroot.chroot(tmp_path, complex_in_chroot)
    assert "Log message with local object: <local C>" in logfile.read_text()
