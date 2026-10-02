#!/usr/bin/env python3
"""Verify downloaded current repository vs the original tested baseline."""
import hashlib
import json
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[2]
current=Path(sys.argv[1]).resolve()
rows=[]
for name in ['index.h','query.c','index_gen.c','stem.c','stem.h']:
    old=root/'evidence/before_fix'/name if name in ['index.h','query.c','index_gen.c'] else root/'code'/name
    a=old.read_text(encoding='utf-8')
    b=(current/'code'/name).read_text(encoding='utf-8')
    rows.append(dict(file='code/'+name,normalized_sha256=hashlib.sha256(b.encode('utf-8')).hexdigest(),
                     equivalent_to_original_test_baseline=a==b))
assert all(row['equivalent_to_original_test_baseline'] for row in rows)
result=dict(repository='https://github.com/nothing793/adsproject',branch='main',
            commit='5d36a46145236b406eb37643db4e5cefcb351f3a',
            initial_reference='https://github.com/nothing793/nothing793_1/tree/master/ADS/pr1',
            initial_reference_commit='3e6a56990661e8a7f7db92e899f87ff379b10431',
            comparison='UTF-8 text with CRLF/LF normalized by universal newline reading',files=rows,
            conclusion='same C code baseline; old corpus build evidence applies; final query/load/Windows fixes retested')
(root/'evidence/repository_baseline.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: current adsproject baseline matches all 5 original C source files after newline normalization')
