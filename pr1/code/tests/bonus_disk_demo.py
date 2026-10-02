#!/usr/bin/env python3
"""A bounded-cache DISK BACKEND DEMO, separate from the user's C program.

SQLite B-tree stores both dictionary and positions on disk. Two deterministic
unique normalized terms per LOGICAL document; no 500k physical files are created.
This validates 500k doc IDs / 1m distinct keys, NOT 400m distinct keys.
Use --docs to reproduce smaller/larger runs; cache budget stays fixed at 8 MiB.
"""
import argparse
import json
import sqlite3
import time
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--docs',type=int,default=500000)
    ap.add_argument('--database',type=Path,required=True)
    args=ap.parse_args()
    assert args.docs>0
    assert not args.database.exists(),'use a new experiment directory'
    args.database.parent.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    conn=sqlite3.connect(args.database)
    conn.execute('PRAGMA page_size=4096')
    conn.execute('PRAGMA cache_size=-8192')
    conn.execute('PRAGMA temp_store=FILE')
    conn.execute('PRAGMA journal_mode=DELETE')
    conn.execute('PRAGMA synchronous=FULL')
    conn.execute('CREATE TABLE postings(term TEXT, doc INTEGER, pos INTEGER, PRIMARY KEY(term,doc,pos)) WITHOUT ROWID')
    conn.execute('CREATE TABLE terms(term TEXT PRIMARY KEY, cf INTEGER, df INTEGER) WITHOUT ROWID')
    # Vocabulary keys are already normalized; every term has cf=df=1, hence none
    # exceed theta=.5 when N>=2. This distribution does not test frequent words.
    assert args.docs>=2
    for begin in range(0,args.docs,1000):
        end=min(begin+1000,args.docs)
        rows=[(f'term{2*d+p:010d}x',d,p) for d in range(begin,end) for p in range(2)]
        conn.executemany('INSERT INTO postings VALUES(?,?,?)',rows)
        conn.executemany('INSERT INTO terms VALUES(?,1,1)',((term,) for term,d,p in rows))
        conn.commit()
    build=time.perf_counter()-started
    conn.close()
    # Independent restart: no build connection/cache reused.
    conn=sqlite3.connect(args.database)
    conn.execute('PRAGMA cache_size=-8192')
    conn.execute('PRAGMA temp_store=FILE')
    integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
    v=conn.execute('SELECT COUNT(*) FROM terms').fetchone()[0]
    m=conn.execute('SELECT COUNT(*) FROM postings').fetchone()[0]
    # Since each ID appears exactly twice, min/max plus count-distinct checks N.
    n=conn.execute('SELECT COUNT(DISTINCT doc) FROM postings').fetchone()[0]
    q_start=time.perf_counter()
    last=f'term{2*args.docs-1:010d}x'
    word=conn.execute('SELECT doc,pos FROM postings WHERE term=?',(last,)).fetchall()
    first=f'term{2*args.docs-2:010d}x'
    phrase=conn.execute('SELECT a.doc,a.pos FROM postings a JOIN postings b ON a.doc=b.doc AND b.pos=a.pos+1 WHERE a.term=? AND b.term=?',(first,last)).fetchall()
    tau=0.5/args.docs # below df/N = 1/N, so the single hit must be suppressed.
    allowed=conn.execute('SELECT df FROM terms WHERE term=? AND 1.0*df/?<=?',(last,args.docs,tau)).fetchall()
    passed=integrity=='ok' and n==args.docs and v==m==2*args.docs and word==[(args.docs-1,1)] and phrase==[(args.docs-1,0)] and not allowed
    result=dict(backend='SQLite disk B-tree prototype, NOT the C backend',logical_documents=n,
                physical_files_created=0,distinct_terms=v,positions=m,cache_budget_bytes=8*1024*1024,
                batch_positions_max=2000,database_bytes=args.database.stat().st_size,build_seconds=build,
                query_seconds=time.perf_counter()-q_start,word_hits=word,phrase_hits=phrase,
                threshold_suppressed=not allowed,integrity=integrity,passed=passed,
                limitations='normalized synthetic terms; one occurrence per term; no frequent-word stress; 400m vocabulary not executed')
    conn.close()
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
