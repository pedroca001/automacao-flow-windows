"""Small platform boundary shared by the macro and the controllers."""
import errno
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

WINDOWS = sys.platform == 'win32'
BASE = Path(__file__).resolve().parents[1]

if not WINDOWS:
    import fcntl as locks
else:
    import msvcrt

    class locks:
        LOCK_EX, LOCK_NB, LOCK_UN = 2, 4, 8

        @staticmethod
        def flock(file, operation):
            fd = file if isinstance(file, int) else file.fileno()
            position = os.lseek(fd, 0, os.SEEK_CUR)
            try:
                while True:
                    os.lseek(fd, 0, os.SEEK_SET)
                    try:
                        msvcrt.locking(fd, msvcrt.LK_UNLCK if operation & locks.LOCK_UN else msvcrt.LK_NBLCK, 1)
                        return
                    except OSError as error:
                        if operation & locks.LOCK_UN or error.errno not in (errno.EACCES, errno.EDEADLK, errno.EAGAIN):
                            raise
                        if operation & locks.LOCK_NB:
                            raise BlockingIOError(errno.EAGAIN, 'Outra automação mantém a trava.') from error
                        time.sleep(.1)
            finally:
                os.lseek(fd, position, os.SEEK_SET)


def native_command():
    if WINDOWS:
        return [str(BASE / '.venv/Scripts/python.exe'), '-u', str(BASE / 'scripts/flow_macro_windows.py')]
    return [str(Path.home() / 'Library/Application Support/Flow Macro/Macro Flow.app/Contents/MacOS/flow-macro')]


def process_options(detached=False):
    if WINDOWS:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP
        flags |= subprocess.DETACHED_PROCESS if detached else subprocess.CREATE_NO_WINDOW
        return {'creationflags': flags}
    return {'start_new_session': True}


def terminate_tree(pid, force=False):
    if WINDOWS:
        import psutil
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in reversed(children):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            parent.kill()
            psutil.wait_procs([*children, parent], timeout=5)
        except psutil.NoSuchProcess:
            pass
    else:
        os.killpg(pid, signal.SIGKILL if force else signal.SIGTERM)


def macro_processes(binary, prompt=None, pid=None):
    if not WINDOWS:
        command = ['ps', '-p', str(pid), '-o', 'pid=,command='] if pid is not None else ['ps', '-axo', 'pid=,command=']
        output = subprocess.run(command, capture_output=True, text=True, timeout=10).stdout
        result = []
        for line in output.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and parts[1].startswith(str(binary) + ' ') and (prompt is None or str(prompt) in parts[1]):
                result.append(int(parts[0]))
        return result
    import psutil
    result = []
    for process in psutil.process_iter(['pid', 'cmdline']):
        try:
            args = process.info['cmdline'] or []
            if (pid is None or process.pid == pid) and str(binary) in args and (prompt is None or str(prompt) in args):
                result.append(process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return result


def stop_signals():
    return tuple(getattr(signal, name) for name in ('SIGTERM', 'SIGINT', 'SIGHUP') if hasattr(signal, name))


def filter_path(path):
    """Quote a filename for FFmpeg's filter parser, including Windows drive colons."""
    value = str(path).replace('\\', '/')
    return "'" + value.replace(':', '\\:').replace("'", "'\\''") + "'"
