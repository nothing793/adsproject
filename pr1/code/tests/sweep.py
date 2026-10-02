#!/usr/bin/env python3
"""Print verified Shakespeare theta/tau tables, counting unique document IDs.

python code/tests/sweep.py             # show the last verified measurements
python code/tests/sweep.py --rebuild   # rebuild/recheck all experiments first
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    summary=root/'results/shakespeare_summary.json'
    if args.rebuild or not summary.exists():
        subprocess.run([sys.executable,Path(__file__).with_name('run_extended.py')],check=True)
    data=json.loads(summary.read_text(encoding='utf-8'))
    if data['failed']:
        raise RuntimeError('correctness tests failed; do not publish threshold tables')
    print('Verified measurements: N=%d, %d checks passed. Values count documents, not positions.\n'%
          (data['corpus']['documents'],data['passed']))
    print('| theta | stop words | indexed terms | positions | index KiB |')
    print('| --- | --- | --- | --- | --- |')
    for row in data['theta']:
        print('| %.1f | %d | %d | %d | %.2f |'%(row['theta'],row['stop_words'],row['indexed_stems'],row['positions'],row['index_bytes']/1024))
    print('\n| tau | caesar documents | antony documents | hamlet documents |')
    print('| --- | --- | --- | --- |')
    for tau in [None,.02,.1,.2,.3,.4,.5]:
        rows=[row for row in data['tau'] if row['tau']==tau]
        print('| %s | %s |'%('off' if tau is None else str(tau),' | '.join(
            'suppressed' if row['blocked'] else str(row['displayed_documents']) for row in rows)))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
