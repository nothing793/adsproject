#!/usr/bin/env python3
"""Additional input and file-format regressions; preserve before/after results."""
import argparse
import hashlib
import json
import random
import re
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def varint(value):
    out=bytearray()
    while value>=128:
        out.append((value&127)|128); value>>=7
    out.append(value)
    return bytes(out)

def make_index(docs, records):
    """Construct small files independently of the C writer, including malformed ones."""
    terms_off=64+4*len(docs)
    postings_off=terms_off+sum(18+len(word) for word,df,tf,posting in records)
    offset=postings_off; dictionary=b''; postings=b''
    for word,df,tf,posting in records:
        dictionary+=struct.pack('<IIQH',df,tf,offset,len(word))+word
        postings+=posting; offset+=len(posting)
    header=b'PR1IDX\0\0'+struct.pack('<IIQQQQQQ',1,64,len(docs),len(records),
        sum(r[2] for r in records),64,terms_off,postings_off)
    return header+b''.join(struct.pack('<I',d) for d in docs)+dictionary+postings

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--bin',type=Path,default=ROOT/'bin')
    ap.add_argument('--source',type=Path,default=ROOT/'code')
    ap.add_argument('--label',choices=['before','after'],default='after')
    args=ap.parse_args(); args.bin=args.bin.resolve(); args.source=args.source.resolve()
    checks=[]; commands=[]
    def check(name,passed,detail=''):
        checks.append(dict(name=name,passed=bool(passed),detail=detail))
        print(('PASS' if passed else 'FAIL')+': '+name,flush=True)
    def run(exe,arguments,cwd):
        command=[str(args.bin/(exe+'.exe'))]+list(map(str,arguments))
        p=subprocess.run(command,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        result=(cwd/'output.txt').read_text(encoding='utf-8') if exe=='query' and (cwd/'output.txt').exists() else ''
        commands.append(dict(command=command,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,output=result))
        return p,result
    def positions(out):
        return [(int(d),int(p)) for d,p in re.findall(r'^Doc ID: (\d+), Position: (\d+)',out,re.M)]
    def phrase_positions(out):
        return [(int(d),int(p)) for d,ps in re.findall(r'^Doc ID: (\d+), Positions: ([0-9 ]+)',out,re.M) for p in ps.split()]
    with tempfile.TemporaryDirectory(prefix='pr1-review-') as tmp:
        base=Path(tmp); fixture=base/'fixture'; fixture.mkdir()
        (fixture/'a.txt').write_text("Alpha, beta ALPHA alpha gamma. Cats were running. abc123 123 well-known don't.\n",encoding='ascii')
        (fixture/'b.txt').write_text('beta gamma cats alpha beta',encoding='ascii')
        (fixture/'empty.txt').write_text('',encoding='ascii')
        files=[fixture/'a.txt',fixture/'b.txt',fixture/'empty.txt']
        p,_=run('index_gen',['--theta=1',*files],fixture)
        check('fixture index builds without filtering',p.returncode==0)
        p,out=run('query',['ALPHA,'],fixture)
        check('punctuated word uses the corpus tokenizer',p.returncode==0 and positions(out)==[(0,0),(0,2),(0,3),(1,3)])
        for phrase,want in [('ALPHA,\tBETA!',[(0,0),(1,3)]),('well-known',[(0,10)]),("don't",[(0,12)])]:
            p,out=run('query',[phrase],fixture)
            check('punctuated phrase '+phrase,p.returncode==0 and phrase_positions(out)==want)
        p,out=run('query',['123'],fixture)
        check('numeric query matches the corpus',positions(out)==[(0,9)])
        invalid_options=base/'invalid_options'; invalid_options.mkdir()
        for option,exe in [('--tau=','query'),('--theta=','index_gen')]:
            for value in ['', 'nan','nan(1)','inf','-0.1','1.1','0.5junk']:
                p,_=run(exe,[option+value,'alpha' if exe=='query' else files[0]],fixture if exe=='query' else invalid_options)
                check(option+value+' is rejected',p.returncode==2)
        p,out=run('query',['--tau=0','alpha'],fixture)
        check('tau=0 suppresses indexed words','Too common:' in out and not positions(out))
        p,out=run('query',['--tau=1','alpha'],fixture)
        check('tau=1 includes indexed words',positions(out)==[(0,0),(0,2),(0,3),(1,3)])
        (fixture/'test.txt').write_text('alpha,gamma\nphrase: ALPHA, beta!\n',encoding='ascii')
        p,out=run('query',[],fixture)
        check('file input punctuation preserves AND and phrase semantics',p.returncode==0 and 'AND [alpha gamma]: 2 document(s)' in out and 'Phrase [ALPHA, beta!]: 2 match(es)' in out)
        (fixture/'test.txt').write_text('a'*1500+'\n',encoding='ascii')
        p,_=run('query',[],fixture)
        check('overlong file input is rejected, not split into queries',p.returncode!=0)
        p,out=run('query',[' '.join(['alpha']*17)],fixture)
        check('phrase word limit is enforced',p.returncode!=0 and 'too many words' in out)
        counts=base/'count_only'; counts.mkdir()
        p,_=run('index_gen',['--count-only','--theta=1',files[0]],counts)
        check('count-only reports counts without writing an index',p.returncode==0 and not (counts/'index.bin').exists() and 'top ' in p.stdout and (counts/'stoplist.txt').exists())
        broken=base/'broken'; broken.mkdir()
        good=make_index([0],[(b'alpha',1,1,b'\0\1\1')])
        (broken/'index.bin').write_bytes(good)
        p,out=run('query',['alpha'],broken)
        check('independently encoded valid index loads',p.returncode==0 and positions(out)==[(0,0)])
        boundary=make_index([0],[(b'alpha',1,1,b'\0\1'+varint(0x80000000))])
        (broken/'index.bin').write_bytes(boundary)
        boundary_command=['gcc','-std=c99','-O1','-ftrapv','-Wall','-Wextra','-Wpedantic',
            '-I',str(args.source),str(ROOT/'code/tests/range_roundtrip.c'),'-o',str(args.bin/'range_roundtrip.exe')]
        subprocess.run(boundary_command,check=True,capture_output=True)
        p,_=run('range_roundtrip',[broken/'index.bin',broken/'saved.bin'],broken)
        check('INT_MAX position survives a checked load/save roundtrip',p.returncode==0 and (broken/'saved.bin').read_bytes()==boundary)
        mutations={
            'unsorted doc table':make_index([1,0],[(b'alpha',2,2,b'\0\1\1\1\1\1')]),
            'duplicate dictionary term':make_index([0],[(b'alpha',1,1,b'\0\1\1'),(b'alpha',1,1,b'\0\1\2')]),
            'unsorted dictionary':make_index([0],[(b'beta',1,1,b'\0\1\1'),(b'alpha',1,1,b'\0\1\2')]),
            'position delta overflow':make_index([0],[(b'alpha',1,2,b'\0\2\1'+varint(0xffffffff))]),
            'document delta overflow':make_index([0,1],[(b'alpha',2,2,b'\1\1\1'+varint(0xffffffff)+b'\1\1')]),
            'posting offset overflow':good[:76]+struct.pack('<Q',0xffffffffffffffff)+good[84:],
        }
        for name,blob in mutations.items():
            (broken/'index.bin').write_bytes(blob)
            p,_=run('query',['alpha'],broken)
            check('malformed index rejected: '+name,p.returncode!=0)
        # Fixed seed; compare a corpus with repeated terms and empty documents.
        rng=random.Random(793); vocabulary=['alpha','beta','gamma','delta']
        raw=[[rng.choice(vocabulary) for _ in range(rng.randrange(0,45))] for _ in range(12)]+[[]]
        random_dir=base/'random'; random_dir.mkdir(); random_files=[]
        for i,seq in enumerate(raw):
            f=random_dir/f'{i:02}.txt'; f.write_text(' '.join(seq),encoding='ascii'); random_files.append(f)
        run('index_gen',['--theta=1',*random_files],random_dir)
        mismatches=[]
        for i in range(80):
            wanted=[rng.choice(vocabulary) for _ in range(rng.randrange(2,5))]
            phrase=i%2==0
            args_query=[' '.join(wanted)] if phrase else wanted
            p,out=run('query',args_query,random_dir)
            if phrase:
                expected=[(d,pos) for d,seq in enumerate(raw) for pos in range(len(seq)-len(wanted)+1) if seq[pos:pos+len(wanted)]==wanted]
                got=phrase_positions(out)
            else:
                expected=[d for d,seq in enumerate(raw) if all(w in seq for w in wanted)]
                got=[int(d) for d in re.findall(r'^Doc ID: (\d+)$',out,re.M)]
            if p.returncode or got!=expected: mismatches.append(dict(query=args_query,expected=expected,actual=got))
        check('80 fixed-seed AND/phrase cases match independent enumeration',not mismatches,json.dumps(mismatches))
        compile_command=['gcc','-std=c99','-O2','-Wall','-Wextra','-Wpedantic',str(args.source/'index_gen.c'),str(args.source/'stem.c'),str(ROOT/'code/tests/review_malloc_fault.c'),'-Wl,--wrap=malloc','-lm','-o',str(args.bin/'fault_index_gen.exe')]
        subprocess.run(compile_command,check=True,capture_output=True)
        fault=base/'allocation_failure'; fault.mkdir(); (fault/'a.txt').write_text('alpha alpha',encoding='ascii')
        p,_=run('fault_index_gen',['--theta=1',fault/'a.txt'],fault)
        check('position allocation failure aborts instead of saving partial data',p.returncode!=0 and not (fault/'index.bin').exists())
    summary=dict(label=args.label,checks=checks,passed=sum(c['passed'] for c in checks),failed=sum(not c['passed'] for c in checks),random_cases=80)
    destination=ROOT/'results'; destination.mkdir(exist_ok=True)
    (destination/f'review_{args.label}.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (destination/f'review_{args.label}_commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"REVIEW: PASS={summary['passed']} FAIL={summary['failed']}",flush=True)
    return bool(summary['failed'])

if __name__=='__main__':
    raise SystemExit(main())
