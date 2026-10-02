#!/usr/bin/env python3
"""Generate the report and result pages from recorded measurements and outputs."""
import csv
import difflib
import html
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RESULTS=ROOT/'results'
EVIDENCE=ROOT/'evidence'
PAGES=EVIDENCE/'pages'


def read(path):
    return path.read_text(encoding='utf-8',errors='replace')


def table(headers, rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join(
        '| '+' | '.join(map(str,row))+' |\n' for row in rows)


def htable(headers,rows):
    esc=lambda x:html.escape(str(x))
    return '<table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join(
        '<tr>'+''.join('<td>'+esc(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'


def pre(label,content):
    return '<section><h3>'+html.escape(label)+'</h3><pre>'+html.escape(content)+'</pre></section>'


def page(number,title,body):
    css='''body{margin:0;background:#f2f5f7;color:#152534;font:18px/1.6 "Microsoft YaHei",sans-serif}
    main{max-width:1320px;margin:36px auto;background:#fff;padding:32px 38px;border:1px solid #ccd5dd;border-radius:10px}
    h1{font-size:32px;line-height:1.3;margin:12px 0 20px}h2{font-size:24px}h3{font-size:19px;margin-bottom:10px}
    .tag{color:#17654a;font-weight:700}.note{background:#edf4ff;border-left:5px solid #376aa7;padding:14px 18px;margin:18px 0}
    .warn{background:#fff4dc;border-left:5px solid #a87616;padding:14px 18px;margin:18px 0}
    pre{background:#152534;color:#e9f1f7;border-radius:6px;padding:18px;font:16px/1.5 Consolas,"Microsoft YaHei",monospace;white-space:pre-wrap;overflow-wrap:anywhere}
    table{width:100%;border-collapse:collapse;font-size:17px;margin:20px 0}th,td{text-align:left;border-bottom:1px solid #d9e0e5;padding:9px 12px}th{background:#eaf0f5}
    a{color:#225d94}.two{display:grid;grid-template-columns:1fr 1fr;gap:24px}section{min-width:0}
    '''
    PAGES.mkdir(parents=True,exist_ok=True)
    path=PAGES/f'{number:02d}.html'
    path.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+html.escape(title)+
        '</title><style>'+css+'</style><main><div class="tag">ADS PR1 · 实验记录 '+f'{number:02d}'+
        '</div><h1>'+html.escape(title)+'</h1>'+body+
        '</main></html>',encoding='utf-8')
    return path


def main():
    s=json.loads(read(RESULTS/'shakespeare_summary.json'))
    b=json.loads(read(RESULTS/'bonus_summary.json'))
    before=json.loads(read(EVIDENCE/'before_fix/shakespeare_summary.json'))
    review=json.loads(read(RESULTS/'review_after.json'))
    baseline=RESULTS/'shakespeare/theta_0.5'
    docs=list(csv.DictReader((ROOT/'data/shakespeare/documents.csv').open(encoding='utf-8-sig')))
    theta_rows=[[r['theta'],r['stop_words'],r['indexed_stems'],r['positions'],f'{100*r["retained_fraction"]:.2f}%',
                 f'{r["index_bytes"]/1024:.2f}',f'{r["seconds"]:.3f}',f'{r["peak_working_set_bytes"]/2**20:.2f}'] for r in s['theta']]
    th=['θ','停用词干','索引词干','位置数','保留比例','索引 KiB','建索引 s','峰值 WS MiB']
    taus=[]
    for tau in [None,.02,.1,.2,.3,.4,.5]:
        samples=[r for r in s['tau'] if r['tau']==tau]
        taus.append(['不设' if tau is None else str(tau)]+['抑制（0）' if r['blocked'] else str(r['displayed_documents']) for r in samples])
    tah=['τ','caesar（19/42）','antony（6/42）','hamlet（1/42）']
    vocab=[r for r in b['original_backend'] if r['mode']=='vocabulary']
    vrows=[[r['terms'],r['documents'],f'{r["seconds"]:.3f}',f'{r["peak_working_set_bytes"]/2**20:.2f}',
             f'{r["index_bytes"]/2**20:.2f}',f'{r["query_seconds"]:.3f}'] for r in vocab]
    vh=['不同词干 V','逻辑文档 N','构建 s','峰值 WS MiB','磁盘 MiB','加载并查询 s']
    common=[r for r in b['original_backend'] if r['mode']=='common']
    crows=[]
    previous=None
    for r in common:
        crows.append([r['n'],f'{r["insert_cpu_seconds"]:.3f}',
                      '—' if previous is None else f'{r["insert_cpu_seconds"]/previous:.2f}×'])
        previous=r['insert_cpu_seconds']
    demos=b['disk_backend_demo']
    drows=[[r['logical_documents'],r['distinct_terms'],f'{r["build_seconds"]:.3f}',
            f'{r["peak_working_set_bytes"]/2**20:.2f}',f'{r["database_bytes"]/2**20:.2f}',
            'PASS' if r['passed'] else 'FAIL'] for r in demos]
    dh=['逻辑文档 N','不同词干 V','构建 s','进程峰值 WS MiB','数据库 MiB','检查']
    top=(RESULTS/'word_statistics.csv').read_text(encoding='utf-8-sig').splitlines()[:13]
    now=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    pages=[]
    pages.append(page(1,'全集语料准备与来源核验',
        '<p>文档粒度：每部戏剧 / 每个诗歌集合 = 一个文档；十四行诗按目录顺序合并。</p>'+htable(
            ['核验项','实测结果'],[['MIT 目录条目','42（37 戏剧 + 5 诗歌集合）'],['十四行诗','154 首，均已提取'],
            ['ASCII 词形种数',s['corpus']['raw_word_types']],['词干种数',s['corpus']['stems']],['原始 token 总数',s['corpus']['tokens']],
            ['原代码 commit',s['corpus']['source_commit']],['MIT 镜像 commit',s['corpus']['mirror_commit']]])+
        '<div class="note">去除 HTML 标签、网页导航和广告；保留场次标题、角色名与舞台说明。源 HTML 与 SHA-256 清单均保留。elegy.html 的缺失 &gt; 已作确定性标签修复。</div>'+
        htable(['doc_id','作品','tokens'],[[d['doc_id'],d['title'],d['words']] for d in docs if int(d['doc_id']) in [0,29,30,37,38,39,40,41]])+
        '<p>来源：<a href="https://shakespeare.mit.edu/">MIT 全集网站</a> · <a href="https://github.com/TheMITTech/shakespeare">该网站公开镜像</a></p>'))
    pages.append(page(2,'编译、词频统计与完整建索引',
        pre('编译命令（四个程序均零告警）','gcc -std=c99 -O2 -Wall -Wextra -Wpedantic code/index_gen.c code/stem.c -lm -o bin/index_gen.exe\n'+
            'gcc -std=c99 -O2 -Wall -Wextra -Wpedantic code/query.c code/stem.c -lm -o bin/query.exe\n'+
            '另外编译 stem_list 和 roundtrip；完整命令保存在 build_*.run.json。')+
        pre('θ=0.5 完整建索引原始 stderr',read(RESULTS/'logs/initial_full_build.stderr.txt'))+
        pre('词频最高的词干（完整表见 word_statistics.csv）','\n'.join(top))+
        '<div class="note">停用词判据：df/N &gt; θ；N=42。θ=0.5 删除 1,780 个词干，保留 131,136 个位置。查询位置从 0 开始，且仍按完整原文计数。</div>'))
    pages.append(page(3,'索引正确性对照检验',
        '<p>Python 重新切词、统计 df/cf、推导 stoplist、解析二进制索引，再逐词逐文档逐位置与 C 输出比较。词干算法复用原 C stemmer，因此不属于词干算法的独立验证。</p>'+
        pre('实际复测控制台（节选）','\n'.join(read(RESULTS/'extended_console.txt').splitlines()[:11]+read(RESULTS/'extended_console.txt').splitlines()[-18:]))+
        pre('补充回归控制台（节选）','\n'.join(read(RESULTS/'review_console.txt').splitlines()[-7:]))+
        htable(['一致性检查','实测结果'],[['初次 vs 重复建索引 SHA-256',s['index_sha256']],['load → save','逐字节相同'],['损坏索引','截断/版本错误/垃圾/尾部字节/不存在文档引用均拒绝']])+
        '<div class="note">全集 '+str(s['passed'])+' 项检查与补充 '+str(review['passed'])+' 项回归通过。五组 θ 的词条集、文档表和位置列表均匹配，80 组随机 AND／短语查询与枚举结果一致。</div>'))
    pages.append(page(4,'短语查询缺陷及修复对照',
        '<p>原程序按 tf 排序短语词数组，随后仍用 start+i 验证位置，改变了短语含义。修复：保持词序，仅选择 anchor 下标，起点 = anchor 位置 − anchor 下标。</p>'+
        '<div class="two">'+pre('修复前：真实莎士比亚短语',read(EVIDENCE/'before_fix/PHRASE_et_tu_brute.txt'))+
        pre('修复后：同一索引、同一查询',read(RESULTS/'queries/PHRASE_et_tu_brute.txt'))+'</div>'+
        '<div class="two">'+pre('修复前：alpha beta 原文起点应为 0',read(EVIDENCE/'before_fix/phrase_order_regression.txt'))+
        pre('修复后：恢复正确起点',read(RESULTS/'queries/phrase_order_regression.txt'))+'</div>'+
        '<div class="note">另一问题：最后一篇文档没有 postings 时被拒绝。改为逐组校验 posting doc_id 属于文档表，允许空文档和全停用词文档。修复前后差异见 source_changes.patch。</div>'))
    pages.append(page(5,'θ / τ 阈值敏感性实验',
        '<p>θ 决定建索引时永久剔除的词；τ 决定查询时是否展示结果列表。条件均为严格大于（&gt;），相等不抑制。</p>'+
        htable(th,theta_rows)+htable(tah,taus)+
        '<div class="note">单词查询输出一行一个位置。本表先按 doc_id 去重：caesar 有 602 个位置，却只命中 19 篇文档。τ 抑制展示后并不等于真实匹配数为零。</div>'+
        pre('含停用词的短语为何查不到',read(RESULTS/'queries/PHRASE_to_be_or_not_to_be.txt'))))
    pages.append(page(6,'Bonus：原 C 后端的规模与性能实测',
        '<div class="warn">以下是逻辑文档 ID / 已归一词干的索引后端压力测试，未创建 50 万个实体文件，未运行 4 亿不同词。</div>'+
        htable(vh,vrows)+htable(['同一词的位置数','插入 CPU s','相邻规模时间倍率'],crows)+
        '<p>每次插入从位置链表头扫描。位置数翻倍时，插入时间近似增至 4 倍，符合 ∑ i = O(tf²)。加载也复用该插入入口。</p>'+
        pre('实际 Windows 命令行上限实验',read(RESULTS/'logs/bonus_cli_limit.json'))+
        '<div class="note">50 万个空逻辑文档的索引为 2,000,064 B，修复后可加载；这验证 doc_id 范围，并不验证海量实体文件的枚举或 I/O。</div>'))
    pages.append(page(7,'Bonus：固定缓存的外存原型验证',
        '<p>独立 Python + SQLite B-tree 演示程序；不属于原 C 后端，也不兼容其 index.bin。词典和位置表存盘，页缓存预算固定 8 MiB，每批最多 2,000 个位置。</p>'+
        htable(dh,drows)+pre('最大档实际重启查询结果',json.dumps({k:demos[-1][k] for k in ['logical_documents','distinct_terms','word_hits','phrase_hits','threshold_suppressed','integrity','passed']},ensure_ascii=False,indent=2))+
        '<div class="warn">实测达到 50 万逻辑文档 / 100 万不同词。原型使用每词出现一次的合成分布；尚不能据此证明一般语料或 4 亿词规模。固定缓存预算也不等于整个进程严格恒定内存。</div>'))
    estimate=b['estimate']; types=b['types']
    pages.append(page(8,'Bonus 结论：结构下限与 4 亿词估算',
        htable(['依据','结果','性质'],[['sizeof(Posting), sizeof(Position), sizeof(long)',f'{types["posting"]} B / {types["position"]} B / {types["long"]} B','本机实测'],
            ['4 亿词，平均字符串 16 B，至少每词一个位置',f'{estimate["c_payload_bytes"]/10**9:.3f} GB（{estimate["c_payload_bytes"]/2**30:.2f} GiB）','条件估算；不含分配器/排序/统计数组'],
            ['v1 词典固定元数据 18 B × 4 亿','7.2 GB，尚未计词干字符串','由格式推导'],
            ['ftell/fseek 使用 32-bit long',f'LONG_MAX = {types["long_max"]}','本机结构限制'],
            ['固定哈希桶平均装填 V/hashsize',f'{estimate["c_hash_average_chain"]:.2f} 词/桶','均匀散列情形的规模估算']])+
        '<div class="note">当前 C 实现不能直接支持题目完整 Bonus 规模。50 万 doc_id 能表示；限制来自一次性内存驻留、链表插入、逐词磁盘 seek、命令行接口及 Windows 文件偏移。</div>'+
        '<p>扩展路线：清单/目录流式输入 → 按内存预算分块 → 外部归并统计全局 df → 剔除停用词 → 64-bit 文件偏移 + 磁盘词典 → 按需读取 postings。百万词外存原型是部分验证，4 亿词仍需专门硬件与实测。</p>'))
    gallery='<h2>截图步骤索引</h2>'+''.join('<p><a href="pages/'+p.name+'">'+p.stem+' · '+
        html.escape(title)+'</a> · <a href="screenshots/'+p.stem+'.png">PNG 截图</a></p>' for p,title in zip(pages,[
        '数据来源与语料准备','编译与建索引','独立对拍','错误复现与修复','阈值实验','原 C 后端压力测试','外存原型','规模估算']))
    (EVIDENCE/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>PR1 实验截图索引</title><body style="font:20px/1.8 Microsoft YaHei;padding:30px"><h1>PR1 实验记录与截图</h1><p>页面由真实结果生成；PNG 是这些日志展示页的浏览器截图。</p>'+gallery+'</body>',encoding='utf-8')
    diff=''
    for name in ['query.c','index.h','index_gen.c']:
        diff+=''.join(difflib.unified_diff(read(EVIDENCE/'before_fix'/name).splitlines(True),read(ROOT/'code'/name).splitlines(True),fromfile='a/pr1/code/'+name,tofile='b/pr1/code/'+name))
    (EVIDENCE/'source_changes.patch').write_text(diff,encoding='utf-8')
    # Provenance map: screenshots are regeneratable views, not replacements for logs.
    provenance=dict(generated_at_shanghai=now,source_commit=s['corpus']['source_commit'],mirror_commit=s['corpus']['mirror_commit'],
        screenshot_kind='browser screenshot of pages generated from actual logs',screenshots=[f'screenshots/{p.stem}.png' for p in pages],
        checks_final=dict(passed=s['passed'],failed=s['failed']),checks_before=dict(passed=before['passed'],failed=before['failed']),
        timing_caveat='single runs, concurrent activity may affect time; threshold 0.5 initial run includes token dump; others do not',
        bonus_caveat='500k logical doc IDs, NOT physical files; 1m distinct terms measured, 400m only estimated')
    (EVIDENCE/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    queryrows=[[r['query'],r['kind'],r['documents'],r.get('positions','—')] for r in s['queries']]
    old_review=json.loads(read(RESULTS/'review_before.json'))
    qrows=[[r['query'],r['kind'],r['documents'],r.get('positions','—')] for r in s['queries']]
    corpus=s['corpus']
    report=f'''# Roll Your Own Mini Search Engine 实验报告

## Chapter 1 问题描述

### 1.1 实验目标

本实验以 MIT 网站提供的莎士比亚全集为检索语料，实现词频统计、停用词识别、词干化倒排索引和查询处理，并分析阈值变化对索引及查询结果的影响。Bonus 部分考察 500,000 个文件与 400,000,000 个不同词条件下的可扩展性。

每个文本文件对应一个文档。程序按输入文件顺序分配从 0 开始的文档 ID，并返回单词或短语所在的文档及位置。除题目要求外，程序支持多查询单元的 AND 运算。

### 1.2 语料及统计口径

语料取自 MIT 目录的 42 个条目，包括 37 部戏剧与 5 个诗歌集合；154 首十四行诗合并为一个文档。源网站及其公开镜像见参考文献 [1]。镜像版本为 `{corpus['mirror_commit']}`。

预处理删除 HTML 标签、网页导航和广告，保留场次标题、角色名及舞台说明。戏剧从首个 `<h3>` 标签开始提取，诗歌提取正文可见文本。`elegy.html` 中的 `</TITLE` 标签缺少结束符，对该标签补全后提取正文，文本内容未作修改。

采用 ASCII 字母与数字的连续段作为 token，并转换为小写。撇号及连字符作为分隔符，例如 `don't` 分为 `don` 和 `t`。一个词在文档中的位置按完整 token 序列编号，起始位置为 0；删除停用词后保留原位置编号。

全集共有 **{corpus['tokens']:,} 个 token、{corpus['raw_word_types']:,} 种原词形和 {corpus['stems']:,} 个词干**。其中，cf 表示词干的总出现次数，df 表示包含该词干的不同文档数，N 表示全部文档数。空文档也计入 N。

原始 HTML、提取文本、文档清单及 SHA-256 校验值位于 `test_data.zip` 的 `data/shakespeare/` 目录。各文档 ID 与作品名的对应关系见 `documents.csv`。

## Chapter 2 数据结构与算法

### 2.1 词频统计与停用词

统计与建索引采用两遍扫描。第一遍对全部词执行 Porter 词干化，累计 cf、df，并按下式确定停用词：

```text
df / N > θ
```

默认 θ=0.5。高文档频率的词在文档间区分能力较低，因此用文档覆盖率划分 noisy words。该判据具有可重复性，但不等同于语义判断；例如 `love` 也可能因覆盖文档较多而被过滤。阈值实验用于考察索引大小与可检索内容之间的取舍。

第一遍生成 `stoplist.txt` 后释放统计索引；第二遍重新读取语料，剔除停用词并写出位置倒排索引。`--count-only` 只执行统计阶段，不生成索引文件。词干化在建索引和查询时各执行一次。词干模块采用文献 [2] 的 C 实现，许可及版权声明附于 `code/LICENSE-stmr.txt`。

### 2.2 内存结构与文件格式

词典采用 1,000,007 个哈希桶，以链地址法处理冲突。每个词条保存词干、tf 和位置链表；位置节点记录 `(doc_id, pos)`，按文档 ID 与位置升序排列。文档表为升序、无重复的 ID 数组。

`index.bin` 使用小端定长整数及 LEB128 变长编码。文件由连续的头部、文档表、词典和位置段组成。

| 部分 | 保存内容 |
| --- | --- |
| 头部（64 B） | 魔数、版本、文档数、词条数、位置总数及三段偏移 |
| 文档表 | N 个 u32 文档 ID |
| 词典 | u32 df、u32 tf、u64 文件绝对偏移、u16 词干长度及词干字节 |
| 位置段 | 文档增量、文档内出现次数与位置增量，采用 LEB128 编码 |

加载器检查魔数、版本、段边界、词典与文档表顺序、df/tf、累计位置数和文档引用，并在增量累加前检查整数范围。该格式未设置校验和，因此无法识别所有仍满足结构约束的内容改动。构建结果先写入临时文件，再替换目标索引；Windows 使用 `MoveFileExA`，POSIX 使用 `rename`。

### 2.3 查询处理

查询采用与建索引相同的分词与词干化规则。单词查询返回 df、tf 和命中位置；AND 查询对各单元的升序文档列表求交。

短语查询先求候选文档交集，再选择 tf 最小词的原始下标 anchor 作为锚点。候选起点为该词的命中位置减去 anchor，并逐词验证 `start+i` 是否存在。该过程保持原短语词序，允许重复词。

命令行中的多个参数表示 AND；单个参数中的多个 token 表示连续短语。`test.txt` 的普通行表示 AND，`phrase:` 行表示短语。每次查询结果写入 `output.txt`。查询最多包含 32 个单元，每个短语最多 16 个词；超出限制的输入返回错误。

查询阈值 τ 满足下式时，程序保留统计信息并抑制完整结果列表：

```text
df / N > τ
```

θ 与 τ 均采用严格大于条件，相等时不触发过滤或抑制。θ 决定索引中的词条，τ 决定查询结果的展示范围。已删除停用词的位置无法由当前索引恢复，因此包含这些词的精确短语不能直接检索。

### 2.4 复杂度

若词干数为 V、哈希桶数为 M，均匀散列下平均链长约为 V/M。当前位置链采用从头扫描的有序插入；一个词的 tf 个位置按升序插入时，遍历次数为 `tf(tf−1)/2`，最坏时间为 O(tf²)。构建成本还包含文件读取、词干化、哈希查找与落盘。

AND 文档列表求交的时间与参与列表的总长度相关。短语查询增加了位置连续性验证。当前查询程序全量加载词典与位置链，因此单次查询的成本还包含完整索引加载；该实现适用于本次语料，但存在明显的规模限制。

## Chapter 3 测试与结果分析

### 3.1 环境与验证方法

实验日期为 2026 年 10 月 2 日。运行环境为 Windows 11、gcc 15.2.0（MinGW-w64）和 Python 3.12。使用 `-std=c99 -O2 -Wall -Wextra -Wpedantic` 编译，四个全集测试程序均无编译告警。

Python 使用独立的正则分词，逐项核对 C 输出的全部 {corpus['tokens']:,} 条原始 token；随后按词干聚合 `(doc_id,pos)`，推导 cf、df 和停用词集合，并独立解析二进制索引。对五组 θ，文档表、词条集合及全部位置列表均与参考结果相等。词干处理复用了原 C 实现，该对照不构成 Porter 算法本身的独立验证。

全集测试共 **{s['passed']} 项通过、{s['failed']} 项失败**。重复构建与 load→save 往返的索引逐字节一致。θ=0.5 的 SHA-256 为：

```text
{s['index_sha256']}
```

补充回归共 **{review['passed']} 项通过、{review['failed']} 项失败**，覆盖标点归一化、阈值合法性、查询长度、异常索引及分配失败。另以固定随机种子 793 生成 13 篇文档，对 80 组 AND／短语查询与独立枚举结果进行比较，全部一致。分配失败测试针对本次 64 位 Windows ABI，通过链接器包装 malloc，验证位置节点分配失败时终止构建。

### 3.2 查询结果

{table(['查询','方式','命中文档数','位置／短语起点数'],qrows)}
`et tu brute` 命中 Julius Caesar（doc_id=30），起点为 10014。`to be or not to be` 在原文中出现一次，但其全部词都被 θ=0.5 的停用词规则删除，故过滤后的索引返回零匹配。该结果体现了停用词规则对短语检索的影响。

### 3.3 缺陷定位与修正

初次全集测试为 67 项通过、2 项失败。短语词数组按 tf 排序后，原程序仍按 `start+i` 检查位置，导致查询顺序改变。将排序改为保留词序的锚点选择后，真实短语及最小反例 `alpha beta alpha alpha gamma` 的起点均正确。

加载器原先要求最大 posting 文档 ID 等于文档表最后一个 ID，因而拒绝尾部空文档。现改为检查每个 posting 引用是否属于文档表，允许文档没有索引词。此外，普通文件查询改按 AND 处理，Windows 连续重建改用可替换已有目标的文件接口。

在后续 {review['passed']} 项补充回归中，修正前结果为 {old_review['passed']} 项通过、{old_review['failed']} 项失败，修正后全部通过。主要修改为：统一语料与查询分词；拒绝空值、NaN 及超范围阈值；拒绝过长查询行；补全单词结果的文档数组；验证词典及文档表的严格顺序；在增量累加前检查整数溢出；使用扩展整数计算 INT_MAX 位置的首个增量；位置节点分配失败时终止构建，防止成功保存不完整索引。

两阶段检查数量不同，分别对应不同的测试集合。修复记录、源码差异及修正前结果保存在压缩包的 `evidence/` 和 `results/review_*.json` 中。

### 3.4 停用词阈值 θ

{table(th,theta_rows)}
θ 增大时，停用词减少，索引词条、位置数与文件体积增加。默认 θ=0.5 删除 1,780 个词干，保留 13,206 个词干与 131,136 个位置，索引大小为 663,434 B。被删除词干约占词表的 11.88%，覆盖 86.29% 的出现位置，说明常见词集中占据了较多文本位置。

### 3.5 查询阈值 τ

{table(tah,taus)}
表中数值为去重后的文档数。`caesar`、`antony` 和 `hamlet` 分别命中 19、6、1 篇文档；对应位置数为 602、513、470。τ=0.1 时前两者被抑制，τ=0.2 时 `antony` 恢复展示，τ=0.5 时三者均展示。三个 `τ=df/N` 边界查询均通过。

性能数据为本机单次墙钟测量，受后台任务影响。θ=0.5 初次构建额外输出 token dump，其他 θ 未输出；因此各档耗时不完全对应相同的 I/O 工作量。内存记录为以 10 ms 间隔读取的 Windows 峰值 working set，不等同于严格 RSS 上限。

## Chapter 4 Bonus：规模实验与可扩展性

### 4.1 原 C 后端

通过 `bonus_probe.c` 直接调用现有索引模块，生成已归一化的词干及逻辑文档 ID。词典规模测试中，每个不同词出现一次。

{table(vh,vrows)}
最大档为 500,000 个逻辑文档、1,000,000 个不同词。索引保存后由查询程序重新加载，各档首词与末词的位置均符合预期；最大档末词命中 `(499999,1)`。该测试未执行实体文件枚举、原文分词与停用词统计。另构建 500,000 个空逻辑文档的索引，大小为 2,000,064 B，加载成功。

{table(['同一词的 tf','插入 CPU s','相邻档时间倍率'],crows)}
高频词的位置插入耗时随 tf 增长呈明显的二次方趋势，与从头扫描链表的复杂度一致。加载器复用该插入接口，也存在同类退化。

### 4.2 外存原型

独立的 `bonus_disk_demo.py` 使用 SQLite B-tree 保存词典和位置表，页缓存预算为 8 MiB，每批最多 2,000 个位置。保存后关闭并重新打开数据库，验证词条数量、文档数量、数据库一致性、单词查询、连续短语及阈值抑制。

{table(dh,drows)}
最大档中，单词命中 `(499999,1)`，短语命中 `(499999,0)`。该原型与原 C 文件格式独立，不兼容 `index.bin`；测试数据采用每词出现一次的合成分布。固定页缓存控制了部分工作内存，但不意味着整个进程的内存严格恒定。

### 4.3 四亿不同词的资源估算

本机测得 `sizeof(Posting)=32 B`、`sizeof(Position)=16 B`、`sizeof(long)=4 B`。假设每个不同词至少有一个位置，且词干字符串连同结束符平均占 16 B，则 C 索引载荷估算为：

```text
8,000,072 + 500,000 × 4 + 400,000,000 × (32 + 16 + 16)
= 25,610,000,072 B ≈ 25.610 GB ≈ 23.85 GiB
```

该估算计入文档表的最低载荷，不含其预留容量、分配器开销、碎片、统计数组、排序数组及重复位置。现有词典每条固定元数据占 18 B，四亿条仅元数据即占 7.2 GB，尚未计入字符串与位置段。固定哈希桶下平均链长约为 400，查询常数也将显著增大。

当前加载器使用 `ftell/fseek` 与 long 偏移，本机 `LONG_MAX=2,147,483,647`，无法可靠处理超过约 2 GiB 的索引。命令行接口也存在限制：将 500,000 个文件名作为参数时，实际进程创建返回 WinError 206，程序尚未开始读取文件。该测试未创建实体文件。

因此，**当前 C 实现不能直接支持题目给出的完整 Bonus 规模**。文档 ID 的表示范围足够，但内存驻留、链表插入、全量加载、命令行长度及文件偏移均构成约束。

### 4.4 改进方向

输入接口可改为目录或文件清单，逐个读取文档。统计阶段应按内存预算分块，再外部归并得到全局 df；确定停用词后，再对保留词构建分块位置索引。SPIMI／BSBI 分块与多路归并可减少一次性内存需求 [3]。

词典可采用磁盘 B-tree 或分块有序文件，文件访问改为 64 位偏移，查询时只读取目标词的位置列表。高频词的位置构建可采用尾指针或顺序缓冲，避免重复遍历。SQLite 原型验证了将词典与位置存盘的可行性，但未验证四亿不同词、五十万实体文件或一般高频语料；完整规模仍需进一步实验。

## Chapter 5 复现与提交文件

提交内容为 `code/`、本报告及 `test_data.zip`。将压缩包解压到本报告所在目录后，会得到 `data/`、`results/` 和 `evidence/`。压缩包含语料、结果表、原始日志、源码修复记录及八张实验截图，不含可执行文件、数据库和临时压力索引。

从 `pr1` 目录编译并查询：

```powershell
Expand-Archive -LiteralPath test_data.zip -DestinationPath . -Force
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic code/index_gen.c code/stem.c -lm -o code/index_gen.exe
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic code/query.c code/stem.c -lm -o code/query.exe
$corpus = Get-ChildItem data/shakespeare/corpus/*.txt | Sort-Object Name
Set-Location code
./index_gen.exe --theta=0.5 $corpus.FullName
./query.exe 'et tu brute'
Get-Content output.txt
```

完整测试入口为 `code/tests/run_lab.ps1`，或依次执行 `run_extended.py`、`review_regression.py` 与 `run_bonus.py`。Python 脚本仅使用标准库；截图重建需要 Playwright 与 Edge。

实验图 01—08 位于 `evidence/screenshots/`，依次对应语料准备、编译与建索引、正确性检查、修复对照、阈值实验、C 后端压力实验、外存原型和资源估算。图中数据来自已保存的运行日志，图片为结果展示页的浏览器截图。

## 参考文献

[1] The Complete Works of William Shakespeare. MIT. https://shakespeare.mit.edu/；网站源码镜像：https://github.com/TheMITTech/shakespeare。

[2] Porter M F. An algorithm for suffix stripping. Program, 1980, 14(3): 130–137. C 实现：https://github.com/wooorm/stmr.c。

[3] Manning C D, Raghavan P, Schütze H. Introduction to Information Retrieval. Cambridge University Press, 2008. https://nlp.stanford.edu/IR-book/。

[4] SQLite. PRAGMA Statements：cache_size、temp_store. https://www.sqlite.org/pragma.html。
'''
    (ROOT/'documentation.md').write_text(report,encoding='utf-8')
    (EVIDENCE/'截图说明.md').write_text('# 实验图索引\n\n图 01—08 为测试结果展示页的浏览器截图。测量、命令及输出分别保存在 results/ 中。\n\n'+
        table(['编号','内容'],[[f'{i:02d}.png',name] for i,name in enumerate([
        '语料来源与预处理','编译、词频与建索引','独立正确性检查','缺陷定位及修复对照',
        'θ 与 τ 阈值实验','原 C 后端规模实验','SQLite 外存原型','四亿词资源估算'],1)]),encoding='utf-8')
    print('Report and eight result pages generated')


if __name__=='__main__':
    main()
