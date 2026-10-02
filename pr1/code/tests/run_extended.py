#!/usr/bin/env python3
"""Reproducible Shakespeare correctness and theta/tau tests. Keep every command/log.

The C stemmer is shared deliberately; tokenization, aggregation, binary decoding,
stop-word choice and query reference answers are independent Python implementations.
"""
import csv
import hashlib
import json
import platform
import re
import shutil
import struct
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from brute_check import parse_index
from lab_support import run_logged, text

ROOT = Path(__file__).resolve().parents[2]
BIN = ROOT / 'bin'
RESULTS = ROOT / 'results'
LOGS = RESULTS / 'logs'
checks = []
REUSE = '--reuse-indexes' in sys.argv


def check(name, condition, detail=''):
    checks.append(dict(name=name, passed=bool(condition), detail=detail))
    print(('PASS' if condition else 'FAIL') + ': ' + name + ('; ' + detail if detail else ''), flush=True)


def compile_all():
    BIN.mkdir(exist_ok=True)
    for name, source in [('index_gen', ROOT/'code/index_gen.c'), ('query', ROOT/'code/query.c'),
                         ('stem_list', ROOT/'code/tests/stem_list.c'), ('roundtrip', ROOT/'code/tests/roundtrip.c')]:
        run_logged(['gcc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Wpedantic', source,
                    ROOT/'code/stem.c', '-lm', '-o', BIN/(name+'.exe')], ROOT, LOGS/('build_'+name))
        check('compile '+name+' with no warnings', not text(LOGS/('build_'+name+'.stderr.txt')).strip())


def stem_mapping(words):
    words = sorted(set(words))
    proc = subprocess.run([str(BIN/'stem_list.exe')], input='\n'.join(words)+'\n',
                          capture_output=True, text=True, encoding='ascii', check=True)
    stems = proc.stdout.splitlines()
    assert len(stems) == len(words), 'stemmer output count mismatch'
    return dict(zip(words, stems))


def query(folder, label, units, tau=None):
    command = [BIN/'query.exe'] + ([] if tau is None else [f'--tau={tau:.17g}']) + units
    measurement = run_logged(command, folder, LOGS/('query_'+label))
    output = text(folder/'output.txt')
    saved = RESULTS/'queries'/(label+'.txt')
    saved.parent.mkdir(exist_ok=True)
    saved.write_text(output, encoding='utf-8')
    docs = {int(x) for x in re.findall(r'^Doc ID: (\d+)', output, re.M)}
    positions = [(int(d),int(p)) for d,p in re.findall(r'^Doc ID: (\d+), Position: (\d+)', output, re.M)]
    phrase_positions = []
    for d, rest in re.findall(r'^Doc ID: (\d+), Positions: ([0-9 ]+)', output, re.M):
        phrase_positions += [(int(d),int(p)) for p in rest.split()]
    return output, docs, positions, phrase_positions, measurement


def phrase_hits(per_doc, wanted):
    return [(d,p) for d, seq in enumerate(per_doc) for p in range(len(seq)-len(wanted)+1)
            if seq[p:p+len(wanted)] == wanted]


