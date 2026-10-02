#!/usr/bin/env python3
"""Build report material and browser evidence pages from actual JSON/raw logs.

Screenshots are captured separately from these pages; this script never fabricates
a terminal screenshot. Tables retain measured/estimated/logical-document labels.
"""
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
    return '<h3>'+html.escape(label)+'</h3><pre>'+html.escape(content)+'</pre>'


def page(number,title,body):
    css='''body{margin:0;background:#f2f5f7;color:#152534;font:18px/1.6 "Microsoft YaHei",sans-serif}
    main{max-width:1320px;margin:36px auto;background:#fff;padding:32px 38px;border:1px solid #ccd5dd;border-radius:10px}
    h1{font-size:32px;line-height:1.3;margin:12px 0 20px}h2{font-size:24px}h3{font-size:19px;margin-bottom:10px}
    .tag{color:#17654a;font-weight:700}.note{background:#edf4ff;border-left:5px solid #376aa7;padding:14px 18px;margin:18px 0}
    .warn{background:#fff4dc;border-left:5px solid #a87616;padding:14px 18px;margin:18px 0}
    pre{background:#152534;color:#e9f1f7;border-radius:6px;padding:18px;font:16px/1.5 Consolas,"Microsoft YaHei",monospace;white-space:pre-wrap;overflow-wrap:anywhere}
    table{width:100%;border-collapse:collapse;font-size:17px;margin:20px 0}th,td{text-align:left;border-bottom:1px solid #d9e0e5;padding:9px 12px}th{background:#eaf0f5}
    a{color:#225d94}.footer{font-size:14px;color:#586777;margin-top:24px}.two{display:grid;grid-template-columns:1fr 1fr;gap:24px}
    '''
    PAGES.mkdir(parents=True,exist_ok=True)
    path=PAGES/f'{number:02d}.html'
    path.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+html.escape(title)+
        '</title><style>'+css+'</style><main><div class="tag">ADS PR1 · 实验记录 '+f'{number:02d}'+
        '</div><h1>'+html.escape(title)+'</h1>'+body+
        '<div class="footer">真实测试日志展示页 · 截图由浏览器实拍 · 非终端原屏截取。原始数据与命令见 results/logs/*.run.json、*.txt。</div></main></html>',encoding='utf-8')
    return path


