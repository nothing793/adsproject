"""Small dependency-free process runner: raw logs, exit status, wall time, OS peak WS."""
import ctypes
import json
import os
import subprocess
import time
from pathlib import Path


if os.name == 'nt':
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ['PeakWorkingSetSize', 'WorkingSetSize',
            'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage']]
    get_memory = ctypes.WinDLL('psapi').GetProcessMemoryInfo
    get_memory.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    get_memory.restype = ctypes.c_int


def run_logged(command, cwd, prefix, timeout=300, expect=0):
    cwd, prefix = Path(cwd), Path(prefix)
    cwd.mkdir(parents=True, exist_ok=True)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    peak = 0
    timed_out = False
    with Path(str(prefix) + '.stdout.txt').open('wb') as out, Path(str(prefix) + '.stderr.txt').open('wb') as err:
        proc = subprocess.Popen([str(x) for x in command], cwd=cwd, stdout=out, stderr=err)
        while True:
            if os.name == 'nt':
                counters = Counters()
                counters.cb = ctypes.sizeof(counters)
                if get_memory(int(proc._handle), ctypes.byref(counters), counters.cb):
                    peak = max(peak, counters.PeakWorkingSetSize)
            status = proc.poll()
            if status is not None:
                break
            if time.perf_counter() - started > timeout:
                timed_out = True
                proc.kill()
                proc.wait()
                break
            time.sleep(0.01)
    result = dict(command=[str(x) for x in command], cwd=str(cwd), exit_code=proc.returncode,
                  seconds=round(time.perf_counter() - started, 6), peak_working_set_bytes=peak,
                  timeout=timed_out, memory_method='GetProcessMemoryInfo.PeakWorkingSetSize (10 ms polling)' if peak else 'unavailable')
    Path(str(prefix) + '.run.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if expect is not None and proc.returncode != expect:
        raise RuntimeError(f'{command[0]} exited {proc.returncode}; see {prefix}.stderr.txt')
    return result


def text(path):
    return Path(path).read_text(encoding='utf-8', errors='replace')
