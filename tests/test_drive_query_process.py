"""Exercise real helper termination rather than substituting completed futures."""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from core import drive_usage
from gui.sidebar import drive_capacity


@pytest.fixture(autouse=True)
def query_lifecycle():
    drive_usage.start_drive_queries()
    yield
    drive_capacity.shutdown_capacity_executor()
    drive_usage.stop_drive_queries()


def sleeper_command(path, result_path):
    return [sys.executable, '-c', 'import time; time.sleep(60)']


def test_real_helper_matches_os_capacity(tmp_path):
    expected = drive_usage.read_drive_usage(str(tmp_path))
    actual = drive_usage.read_drive_usage_bounded(str(tmp_path))
    assert actual.total == expected.total
    assert 0 <= actual.used_percent <= 100
    assert not drive_usage._query_processes


def test_timed_out_helper_is_reaped(monkeypatch):
    monkeypatch.setattr(drive_usage, '_query_command', sleeper_command)
    monkeypatch.setattr(drive_usage, 'QUERY_TIMEOUT_SECONDS', .2)
    processes = []
    real_popen = subprocess.Popen

    def record(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(drive_usage.subprocess, 'Popen', record)
    with pytest.raises(OSError, match='timed out'):
        drive_usage.read_drive_usage_bounded('blocked')
    assert processes[0].poll() is not None
    assert not drive_usage._query_processes


def test_four_stalled_reads_release_slot_for_healthy_fifth(monkeypatch, tmp_path):
    real_command = drive_usage._query_command
    monkeypatch.setattr(drive_usage, '_query_command',
                        lambda path, result: sleeper_command(path, result) if path == 'blocked' else real_command(path, result))
    monkeypatch.setattr(drive_usage, 'QUERY_TIMEOUT_SECONDS', 1)
    with ThreadPoolExecutor(max_workers=4) as executor:
        stalled = [executor.submit(drive_usage.read_drive_usage_bounded, 'blocked') for _ in range(4)]
        healthy = executor.submit(drive_usage.read_drive_usage_bounded, str(tmp_path))
        assert healthy.result(timeout=6).total > 0
        for future in stalled:
            with pytest.raises(OSError, match='timed out'):
                future.result()
    assert not drive_usage._query_processes


def test_shutdown_kills_running_helpers_and_cancels_queued(monkeypatch):
    monkeypatch.setattr(drive_usage, '_query_command', sleeper_command)
    monkeypatch.setattr(drive_usage, 'QUERY_TIMEOUT_SECONDS', 60)
    executor = drive_capacity.capacity_executor()
    futures = [executor.submit(drive_usage.read_drive_usage_bounded, 'blocked') for _ in range(8)]
    deadline = time.monotonic() + 5
    while len(drive_usage._query_processes) != 4:
        assert time.monotonic() < deadline
        time.sleep(.01)
    processes = tuple(drive_usage._query_processes)
    started = time.monotonic()
    drive_capacity.shutdown_capacity_executor()
    assert time.monotonic() - started < 3
    assert all(process.poll() is not None for process in processes)
    assert all(future.done() for future in futures)
    assert not drive_usage._query_processes


def test_packaged_entrypoint_dispatches_before_qt(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / 'result.json'
    result = subprocess.run([sys.executable, str(root / 'src/main.py'),
                             '--drive-capacity-query', str(tmp_path), str(output)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert '"total"' in output.read_text(encoding='utf-8')


def test_helper_works_without_stdout(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'stdout', None)
    output = tmp_path / 'result.json'
    assert drive_usage.capacity_query_main(str(tmp_path), str(output)) == 0
    assert '"total"' in output.read_text(encoding='utf-8')