def run_all():
    compile_all()
    files = sorted((ROOT/'data/shakespeare/corpus').glob('*.txt'))
    manifest = json.loads(text(ROOT/'data/shakespeare/manifest.json'))
    check('complete MIT catalogue', len(files)==42 and sum(d['kind']=='play' for d in manifest['documents'])==37)
    raw_docs = [[w.lower()[:255] for w in re.findall(r'[A-Za-z0-9]+', text(f))] for f in files]
    mapping = stem_mapping(w for seq in raw_docs for w in seq)
    per_doc = [[mapping[w] for w in seq] for seq in raw_docs]
    expected = defaultdict(list)
    for d,seq in enumerate(per_doc):
        for p,w in enumerate(seq):
            expected[w].append((d,p))
    stats = {w:(len(pos),len({d for d,_ in pos})) for w,pos in expected.items()}
    with (RESULTS/'word_statistics.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer=csv.writer(f); writer.writerow(['stem','cf','df','df/N','stop_at_theta_0.5'])
        writer.writerows((w,cf,df,df/42,df/42>0.5) for w,(cf,df) in sorted(stats.items(),key=lambda x:(-x[1][0],x[0])))
    baseline = RESULTS/'shakespeare/theta_0.5'
    initial = LOGS/'initial_full_build.run.json'
    if not (REUSE and initial.exists() and (baseline/'index.bin').exists()):
        if (baseline/'index.bin').exists():
            (baseline/'index.bin').unlink()
        run_logged([BIN/'index_gen.exe','--theta=0.5','--dump-tokens=tokens.txt']+files,baseline,LOGS/'initial_full_build')
    token_ok = True
    row_count=0
    with (baseline/'tokens.txt').open(encoding='ascii') as f:
        for d,seq in enumerate(raw_docs):
            for p,w in enumerate(seq):
                row_count+=1
                if f.readline().split() != [w,str(d),str(p)]:
                    token_ok=False
        token_ok=token_ok and not f.read()
    check('all raw tokens match independent ASCII regex',token_ok,f'{row_count} tokens')
    theta_rows=[]
    parsed={}
    for theta in [0.3,0.4,0.5,0.6,0.8]:
        folder=RESULTS/f'shakespeare/theta_{theta:.1f}'
        if theta==0.5:
            timing=json.loads(text(initial))
        elif REUSE and (folder/'index.bin').exists():
            timing=json.loads(text(LOGS/f'theta_{theta:.1f}.run.json'))
        else:
            if (folder/'index.bin').exists():
                (folder/'index.bin').unlink()
            timing=run_logged([BIN/'index_gen.exe',f'--theta={theta}']+files,folder,LOGS/f'theta_{theta:.1f}',timeout=300)
        docs,actual=parse_index(folder/'index.bin')
        stops={w for w,(cf,df) in stats.items() if df/42>theta}
        sl={line.split()[0] for line in text(folder/'stoplist.txt').splitlines() if line and not line.startswith('#')}
        want={w:pos for w,pos in expected.items() if w not in stops}
        check(f'theta={theta}: exact term/doc/position equality',docs==list(range(42)) and actual==want)
        check(f'theta={theta}: stoplist matches strict df/N threshold',sl==stops)
        check(f'theta={theta}: zero dropped positions','0 positions dropped' in text(LOGS/('initial_full_build.stderr.txt' if theta==0.5 else f'theta_{theta:.1f}.stderr.txt')))
        positions=sum(map(len,actual.values()))
        theta_rows.append(dict(theta=theta,documents=len(docs),raw_stems=len(stats),stop_words=len(sl),
            indexed_stems=len(actual),positions=positions,retained_fraction=positions/row_count,
            index_bytes=(folder/'index.bin').stat().st_size,seconds=timing['seconds'],
            peak_working_set_bytes=timing['peak_working_set_bytes']))
        parsed[theta]=actual
    actual=parsed[0.5]
    # Rebuilding into a fresh directory avoids Windows rename-over-existing limitations.
    repeat=RESULTS/'shakespeare/repeat_0.5'
    if not (REUSE and (repeat/'index.bin').exists()):
        if (repeat/'index.bin').exists():
            (repeat/'index.bin').unlink()
        run_logged([BIN/'index_gen.exe','--theta=0.5']+files,repeat,LOGS/'repeat_0.5')
    digest=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    check('repeated full build is byte-identical',digest(baseline/'index.bin')==digest(repeat/'index.bin'))
    run_logged([BIN/'roundtrip.exe',baseline/'index.bin',baseline/'roundtrip.bin'],baseline,LOGS/'roundtrip')
    check('C load/save roundtrip is byte-identical',digest(baseline/'index.bin')==digest(baseline/'roundtrip.bin'))
    query_rows=[]
    for word in ['hamlet','HAMLET','horatio','antonio','bassanio','unicornzzzz','the','love']:
        out,docs,pos,_,timing=query(baseline,word,[word])
        stem=stem_mapping([word.lower()])[word.lower()]
        want=actual.get(stem,[])
        check('word query '+word,pos==want and docs=={d for d,_ in want})
        query_rows.append(dict(query=word,kind='word',documents=len(docs),positions=len(pos),seconds=timing['seconds']))
    for words in [['antonio','bassanio'],['hamlet','horatio'],['hamlet','unicornzzzz']]:
        out,docs,*_=query(baseline,'AND_'+'_'.join(words),words)
        stemmed=stem_mapping(words)
        want=set(range(42))
        for word in words:
            want &= {d for d,_ in actual.get(stemmed[word],[])}
        check('AND '+str(words),docs==want)
        query_rows.append(dict(query=' AND '.join(words),kind='AND',documents=len(docs)))
    for phrase in ['et tu brute','yorick horatio','gallop apace','to be or not to be']:
        words=phrase.split(); sm=stem_mapping(words); wanted=[sm[w] for w in words]
        raw_hits=phrase_hits(per_doc,wanted)
        available=all(w in actual for w in wanted)
        want=raw_hits if available else []
        out,docs,_,got,timing=query(baseline,'PHRASE_'+phrase.replace(' ','_'),[phrase])
        check('phrase '+phrase,got==want and docs=={d for d,_ in want},f'raw={len(raw_hits)}; index={len(got)}')
        query_rows.append(dict(query=phrase,kind='phrase',raw_matches=len(raw_hits),all_terms_indexed=available,
                               documents=len(docs),positions=len(got),expected_positions=want))
    # Representative words chosen by raw word form (never stem an already stemmed key twice).
    selected=[]
    for name,lo,hi in [('high',0.35,0.5),('mid',0.10,0.20),('rare',0,1/42)]:
        candidates=[w for w in mapping if mapping[w] in actual and lo < stats[mapping[w]][1]/42 <= hi and w.isalpha()]
        candidates.sort(key=lambda w:(-stats[mapping[w]][0],w))
        assert candidates,name
        word=candidates[0]; cf,df=stats[mapping[word]]
        selected.append(dict(level=name,word=word,stem=mapping[word],cf=cf,df=df,ratio=df/42))
    tau_rows=[]
    for tau in [None,0.02,0.1,0.2,0.3,0.4,0.5]:
        for sample in selected:
            out,docs,pos,_,timing=query(baseline,f'tau_{tau}_{sample["level"]}',[sample['word']],tau)
            blocked='Too common:' in out
            expected_block=tau is not None and sample['ratio']>tau
            check(f'tau={tau} {sample["word"]}',blocked==expected_block and len(docs)==(0 if expected_block else sample['df']))
            tau_rows.append(dict(tau=tau,**sample,blocked=blocked,displayed_documents=len(docs),
                                 displayed_positions=len(pos),seconds=timing['seconds']))
    for sample in selected:
        tau=sample['ratio']
        out,docs,*_=query(baseline,'tau_equal_'+sample['level'],[sample['word']],tau)
        check('tau equality is allowed '+sample['word'],'Too common:' not in out and len(docs)==sample['df'])
    # Isolated edge cases; leave the complete corpus index intact.
    damaged=RESULTS/'edge_cases/corrupt'; damaged.mkdir(parents=True,exist_ok=True)
    good=(baseline/'index.bin').read_bytes()
    variants={'truncated':good[:-1],'wrong_version':good[:8]+struct.pack('<I',2)+good[12:],
              'garbage':b'not an index','trailing':good+b'x'}
    for name,blob in variants.items():
        (damaged/'index.bin').write_bytes(blob)
        measurement=run_logged([BIN/'query.exe','hamlet'],damaged,LOGS/('corrupt_'+name),expect=None)
        check('corruption rejected '+name,measurement['exit_code']!=0)
    empty=RESULTS/'edge_cases/empty'; empty.mkdir(parents=True,exist_ok=True)
    (empty/'empty.txt').write_text('',encoding='ascii')
    if (empty/'index.bin').exists():
        (empty/'index.bin').unlink()
    run_logged([BIN/'index_gen.exe',empty/'empty.txt'],empty,LOGS/'empty_build')
    out,docs,*_=query(empty,'empty',['hamlet'])
    check('empty document stays in N', (empty/'index.bin').stat().st_size==68 and not docs)
    (empty/'index.bin').write_bytes(b'PR1IDX\0\0'+struct.pack('<IIQQQQQQ',1,64,0,0,0,64,64,64))
    out,docs,*_=query(empty,'zero_documents',['hamlet'])
    check('zero-document header can load',not docs and 'Not found:' in out)
    # Two terms with unequal tf expose phrase-anchor ordering bugs at theta=1.
    fixture=RESULTS/'edge_cases/phrase_order'; fixture.mkdir(parents=True,exist_ok=True)
    (fixture/'a.txt').write_text('alpha beta alpha alpha gamma\n',encoding='ascii')
    if (fixture/'index.bin').exists():
        (fixture/'index.bin').unlink()
    run_logged([BIN/'index_gen.exe','--theta=1',fixture/'a.txt'],fixture,LOGS/'phrase_fixture_build')
    out,docs,_,pos,_=query(fixture,'phrase_order_regression',['alpha beta'])
    check('phrase order regression alpha beta',pos==[(0,0)])
    (fixture/'test.txt').write_text('alpha gamma\nphrase: alpha beta\nalpha\n',encoding='ascii')
    run_logged([BIN/'query.exe'],fixture,LOGS/'query_file_input')
    file_output=text(fixture/'output.txt')
    (RESULTS/'queries/file_input.txt').write_text(file_output,encoding='utf-8')
    check('test.txt multiple words mean AND','AND [alpha gamma]: 1 document(s)' in file_output)
    check('test.txt phrase prefix preserves order','Phrase [alpha beta]: 1 match(es)' in file_output and 'Doc ID: 0, Positions: 0' in file_output)
    check('test.txt processes all lines',file_output.count('# query ')==3)
    fixture_hash=digest(fixture/'index.bin')
    run_logged([BIN/'index_gen.exe','--theta=1',fixture/'a.txt'],fixture,LOGS/'overwrite_existing_index')
    check('rebuilding replaces existing index on Windows',digest(fixture/'index.bin')==fixture_hash)
    for phrase,want in [('beta alpha',[(0,1)]),('alpha alpha',[(0,2)]),('gamma alpha',[])]:
        out,docs,_,pos,_=query(fixture,'phrase_regression_'+phrase.replace(' ','_'),[phrase])
        check('phrase regression '+phrase,pos==want)
    trailing=RESULTS/'edge_cases/trailing_empty'; trailing.mkdir(parents=True,exist_ok=True)
    (trailing/'first.txt').write_text('alpha beta',encoding='ascii')
    (trailing/'last.txt').write_text('',encoding='ascii')
    if (trailing/'index.bin').exists():
        (trailing/'index.bin').unlink()
    run_logged([BIN/'index_gen.exe','--theta=1',trailing/'first.txt',trailing/'last.txt'],trailing,LOGS/'trailing_empty_build')
    out,docs,*_=query(trailing,'trailing_empty',['alpha'])
    check('trailing empty document is loadable',docs=={0} and 'df=1/2' in out)
    # Mutate doc-table ID 0 to 2; posting ID 0 is now absent from docs, must reject.
    blob=bytearray((trailing/'index.bin').read_bytes()); blob[64:68]=struct.pack('<I',2)
    (damaged/'index.bin').write_bytes(blob)
    measurement=run_logged([BIN/'query.exe','alpha'],damaged,LOGS/'corrupt_absent_doc',expect=None)
    check('posting referencing absent document is rejected',measurement['exit_code']!=0)
    summary=dict(environment=dict(platform=platform.platform(),python=sys.version,gcc=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0]),
        corpus=dict(documents=42,plays=37,poetry=5,sonnets=154,tokens=row_count,raw_word_types=len(mapping),stems=len(stats),
                    source_commit='5d36a46145236b406eb37643db4e5cefcb351f3a',original_reference_commit='3e6a56990661e8a7f7db92e899f87ff379b10431',mirror_commit=manifest['mirror_commit']),
        theta=theta_rows,selected_query_words=selected,tau=tau_rows,queries=query_rows,checks=checks,
        passed=sum(c['passed'] for c in checks),failed=sum(not c['passed'] for c in checks),
        index_sha256=digest(baseline/'index.bin'))
    (RESULTS/'shakespeare_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    for filename,rows in [('theta_results.csv',theta_rows),('tau_results.csv',tau_rows)]:
        with (RESULTS/filename).open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(f'FINAL: PASS={summary["passed"]} FAIL={summary["failed"]}',flush=True)
    return bool(summary['failed'])


if __name__=='__main__':
    raise SystemExit(run_all())
