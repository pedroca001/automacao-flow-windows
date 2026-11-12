"""Keep Windows awake only while this exact authorized controller is alive."""
import ctypes
import json
from pathlib import Path
import time
import psutil

ROOT = Path(__file__).resolve().parent
launch = json.loads((ROOT / 'launcher-windows.json').read_text(encoding='utf-8'))
process = psutil.Process(launch['pid'])
created = process.create_time()
ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
try:
    while process.is_running() and process.create_time() == created:
        if (ROOT / 'PARAR').exists():
            break
        (ROOT / 'monitor-windows.json').write_text(json.dumps({'at': time.time(), 'controller_pid': process.pid,
            'controller_created_at': created, 'keep_awake': True}), encoding='utf-8')
        time.sleep(30)
finally:
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    (ROOT / 'monitor-windows.json').write_text(json.dumps({'at': time.time(), 'controller_pid': process.pid,
        'keep_awake': False}), encoding='utf-8')
