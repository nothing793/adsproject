#!/usr/bin/env python3
"""编译、独立穷举对拍及几何检查；原始输入、输出、统计统一写入指定目录。"""
import argparse
import csv
import hashlib
import itertools
import json
import platform
import random
import re
import statistics
import subprocess
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SEED = 20261020


def candidate_edges(grid):
    """小规模参考模型：两两枚举连接器，并独立检查开区间内是否还有连接器。"""
    nodes = [(r,c) for r,row in enumerate(grid) for c,k in enumerate(row) if k]
    edges = []
    for a,b in itertools.combinations(nodes,2):
        if a[0] == b[0] and not any(grid[a[0]][c] for c in range(a[1]+1,b[1])):
            edges.append((a,b))
        elif a[1] == b[1] and not any(grid[r][a[1]] for r in range(a[0]+1,b[0])):
            edges.append((a,b))
    return nodes,edges


def crosses(first, second):
    a,b=first; c,d=second
    if a[0] != b[0]:
        a,b,c,d=c,d,a,b
    return a[0] == b[0] and c[1] == d[1] and c[0] < a[0] < d[0] and a[1] < c[1] < b[1]


def brute_feasible(grid, ignore_crossings=False):
    """直接枚举选边，不使用 SAT 子句、监视表或学习规则。"""
    nodes,edges=candidate_edges(grid)
    index={node:i for i,node in enumerate(nodes)}
    need=[grid[r][c] for r,c in nodes]
    remain=[0]*len(nodes)
    endpoints=[(index[a],index[b]) for a,b in edges]
    for a,b in endpoints:
        remain[a]+=1; remain[b]+=1
    selected=[]

    def search(position):
        if any(k<0 or k>r for k,r in zip(need,remain)):
            return False
        if position == len(edges):
            return not any(need)
        a,b=endpoints[position]
        remain[a]-=1; remain[b]-=1
        if need[a] and need[b] and (ignore_crossings or not any(crosses(edges[position],edges[i]) for i in selected)):
            need[a]-=1; need[b]-=1; selected.append(position)
            found=search(position+1)
            selected.pop(); need[a]+=1; need[b]+=1
            if found:
                remain[a]+=1; remain[b]+=1
                return True
        found=search(position+1)
        remain[a]+=1; remain[b]+=1
        return found
    return search(0)


def check_output(grid, text):
    """按射线恢复输出中的线段，检查度数、互反、最邻近端点和真实几何交叉。"""
    if text == 'No Solution\n':
        return False
    nodes=[(r,c) for r,row in enumerate(grid) for c,k in enumerate(row) if k]
    lines=text.splitlines()
    assert len(lines)==len(nodes), '连接器输出行数不符'
    states={}
    for node,line in zip(nodes,lines):
        assert re.fullmatch(r'\d+(?: \d+){5}',line), '输出空格或字段格式错误'
        row,column,*bits=map(int,line.split(' '))
        assert (row-1,column-1)==node, '未按行优先输出'
        assert all(b in (0,1) for b in bits), '方向值非 0/1'
        assert sum(bits)==grid[node[0]][node[1]], '连接器度数错误'
        states[node]=bits
    segments=set()
    for (r,c),bits in states.items():
        for direction,(dr,dc) in enumerate(((-1,0),(1,0),(0,-1),(0,1))):
            if not bits[direction]:
                continue
            nr,nc=r+dr,c+dc
            while 0<=nr<len(grid) and 0<=nc<len(grid[0]) and not grid[nr][nc]:
                nr+=dr; nc+=dc
            assert (nr,nc) in states, '栅栏离开边界或没有连接器端点'
            assert states[nr,nc][direction^1], '边的两个端点不互反'
            segments.add(tuple(sorted(((r,c),(nr,nc)))))
    occupied={}
    for (r1,c1),(r2,c2) in segments:
        axis=0 if r1==r2 else 1
        cells=((r1,c) for c in range(c1+1,c2)) if axis==0 else ((r,c1) for r in range(r1+1,r2))
        for cell in cells:
            assert cell not in occupied or occupied[cell]==axis, '空位置发生交叉'
            occupied[cell]=axis
    return True


def encode(grid):
    return f'{len(grid)} {len(grid[0])}\n'+''.join(' '.join(map(str,row))+'\n' for row in grid)