def main():
    s=json.loads(read(RESULTS/'shakespeare_summary.json'))
    b=json.loads(read(RESULTS/'bonus_summary.json'))
    before=json.loads(read(EVIDENCE/'before_fix/shakespeare_summary.json'))
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
    pages.append(page(3,'独立对拍与修复后测试结果',
        '<p>Python 重新切词、统计 df/cf、推导 stoplist、解析二进制索引，再逐词逐文档逐位置与 C 输出比较。词干算法复用原 C stemmer，因此不属于词干算法的独立验证。</p>'+
        pre('实际复测控制台（节选）','\n'.join(read(RESULTS/'extended_console.txt').splitlines()[:11]+read(RESULTS/'extended_console.txt').splitlines()[-18:]))+
        htable(['一致性检查','实测结果'],[['初次 vs 重复建索引 SHA-256',s['index_sha256']],['load → save','逐字节相同'],['损坏索引','截断/版本错误/垃圾/尾部字节/不存在文档引用均拒绝']])+
        '<div class="note">最终 '+str(s['passed'])+' 项检查通过，'+str(s['failed'])+' 项失败。所有五组 θ 的词条集、文档表和位置列表均完全匹配。</div>'))
    pages.append(page(4,'发现问题 → 最小复现 → 修复验证',
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
        '<div class="note">答案：当前 C 实现不能直接支持题目完整 Bonus 规模。50 万 doc_id 能表示；限制来自一次性内存驻留、链表插入、逐词磁盘 seek、命令行接口及 Windows 文件偏移。</div>'+
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
    report=f'''# ADS PR1：莎士比亚全集测试、Bonus 与实验过程记录

本文件由真实测试 JSON / 控制台日志生成，生成时间：{now}（北京时间）。这份素材补充已有代码与历史合成语料报告，可据此编写实验报告的测试、分析和 Bonus 章节。

## 1. 数据来源与预处理记录

- 当前作业仓库：<https://github.com/nothing793/adsproject>，main 基线 commit `{s['corpus']['source_commit']}`。与最初参考仓库 commit `{s['corpus']['original_reference_commit']}` 的五个主源码在归一化换行后完全一致，已有全集构建数据适用。核验见 `evidence/repository_baseline.json`。
- 题目指定网站：<https://shakespeare.mit.edu/>；使用该网站公开 Git 镜像 <https://github.com/TheMITTech/shakespeare>，commit `{s['corpus']['mirror_commit']}`，完整 HTML 保存在 `data/shakespeare/html/`。
- 以网站目录为全集范围：37 部戏剧 + 5 个诗歌集合，共 42 篇文档；154 首十四行诗合并为一篇。42 是网站条目数，不是戏剧部数。
- 从戏剧首个 `<h3>` 开始取可见文本；诗歌取正文可见文本。去掉 HTML 标签、导航与广告，保留场次标题、角色名和舞台说明。
- 预处理第一次在 `elegy.html` 得到空正文；原因是原 HTML 的 `</TITLE` 缺少 `>`，解析器把后续内容当作 head。给该标签补 `>` 后，全部 42 篇均有正文。修复只改标签，不改文学内容。
- `data/shakespeare/manifest.json` 记录源 URL、HTML SHA-256、文本 SHA-256、字数；`documents.csv` 给出 doc_id 与作品名称。顺序固定，doc_id 从 0 开始。
- C tokenizer 使用 ASCII 字母/数字分词、转小写，位置从 0 开始。撇号和连字符是分隔符，停用词删除后位置仍保持原文编号。

本次 token 总数 **{s['corpus']['tokens']:,}**，词干化前词形数 **{s['corpus']['raw_word_types']:,}**，词干数 **{s['corpus']['stems']:,}**。

截图：[01 数据准备](evidence/screenshots/01.png)。源文本可以自行打开抽查；如 Hamlet 为 doc_id=29，Julius Caesar 为 doc_id=30。

## 2. 环境、编译和原始命令

环境：{s['environment']['platform']}；{s['environment']['gcc']}；Python 3.12。

```powershell
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic code/index_gen.c code/stem.c -lm -o bin/index_gen.exe
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic code/query.c code/stem.c -lm -o bin/query.exe
```

实际脚本还编译 `stem_list`、`roundtrip` 和 `bonus_probe`，均零告警。建索引需显式传入所有语料文件；通配符展开由测试脚本负责。每个 θ 在不同目录运行，独立保存索引和 stoplist；Windows 覆盖已有索引问题已修复并回归验证。

`query` 从当前工作目录读取 `index.bin` 和 `stoplist.txt`，每次覆盖 `output.txt`。本次脚本把每次查询结果另存为 `results/queries/*.txt`。完整参数、cwd、退出码、时间、峰值 working set 在 `results/logs/*.run.json`，stdout / stderr 原文同名保存。

```text
{read(RESULTS/'logs/initial_full_build.stderr.txt').strip()}
```

θ=0.5：索引 **663,434 B（647.88 KiB）**，保留 **131,136** 个位置，比例 **13.71%**，两遍扫描均 **0 positions dropped**。

截图：[02 编译、词频与建索引](evidence/screenshots/02.png)。完整词频表：`results/word_statistics.csv`，按 cf 降序，包括每个词干的 cf、df、df/N。

## 3. 正确性测试方法与结果

测试参考答案不靠“查询输出看起来合理”：Python 对全部文本独立用正则分词，核对 C 的全部 956,647 条 token，然后按词干聚合 `(doc_id,pos)`，统计 cf/df，独立推导 stoplist，并按二进制格式解析 `index.bin`。对五组 θ，文档表、词条集合和全部位置列表逐项相等。词干处理复用原 C `stem_list`，因此验证范围不包含 Porter 算法本身的独立正确性。

进一步测试：同词大小写、单词位置列表、AND 文档交集、短语连续位置、停用词解释、τ 边界、空文档、尾部空文档、N=0 索引和损坏文件。重复构建与 load→save 往返均逐字节相同，θ=0.5 的 SHA-256 为：

```text
{s['index_sha256']}
```

修复前测试为 **{before['passed']} PASS / {before['failed']} FAIL**；修复后为 **{s['passed']} PASS / {s['failed']} FAIL**。前后检查数量不同，因为修复时增加了专门的回归与文档引用校验测试；不能把新增检查误写为“同一套测试增加了通过项”。

{table(['查询','方式','命中文档数','位置/短语起点数'],queryrows)}

截图：[03 对拍与最终结果](evidence/screenshots/03.png)。原始完整控制台：`results/extended_console.txt`；逐项判断在 `results/shakespeare_summary.json`。

## 4. 真实问题定位与修复痕迹

### 4.1 短语重排导致错查

原 `run_phrase_query()` 把词数组按 tf 排序，然后继续用 `start+i` 检查相邻位置。这使数组顺序变成频率顺序，原短语顺序丢失。

- 真实数据：`et tu brute` 修复前返回 0，独立枚举预期为 `(30,10014)`。
- 最小输入：`alpha beta alpha alpha gamma`；`alpha` 比 `beta` 多，原排序变成 `beta alpha`，查询 `alpha beta` 错误返回起点 1，预期起点为 0。
- 修复：保留词序，以最小 tf 的词下标 `anchor` 作锚点；候选起点为 `positions[anchor][a]-anchor`，仍按原下标 i 验证 `start+i`。
- 复测：`et tu brute` 返回 doc 30 / pos 10014，`alpha beta` 返回 doc 0 / pos 0；反向、重复词、不命中短语回归均通过。

### 4.2 合法空文档被判为坏索引

原加载器要求最大 posting 的 doc_id 等于文档表最后一个 ID。最后一篇文档为空或全是停用词时，不会有 posting，这个等式不成立。50 万个空逻辑文档的合法索引也因此被拒绝。

修复为逐组二分验证 posting 的 doc_id 确实属于文档表；允许文档没有索引词。尾部空文档、50 万空逻辑文档加载通过，posting 引用不存在的文档仍被拒绝。索引文件格式保持 v1。

修复前源码和失败结果在 `evidence/before_fix/`；精确差异在 `evidence/source_changes.patch`。截图：[04 问题复现和修复](evidence/screenshots/04.png)。

### 4.3 文件输入和 Windows 重建索引

原 `test.txt` 多词行说明是 AND，实际却把整行当一个短语单元。改为逐词构成查询单元；只有 `phrase:` 行作为短语。用 `alpha gamma`（文档中都有但不连续）、`phrase: alpha beta` 和单词行回归，均通过。`code/test.txt` 已补上真实查询样例。

原 Windows CRT `rename()` 无法替换旧 `index.bin`，第二次构建失败。Windows 改用 `MoveFileExA(REPLACE_EXISTING | WRITE_THROUGH)`，POSIX 继续 `rename()`；同一目录连续重建后索引 SHA-256 相同。Linux 分支保持原实现，本次环境只实测 Windows。

原 `tests/sweep.py` 未给 index_gen 传语料文件，且将位置行数当文档数；该入口现改为调用独立校验后的全集测试，再按去重文档数打印 θ/τ 表。原脚本保存在 `evidence/before_fix/sweep.py` 供过程对照。

## 5. θ 与 τ 实验及分析

θ：建索引时剔除 `df/N > θ` 的词。τ：查询时对 `df/N > τ` 的已有索引词抑制完整结果列表。两者相等时均不触发删除/抑制。

{table(th,theta_rows)}

θ 增大时，停用词减少，索引词条、保留位置和索引体积都增大。以默认 θ=0.5 为例，1,780 个词干仅占词表约 11.88%，却覆盖 86.29% 的出现位置；说明少数常见词占据大量文本。但 df/N 高并不一定语义无用，`love` 等内容词也可能被剔除，所以这种“noisy”划分是操作性判据，有精度/召回取舍。

{table(tah,taus)}

查询词使用原词形 `caesar`、`antony`、`hamlet`，不会对已词干化结果再词干化。`antony` 对应 `antoni`。表中数值为去重 doc_id 后展示的文档数：caesar 是 19 篇 / 602 个位置，不能写成 602 篇。

τ=0.1 时 caesar 和 antony 被抑制，hamlet 仍展示；τ=0.2 时 antony 恢复；τ=0.5 时三者均展示。抑制不代表原文没有匹配；程序仍打印 df/tf。三个 `τ=df/N` 的边界查询均允许展示。

`to be or not to be` 在原文中存在，但每个词都在 θ=0.5 stoplist 中，位置索引不再含这些词，所以默认短语查询返回 0。报告要把“原文出现次数”和“过滤后可检索次数”分开，不能将此结果当作语料缺失。

截图：[05 阈值实验](evidence/screenshots/05.png)。CSV：`theta_results.csv`、`tau_results.csv`。

测量限制：建索引时间是单次墙钟时间，部分实验运行时有其他测试活动；θ=0.5 初次构建额外写 token dump，其他 θ 没有。峰值内存为 Windows `PeakWorkingSetSize`（working set），10 ms 轮询读取；不是严格 RSS 上限或纯算法内存。性能数据只用于本机量级观察，不据小幅耗时差下结论。

## 6. Bonus：原 C 实现实测

题面是 **400,000,000 distinct words（不同词）**，不是 4 亿次重复出现。用重复词凑 4 亿 token 不能验证词典规模。

### 6.1 文档数与词典规模

{table(vh,vrows)}

`bonus_probe.c` 直接调用现有 `index.h`；生成确定性已归一词干，每词一个位置，构建、保存，再由原 query 重启加载查询。最大档达到 **500,000 逻辑文档 / 1,000,000 不同词**，查询校验通过。它未经过文件枚举、原文 tokenization 或停用词统计，不能称为“50 万实体文件端到端测试”。

另验证 500,000 个空逻辑 doc_id 的索引大小为 2,000,064 B，修复后可加载；这证明 doc_id 表达范围足够，不证明磁盘文件处理能力。

### 6.2 高频位置链退化

{table(['同一词的 tf','插入 CPU s','相邻档倍率'],crows)}

位置链表每次从头寻找插入点；按升序插入一个词的 n 个位置，遍历数为 `0+1+…+(n−1)=n(n−1)/2`，时间为 O(n²)。本机多数倍增档接近 4 倍耗时，最大档受系统负载影响更大；`index_load` 复用同一插入入口，也有该退化。

### 6.3 CLI 与文件偏移限制

将 500,000 个文件名构成参数列表，字符串长度 {b['cli']['command_chars']:,} 字符；真实创建进程时被 Windows 拒绝，WinError {b['cli']['winerror']}。这是参数接口限制测试，失败发生在 C 程序启动之前，因此不需要创建实体文件。

本机 `sizeof(long)=4`，`LONG_MAX=2,147,483,647`。索引虽在文件中存 u64 偏移，加载器却调用 `ftell/fseek` 并转成 long，不能可靠处理超过约 2 GiB 的索引。该结论来自类型探针和源代码，不是创建并测试了一个 2 GiB 文件。

截图：[06 原 C 后端压力测试](evidence/screenshots/06.png)。完整 CSV 和 JSON：`bonus_results.csv`、`bonus_summary.json`。

## 7. Bonus：外存原型补充验证

新增独立 `bonus_disk_demo.py`，用磁盘 SQLite B-tree 保存词典和位置表。页缓存预算 8 MiB，每批最多 2,000 个位置；保存后关闭再打开，核验词条数、不同 doc_id 数、integrity_check、单词、连续短语和阈值抑制。

{table(dh,drows)}

最大档查询最后一篇文档：单词命中 `(499999,1)`，两词短语命中 `(499999,0)`。测试通过。

这只是“把词典和 postings 存盘”的可运行原型，**不是原 C 程序已实现 SPIMI，也不兼容原 index.bin**。它使用已归一合成词干、每词出现一次的分布；页缓存固定不代表整个进程内存严格恒定。上述实测支持有限工作内存方向，但未验证 4 亿不同词，也未验证 50 万实体文件或一般高频语料。大型数据库在工作目录 `work/`，交付保留代码、测量和原始日志，避免把临时压力数据当真实语料。

截图：[07 外存原型](evidence/screenshots/07.png)。

## 8. Bonus：4 亿不同词的条件估算与结论

本机 `sizeof(Posting)={types['posting']}`、`sizeof(Position)={types['position']}`。假设每个不同词至少一个位置、词干字符串平均含结束符 16 B，则仅 C 索引载荷约为：

```text
8,000,072 + 400,000,000 × (32 + 16 + 16)
= 25,608,000,072 B
≈ 25.608 GB ≈ 23.85 GiB
```

这是**条件估算**，不含 malloc 元数据、碎片、词频统计数组、排序数组和重复词位置，实际需求更大。原 v1 词典每条固定元数据为 18 B，4 亿条仅元数据就需 **7.2 GB**，尚未计词干和 postings；这已超出本机 long 文件偏移范围。固定 1,000,007 个哈希桶下，V/hashsize≈400，均匀散列时每桶平均约 400 个词，链式查找常数明显增大。

因此回答题面“Will your program still work?”：**当前 C 内存后端不能直接支持完整 Bonus 规模。50 万 doc_id 可表示，但内存、位置链表构建、全量加载、命令行和 Windows 文件偏移限制都必须解决。**

可扩展路线：

1. 改为目录或文件清单输入，流式枚举，避免巨型 argv。
2. 统计阶段也要分块：先输出词干/文档统计块，外部归并得到全局 df，之后再确定停用词。只对 pass 2 分块不够。
3. 建索引用 SPIMI/BSBI 分块排序和多路外部归并；保留原文位置，生成 delta + varint postings。
4. 磁盘词典使用 B-tree 或分块 SSTable；64-bit 文件偏移；查询按需读取目标词的 postings，避免一次加载完整词典与位置链。
5. 高频查询可采用按需迭代、跳跃表、分页；如引入 top-K/BM25，应明确它改变了题目“返回全部 ID”的接口语义，不能直接用 top-K 代替完整正确性测试。
6. 更大规模验证需继续按不同词数量递增，记录峰值内存、磁盘容量、归并次数、索引正确性和查询延迟。

**已实测**：全集 42 文档，C 后端百万不同词 / 50 万逻辑文档，外存原型百万不同词，以及 CLI 失败与类型尺寸。**未实测**：4 亿不同词、50 万实体文件端到端输入。报告不可写成两者已全部跑过。

截图：[08 规模估算](evidence/screenshots/08.png)。

## 9. 复现与文件索引

已附语料，无需重新下载。Windows 安装 gcc 和 Python 3 后，从本目录运行：

```powershell
.\\run_lab.ps1 -PythonExe "你的Python路径\\python.exe"
# 复用已有索引，只重编译/对拍/查询；初始构建时间保留为首次实测值
.\\run_lab.ps1 -PythonExe "你的Python路径\\python.exe" -ReuseIndexes
```

完整重新构建约需数分钟；可复用模式不会再次运行五组全集建索引，仍重新验证索引内容和查询。脚本不依赖第三方 Python 包。`run_bonus.py` 外存数据写在工作目录，不递归删除任何目录。

直接复现查询：

```powershell
Set-Location .\\results\\shakespeare\\theta_0.5
& ..\\..\\..\\bin\\query.exe 'et tu brute'
& ..\\..\\..\\bin\\query.exe antonio bassanio
& ..\\..\\..\\bin\\query.exe --tau=0.1 caesar
Get-Content .\\output.txt
```

优先阅读本文件；浏览器记录入口 `evidence/index.html`；PNG 截图 `evidence/screenshots/01.png` 至 `08.png`。PNG 是真实浏览器对原始结果展示页的截图，**不是原生终端窗口截取**。生成展示页的脚本也已提供，可核对是否忠实于日志。

写报告时建议采用“实验目的 → 数据/环境 → 方法和命令 → 实测表 → 原因分析 → 局限 → Bonus 结论”的顺序，引用对应图片、原始日志和源代码差异。`documentation.md` 是整合后的完整报告；此前的合成语料报告保存在 `evidence/before_fix/documentation.md`，不能与本次真实全集数字混用。
'''
    (ROOT/'实验记录与报告素材.md').write_text(report,encoding='utf-8')
    design='''# PR1 实验报告：Roll Your Own Mini Search Engine

## Chapter 1：问题描述与目标

对题目指定 MIT 莎士比亚全集构建迷你搜索引擎。要求：（1）统计词频，划分 interesting / noisy words；（2）建立去除停用词、带词干化的位置倒排索引；（3）支持单词、AND 和短语，返回文档 ID；（4）测试查询阈值；（5）讨论 50 万文件 / 4 亿不同词的可行性。

输入为一组文本文件，每个文件一篇文档，doc_id 按固定清单顺序分配；输出包括词频/停用词记录、index.bin 和查询结果。真实语料按网站目录取 42 个条目，十四行诗 154 首合并。字段 df 是不同文档数，cf/tf 是出现次数，不能混用。

## Chapter 2：数据结构与算法

### 2.1 预处理与两遍扫描

先确定性地从 HTML 提取可见正文，再以 ASCII 字母/数字连续段分词、转小写。位置是完整文本中的 0 起始 token 编号。切词层不做词干化；每个原词在扫描/查询时通过 Porter stemword 一次变成词干，避免二次词干化改变 key。词干模块来源见 stem.c 注释。

Pass 1 为全部词建立位置索引，统计 cf/df。停用词判据为 df/N > θ，默认 θ=0.5；保存 stoplist 后释放第一遍索引。Pass 2 重新扫描全部文档，跳过 stoplist，保留原文位置，写出最终索引。--count-only 保留独立的词频统计入口。统计和建索引共用切词/词干口径。

高 df/N 表示在该文档粒度下区分能力弱，因此作为 noisy 的可操作定义；它不是语义上的绝对判断，部分内容词也会被删除。θ 实验用于展示空间与可检索范围的取舍。

### 2.2 内存与文件索引

内存使用固定 1,000,007 个哈希桶，链地址法按词干查 Posting；每个 Posting 保存词干、tf 和按 (doc_id,pos) 升序的位置链。DocTable 是升序去重文档 ID 数组，允许空文档，df/N 的 N 包含所有文档。Position 记录文档、位置和 next。

index.bin v1 的 64 B 头部保存魔数、版本、N/V/位置总数和三段偏移；文档段为 u32 ID；词典段按词干排序，每条为 u32 df、u32 tf、u64 posting 偏移、u16 字符串长度和字符串；位置段采用文档/位置差分与 LEB128。整数按小端写出，不直接 dump C 结构体。加载验证段边界、tf/df、总位置数和文档引用。没有校验和，因此结构自洽的字节改动不一定能发现。

写文件先写临时文件再替换；Windows 使用 MoveFileExA，POSIX 使用 rename。本次验证 Windows 重建覆盖。文件格式未改，但 Windows long 文件偏移仍限制超大索引。

### 2.3 查询算法

单词：归一化后查表，输出 df/tf 与全部位置。AND：各词提取升序文档列表，指针求交。短语：先求文档交集，再选 tf 最小词的原始下标 anchor；候选起点为 anchor 位置减 anchor，下标 i 的词必须位于 start+i。保持短语词序，不能按 tf 重排词数组。CLI 多个参数与 test.txt 普通多词行均为 AND；单个含空格参数或 phrase: 行为短语。

τ 为查询时的硬抑制阈值：已有词 df/N > τ 时打印统计，抑制完整 ID/位置列表。相等不抑制；原文匹配不因抑制变为不存在。含已删除停用词的精确短语无法在当前索引恢复。

### 2.4 复杂度与规模限制

一次哈希查找的平均链长度约为 V/hashsize。当前位置插入每次从头找位置，同一词的升序 tf 次插入需要 O(tf²)，不能将整条构建流程简单称为 O(tokens)。内存至少与词典和保留位置数一起增长。查询当前加载完整索引，并逐词 seek 到 postings，因此短查询也承担全量加载成本；具体实测见 Chapter 3。

### 2.5 验证原则

独立 Python 切词/聚合/二进制解析核对全部位置；词干实现共享，明确验证边界。另验证重复构建、load/save 往返、阈值边界、短语词序、空文档、文件输入与损坏拒绝。记录失败、修复前源码、最小反例和复测；将逻辑文档压力、实体文件输入、实际测量和理论估算分别说明。

## Chapter 3：真实实验、过程记录与 Bonus

'''
    experiment='\n'.join(('#'+line if line.startswith('#') else line) for line in report.splitlines()[1:])
    refs='''

## 参考资料

1. 题目截图：image.png，陈越，浙江大学。
2. MIT The Complete Works of William Shakespeare：https://shakespeare.mit.edu/；公开网站镜像：https://github.com/TheMITTech/shakespeare。
3. Martin Porter, An algorithm for suffix stripping, Program, 1980。C 实现引用：https://github.com/wooorm/stmr.c（项目 stem.c 中保留来源）。
4. Manning, Raghavan, Schütze, Introduction to Information Retrieval，倒排索引和索引构建章节：https://nlp.stanford.edu/IR-book/。
5. SQLite 官方文档，cache_size 与 temp_store：https://www.sqlite.org/pragma.html；用于独立 Bonus 外存原型。
6. 当前源码基线和完整测量见 evidence/repository_baseline.json、results/*.json。4 亿词规模没有实跑，相关数字均为条件估算或格式推导。
'''
    (ROOT/'documentation.md').write_text(design+experiment+refs,encoding='utf-8')
    readme=f'''# ADS PR1：迷你搜索引擎

当前仓库基线：nothing793/adsproject，commit `{s['corpus']['source_commit']}`。

已补充题目指定网站的全集语料、真实正确性与 θ/τ 测试、Bonus 规模实验、修复回归和 8 张过程截图。全集为 **42 文档 / 956,647 tokens / 14,986 词干**；最终 **{s['passed']} PASS / {s['failed']} FAIL**。

- [完整实验报告](documentation.md)：Chapter 1 问题、Chapter 2 方法、Chapter 3 测试与 Bonus。
- [实验记录与报告素材](实验记录与报告素材.md)：命令、结果、分析和截图引用。
- [8 张截图的说明](evidence/截图说明.md)；[浏览器展示页索引](evidence/index.html)。PNG 是实际浏览器截图，展示页由原始日志生成。
- [源码修改差异](evidence/source_changes.patch)：短语词序、合法空文档加载、test.txt AND 语义、Windows 索引替换。
- [全集清单](data/shakespeare/documents.csv)、[来源与校验和](data/shakespeare/manifest.json)。

## 编译与运行

```powershell
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic -o code/index_gen.exe code/index_gen.c code/stem.c -lm
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic -o code/query.exe code/query.c code/stem.c -lm
Set-Location code
$corpus = Get-ChildItem ../data/shakespeare/corpus/*.txt | Sort-Object Name
./index_gen.exe --theta=0.5 $corpus.FullName
./query.exe 'et tu brute'
./query.exe antonio bassanio
./query.exe --tau=0.1 caesar
./query.exe # 读取已附 test.txt；普通多词行是 AND，phrase: 行为短语
Get-Content output.txt
```

Linux / macOS 使用同样 gcc 命令生成 index_gen / query，然后 `./index_gen corpus/*.txt`（传入正确相对路径）。输入文件顺序决定 doc_id；本次清单按文件名排序。

## 一键复现实验

Python 3 + gcc，无第三方 Python 包依赖。PowerShell：

```powershell
./run_lab.ps1 -PythonExe '你的Python路径/python.exe'
# 已有索引时，可复用索引并重新对拍、重启查询
./run_lab.ps1 -PythonExe '你的Python路径/python.exe' -ReuseIndexes
```

也可直接运行 `python code/tests/run_extended.py`、`python code/tests/run_bonus.py`、`python code/tests/make_lab_report.py`。首次全集建索引需要数分钟；原始 stdout/stderr、参数、cwd、退出码和测量保存在 results/logs。

`python code/tests/sweep.py` 展示最近一次校验通过的阈值表；`--rebuild` 重新构建并校验。旧合成语料测试保留作补充，不再代表真实全集结果。

## Bonus 的验证范围

原 C 后端与独立外存原型均实测至 **50 万逻辑 doc_id / 100 万不同词干**。未创建 50 万实体文件，未实跑 4 亿不同词。当前 C 后端不能直接支持完整 Bonus 规模：内存词典、二次方位置插入、全量加载、巨型 argv 与 Windows long 偏移限制均需改造。独立 SQLite 原型验证固定页缓存的外存方向，不能据此宣称完整 Bonus 规模已通过。

临时大型索引、数据库、exe、token dump 不纳入 Git；测量、真实语料、截图和生成脚本纳入 Git。源代码版本与初始参考仓库相等性见 evidence/repository_baseline.json。
'''
    (ROOT/'readme.md').write_text(readme,encoding='utf-8')
    (EVIDENCE/'截图说明.md').write_text('# 实验截图索引\n\n这些 PNG 是真实浏览器截图，页面由实际测试日志生成，并非终端原屏截图。原始命令、参数、cwd、退出码、时间和内存都能在 results/logs 中核对。\n\n'+
        table(['编号','实验步骤','报告用途'],[[f'{i:02d}.png',name,purpose] for i,name,purpose in [
        (1,'数据准备与来源','说明全集范围、doc_id、预处理'),(2,'编译、词频与建索引','说明 Part 1/2 原始输出'),
        (3,'独立对拍与测试通过','证明倒排索引正确性'),(4,'短语错误与修复前后','展示真实问题定位和回归'),
        (5,'θ/τ 实验','分析阈值对空间与结果展示的影响'),(6,'原后端压力与 CLI 限制','Bonus 实测瓶颈'),
        (7,'外存原型重启查询','Bonus 改进方向的有限验证'),(8,'4 亿不同词估算','区分测量、格式推导与条件估算')]])+
        '\n详见 ../实验记录与报告素材.md；打开 index.html 可查看全部展示页。\n',encoding='utf-8')
    print('PASS: report material + 8 browser evidence pages generated from actual results')


if __name__=='__main__':
    main()
