#!/usr/bin/env python3
"""Measure original backend limits and a separate disk proof of concept."""
import csv
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from lab_support import run_logged, text
from brute_check import parse_index

ROOT=Path(__file__).resolve().parents[2]
RESULTS=ROOT/'results'
LOGS=RESULTS/'logs'
BIN=ROOT/'bin'


def main():
    run_logged(['gcc','-std=c99','-O2','-Wall','-Wextra','-Wpedantic',ROOT/'code/tests/bonus_probe.c',
                '-o',BIN/'bonus_probe.exe'],ROOT,LOGS/'build_bonus_probe')
    assert not text(LOGS/'build_bonus_probe.stderr.txt').strip()
    run_logged([BIN/'bonus_probe.exe','types'],ROOT,LOGS/'bonus_types')
    types=json.loads(text(LOGS/'bonus_types.stdout.txt'))
    rows=[]
    for mode,counts in [('common',[4000,8000,16000,32000,64000]),('vocabulary',[10000,100000,1000000]),('docs',[500000])]:
        for count in counts:
            folder=RESULTS/f'bonus/{mode}_{count}'
            label=f'bonus_{mode}_{count}'
            if '--reuse-indexes' in sys.argv and (folder/'index.bin').exists():
                timing=json.loads(text(LOGS/(label+'.run.json')))
            else:
                timing=run_logged([BIN/'bonus_probe.exe',mode,count],folder,LOGS/label,timeout=180)
            measurement=json.loads(text(LOGS/(label+'.stdout.txt')))
            assert measurement['n']==count
            loaded=run_logged([BIN/'query.exe','term0000000000x' if mode=='vocabulary' else 'common'],folder,LOGS/(label+'_query'),timeout=180)
            output=text(folder/'output.txt')
            if mode=='vocabulary':
                assert 'df=1/' in output and 'Doc ID: 0, Position: 0' in output
                last=count-1
                last_loaded=run_logged([BIN/'query.exe',f'term{last:010d}x'],folder,LOGS/(label+'_last_query'),timeout=180)
                last_output=text(folder/'output.txt')
                assert f'Doc ID: {last % measurement["documents"]}, Position: {last // measurement["documents"]}' in last_output
                assert 'df=1/' in last_output
            elif mode=='common':
                got=[int(line.split('Position: ')[1]) for line in output.splitlines() if line.startswith('Doc ID:')]
                assert got==list(range(count))
            else:
                blob=(folder/'index.bin').read_bytes()
                assert len(blob)==64+4*count and int.from_bytes(blob[16:24],'little')==count
                assert 'Not found:' in output
            rows.append(dict(**measurement,seconds=timing['seconds'],peak_working_set_bytes=timing['peak_working_set_bytes'],
                index_bytes=(folder/'index.bin').stat().st_size,query_seconds=loaded['seconds'],
                query_peak_working_set_bytes=loaded['peak_working_set_bytes'],verified=True))
            print('PASS:',mode,count,rows[-1],flush=True)
    # Validate a real OS invocation failure; paths need not exist because CreateProcess
    # rejects the argument string before the C program is entered.
    command=[str(BIN/'index_gen.exe')]+[f'doc_{i:06d}.txt' for i in range(500000)]
    command_chars=len(subprocess.list2cmdline(command))
    cli_result=dict(requested_paths=500000,physical_files_created=0,command_chars=command_chars)
    if os.name=='nt':
        try:
            subprocess.run(command,cwd=ROOT,capture_output=True,check=False)
            cli_result.update(rejected=False)
        except OSError as exc:
            cli_result.update(rejected=True,winerror=exc.winerror,error=str(exc))
        assert cli_result['rejected']
    (LOGS/'bonus_cli_limit.json').write_text(json.dumps(cli_result,ensure_ascii=False,indent=2),encoding='utf-8')
    demos=[]
    # Large database/intermediate files stay under work/, not in the deliverable.
    workspace=ROOT.parent.parent
    experiment_id=uuid.uuid4().hex[:8]
    for docs in [5000,50000,500000]:
        database=workspace/f'work/disk_demo_{experiment_id}_{docs}/index.sqlite'
        label=f'bonus_disk_{docs}'
        timing=run_logged([sys.executable,ROOT/'code/tests/bonus_disk_demo.py','--docs',docs,'--database',database],
                          ROOT,LOGS/label,timeout=300)
        result=json.loads(text(LOGS/(label+'.stdout.txt')))
        assert result['passed']
        demos.append(dict(**result,seconds=timing['seconds'],peak_working_set_bytes=timing['peak_working_set_bytes']))
        print('PASS: disk backend',docs,demos[-1]['distinct_terms'],flush=True)
    target_v=400000000
    mean_key_bytes=16 # 15 visible bytes in term%010dx + null; assumption for estimate.
    estimate=dict(distinct_words=target_v,min_occurrences=target_v,documents=500000,
                  mean_key_bytes_assumption=mean_key_bytes,
                  doc_table_min_bytes=500000*types['int'],
                  c_payload_bytes=types['index']+500000*types['int']+target_v*(types['posting']+types['position']+mean_key_bytes),
                  c_hash_average_chain=target_v/types['hashsize'],
                  v1_term_metadata_bytes_without_strings=18*target_v,
                  warning='excludes allocator overhead, document-table spare capacity, extra stats/sort arrays, repeated occurrences; estimate, not measured')
    summary=dict(types=types,original_backend=rows,cli=cli_result,disk_backend_demo=demos,estimate=estimate,
                 executed_400m_distinct_words=False,created_500k_physical_files=False,
                 conclusion='C backend cannot scale directly; logical doc IDs fit; vocabulary/time/CLI/Windows file offsets are limiting')
    (RESULTS/'bonus_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with (RESULTS/'bonus_results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print('FINAL: BONUS TESTS PASSED (400m distinct words NOT executed)',flush=True)


if __name__=='__main__':
    main()