def witness_grid(rows, columns, rng, probability):
    """从单位栅栏的已知合法布局反推度数，作为大规模可解输入的独立见证。"""
    grid=[[0]*columns for _ in range(rows)]
    for r in range(rows):
        for c in range(columns):
            for dr,dc in ((0,1),(1,0)):
                if r+dr<rows and c+dc<columns and rng.random()<probability:
                    grid[r][c]+=1; grid[r+dr][c+dc]+=1
    return grid


def sat_core_tests(driver, output, rng):
    cases=[]
    # 覆盖空公式、空子句、互相矛盾的单位子句及零变量边界。
    cases.extend([(0,[],True),(0,[[]],False),(1,[[1],[-1]],False)])
    for _ in range(3000):
        n=rng.randint(1,10)
        clauses=[]
        for _ in range(rng.randint(0,55)):
            variables=rng.sample(range(1,n+1),rng.randint(1,min(4,n)))
            clauses.append([v if rng.randrange(2) else -v for v in variables])
        expected=any(all(any(bool(mask&(1<<(abs(lit)-1)))==(lit>0) for lit in clause) for clause in clauses) for mask in range(1<<n))
        cases.append((n,clauses,expected))
    # 7 只鸽子放入 6 个孔，每鸽至少一孔，每孔最多一鸽；必不可满足。
    n=42; clauses=[]
    for pigeon in range(7):
        clauses.append([pigeon*6+hole+1 for hole in range(6)])
    for hole in range(6):
        for a,b in itertools.combinations(range(7),2):
            clauses.append([-(a*6+hole+1),-(b*6+hole+1)])
    cases.append((n,clauses,False))
    payload=''.join(f'{n} {len(cs)}\n'+''.join(' '.join(map(str,c))+' 0\n' for c in cs) for n,cs,_ in cases)
    (output/'sat_cases.txt').write_text(payload,encoding='utf-8')
    p=subprocess.run([str(driver)],input=payload,capture_output=True,text=True,encoding='utf-8',timeout=120)
    (output/'sat_stdout.txt').write_text(p.stdout,encoding='utf-8')
    (output/'sat_statistics.txt').write_text(p.stderr,encoding='utf-8')
    assert p.returncode==0,p.stderr
    lines=p.stdout.splitlines(); assert len(lines)==len(cases)
    records=[]
    for case_id,(line,(n,clauses,expected)) in enumerate(zip(lines,cases)):
        assert (line.split()[0]=='SAT')==expected,(line,n,clauses)
        if expected:
            values=list(map(int,line.split()[1:])); assert len(values)==n
            assert all(any(bool(values[abs(lit)-1])==(lit>0) for lit in clause) for clause in clauses)
        records.append({'case':case_id,'variables':n,'clauses':len(clauses),'expected':expected,'actual':line.split()[0]=='SAT','passed':True,'purpose':'鸽巢冲突学习及重启' if case_id==len(cases)-1 else '枚举真值表检查可满足性及返回模型'})
    with (output/'sat_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    stats=[list(map(int,line.split())) for line in p.stderr.splitlines()]
    assert stats[-1][0]>0 and stats[-1][1]>0 and stats[-1][2]>0,'未覆盖冲突学习与重启'
    return {'cases':len(cases),'passed':len(cases),'pigeonhole_conflicts':stats[-1][0],'pigeonhole_learned':stats[-1][1],'pigeonhole_restarts':stats[-1][2]}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=PROJECT/'testresult/run')
    ap.add_argument('--cc',default='gcc')
    args=ap.parse_args(); output=args.output.resolve(); output.mkdir(parents=True,exist_ok=True)
    for folder in ('bin','inputs','outputs','logs'):
        (output/folder).mkdir(exist_ok=True)
    suffix='.exe' if platform.system()=='Windows' else ''
    program=output/'bin'/('fence'+suffix); driver=output/'bin'/('sat_driver'+suffix)
    builds=[]
    for destination,sources in ((program,['main.c','fence.c','sat.c']),(driver,['tests/sat_driver.c','sat.c'])):
        command=[args.cc,'-std=c99','-O2','-Wall','-Wextra','-Wpedantic']+[str(PROJECT/'code'/s) for s in sources]+['-o',str(destination)]
        p=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
        builds.append({'command':command,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        assert p.returncode==0 and not p.stderr,p.stderr
    (output/'build.json').write_text(json.dumps(builds,ensure_ascii=False,indent=2),encoding='utf-8')
    rng=random.Random(SEED); rows=[]

    def run_case(name,group,grid,expected,purpose):
        data=encode(grid); (output/'inputs'/f'{name}.txt').write_text(data,encoding='utf-8')
        start=time.perf_counter()
        p=subprocess.run([str(program),'--stats'],input=data,capture_output=True,text=True,encoding='utf-8',timeout=30)
        elapsed=(time.perf_counter()-start)*1000
        (output/'outputs'/f'{name}.txt').write_text(p.stdout,encoding='utf-8')
        (output/'logs'/f'{name}.json').write_text(json.dumps({'exit_code':p.returncode,'stderr':p.stderr,'wall_ms':elapsed},ensure_ascii=False,indent=2),encoding='utf-8')
        assert p.returncode==0,(name,p.stderr)
        feasible=check_output(grid,p.stdout)
        assert feasible==expected,(name,expected,p.stdout)
        stats=json.loads(p.stderr)
        rows.append({'name':name,'group':group,'rows':len(grid),'columns':len(grid[0]),'expected':expected,'actual':feasible,'passed':True,'wall_ms':elapsed,'purpose':purpose,**stats})

    samples=re.findall(r'Sample Input (\d):\s*\n(.*?)\n\s*Sample Output \1:',(PROJECT/'readme.md').read_text(encoding='utf-8'),re.S)
    assert len(samples)==3
    for number,text in samples:
        values=list(map(int,text.split())); n,m=values[:2]
        grid=[values[2+r*m:2+(r+1)*m] for r in range(n)]
        run_case('sample_'+number,'sample',grid,number!='2','题目样例及非唯一解几何检查')
    curated=[
        ('empty',[[0,0],[0,0]],True,'无连接器，输出为空'),
        ('single',[[1,0],[0,0]],False,'孤立连接器'),
        ('square',[[2,2],[2,2]],True,'最小闭合栅栏'),
        ('multiple',[[1,1],[1,1]],True,'多解且不要求整体连通'),
        ('too_many',[[4,4],[4,4]],False,'边界可用方向不足'),
        ('forced_cross',[[0,1,0],[1,0,1],[0,1,0]],False,'度数可满足但交叉导致无解'),
        ('avoid_cross',[[1,1,1],[1,0,1],[1,1,1]],True,'存在交叉候选但可选择合法布局'),
        ('shared_four',[[0,1,0],[1,4,1],[0,1,0]],True,'四路连接器处允许交汇'),
        ('odd_cycle',[[2,0,2],[0,0,0],[2,2,2]],True,'含长边的奇环，不能假设候选图总为二分图'),
        ('long_horizontal',[[1]+[0]*48+[1],[0]*50],True,'跨越 48 个空格的长边'),
        ('long_vertical',[[1,0]]+[[0,0] for _ in range(48)]+[[1,0]],True,'50 行长边'),
        ('global_odd',[[1,1,1],[1,1,1],[1,1,1]],False,'度数和为奇数'),
    ]
    for name,grid,expected,purpose in curated:
        assert brute_feasible(grid)==expected
        run_case(name,'curated',grid,expected,purpose)
    for index,values in enumerate(itertools.product(range(5),repeat=4)):
        grid=[list(values[:2]),list(values[2:])]
        run_case(f'exhaustive_2x2_{index:03d}','exhaustive_2x2',grid,brute_feasible(grid),'2×2 所有 0..4 度数组合穷举')
    for mask in range(512):
        grid=[[(mask>>(r*3+c))&1 for c in range(3)] for r in range(3)]
        run_case(f'matching_3x3_{mask:03d}','matching_3x3',grid,brute_feasible(grid),'3×3 所有 0/1 组合，覆盖空格交叉及匹配')
    for index in range(600):
        n,m=rng.randint(2,5),rng.randint(2,5)
        while True:
            grid=[[rng.choices([0,1,2,3,4],[4,4,3,1,1])[0] for _ in range(m)] for _ in range(n)]
            if len(candidate_edges(grid)[1])<=18:
                break
        run_case(f'random_small_{index:03d}','random_small',grid,brute_feasible(grid),'固定种子小规模直接选边对拍')
    for n,m in ((2,50),(10,10),(25,25),(50,50)):
        for probability in (0.15,0.4,0.75,1.0):
            for repeat in range(3):
                grid=witness_grid(n,m,rng,probability)
                run_case(f'witness_{n}_{m}_{probability}_{repeat}','witness_large',grid,True,'从已知合法单位栅栏生成输入并检查恢复布局')
    for n in (10,25,50):
        grid=[[2]*n for _ in range(n)]
        run_case(f'cycles_{n}','dense_cycles',grid,n%2==0,'满网格二度连接器；奇数阶二分图无二因子')
    grid=[[1]*50 for _ in range(50)]; grid[0][0]=3
    run_case('bipartite_imbalance_50','large_unsat',grid,False,'二分分量两侧度数和不同，度数总和仍为偶数')
    malformed=['','1 2\n0 0\n','2 1\n0 0\n','51 2\n','2 51\n','n 2\n','2 2\n0 0 0\n','2 2\n0 0 0 5\n','2 2\n0 0 0 -1\n','2 2\n0 0 0 9999999999999999999999999\n','2 2\n0 0 0 0 extra\n','2 2\n0 0 0 0 1\n','2.0 2\n','2 2\n0 0 0 +\n']
    for i,text in enumerate(malformed):
        p=subprocess.run([str(program)],input=text,capture_output=True,text=True,encoding='utf-8',timeout=10)
        assert p.returncode==1 and not p.stdout and p.stderr.startswith('输入错误:'),(i,p.stdout,p.stderr)
        (output/'logs'/f'invalid_{i:02d}.json').write_text(json.dumps({'input':text,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr},ensure_ascii=False,indent=2),encoding='utf-8')
    p=subprocess.run([str(program),'--unknown'],input='',capture_output=True,text=True,encoding='utf-8',timeout=10)
    assert p.returncode==1 and not p.stdout and p.stderr
    (output/'logs/unknown_argument.json').write_text(json.dumps({'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr},ensure_ascii=False,indent=2),encoding='utf-8')
    sink=output/'readonly_sink.txt'; sink.write_text('只读输出句柄\n',encoding='utf-8')
    with sink.open('rb') as stream:
        p=subprocess.run([str(program)],input='2 2\n1 1\n1 1\n',stdout=stream,stderr=subprocess.PIPE,text=True,encoding='utf-8',timeout=10)
    assert p.returncode==2,(p.returncode,p.stderr)
    (output/'logs/output_error.json').write_text(json.dumps({'purpose':'标准输出为只读句柄时检查刷新错误','exit_code':p.returncode,'stderr':p.stderr},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'花园用例 {len(rows)} 项及非法输入 {len(malformed)} 项通过；开始 SAT 核心对拍。',flush=True)
    sat=sat_core_tests(driver,output,rng)
    with (output/'cases.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    groups=[]
    for group in dict.fromkeys(row['group'] for row in rows):
        part=[r for r in rows if r['group']==group]
        groups.append({'group':group,'count':len(part),'sat':sum(r['actual'] for r in part),'unsat':sum(not r['actual'] for r in part),'max_wall_ms':max(r['wall_ms'] for r in part),'max_conflicts':max(r['conflicts'] for r in part)})
    sizes=[]
    for n,m in ((2,50),(10,10),(25,25),(50,50)):
        for probability in (0.15,0.4,0.75,1.0):
            part=[r for r in rows if r['name'].startswith(f'witness_{n}_{m}_{probability}_')]
            sizes.append({'rows':n,'columns':m,'probability':probability,'runs':3,'median_wall_ms':statistics.median(r['wall_ms'] for r in part),'max_variables':max(r['variables'] for r in part),'max_conflicts':max(r['conflicts'] for r in part)})
    sources={p.relative_to(PROJECT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (PROJECT/'code').rglob('*') if p.is_file() and p.suffix in ('.c','.h')}
    summary={'seed':SEED,'environment':{'platform':platform.platform(),'python':platform.python_version(),'compiler':subprocess.check_output([args.cc,'--version'],text=True,encoding='utf-8').splitlines()[0]},'garden_cases':len(rows),'invalid_inputs':len(malformed),'error_paths':2,'sat_core':sat,'passed':len(rows)+len(malformed)+2+sat['passed'],'failed':0,'groups':groups,'sizes':sizes,'sources_sha256':sources}
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('garden_cases','invalid_inputs','sat_core','passed','failed')},ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
