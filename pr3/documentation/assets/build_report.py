#!/usr/bin/env python3
"""读取真实测试记录，生成中文报告、结果图和 PDF；不重新生成测试结果。"""
import argparse
import csv
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from render_pdf import render
from math_layout import typeset_math

PROJECT=Path(__file__).resolve().parents[2]


def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)


def figures(validation,destination,font_path):
    """图像坐标只用于排版；每条边及每个计时点都来自本次实际输出。"""
    font=ImageFont.truetype(str(font_path),24,index=0)
    small=ImageFont.truetype(str(font_path),20,index=0)
    image=Image.new('RGB',(1120,650),'white'); draw=ImageDraw.Draw(image)
    values=list(map(int,(validation/'inputs/sample_1.txt').read_text().split())); n,m=values[:2]
    grid=[values[2+r*m:2+(r+1)*m] for r in range(n)]
    step=95; left=280; top=110
    draw.text((30,24),'样例 1：根据程序实际输出恢复的栅栏',fill='black',font=font)
    for r in range(n):
        draw.line((left,top+r*step,left+(m-1)*step,top+r*step),fill='#d7dde2',width=1)
    for c in range(m):
        draw.line((left+c*step,top,left+c*step,top+(n-1)*step),fill='#d7dde2',width=1)
    for line in (validation/'outputs/sample_1.txt').read_text().splitlines():
        row,column,*bits=map(int,line.split()); r=row-1; c=column-1
        for direction,(dr,dc) in enumerate(((-1,0),(1,0),(0,-1),(0,1))):
            if not bits[direction] or direction not in (1,3):
                continue
            nr,nc=r+dr,c+dc
            while not grid[nr][nc]:
                nr+=dr; nc+=dc
            draw.line((left+c*step,top+r*step,left+nc*step,top+nr*step),fill='#225a82',width=7)
    for r in range(n):
        for c in range(m):
            if grid[r][c]:
                x,y=left+c*step,top+r*step
                draw.ellipse((x-22,y-22,x+22,y+22),fill='white',outline='#225a82',width=2)
                draw.text((x,y),str(grid[r][c]),fill='black',font=font,anchor='mm')
    for r in range(n):
        draw.text((left-55,top+r*step),str(r+1),fill='black',font=small,anchor='mm')
    for c in range(m):
        draw.text((left+c*step,top-52),str(c+1),fill='black',font=small,anchor='mm')
    image.save(destination/'sample_solution.png')

    summary=json.loads((validation/'summary.json').read_text(encoding='utf-8'))
    image=Image.new('RGB',(1120,650),'white'); draw=ImageDraw.Draw(image)
    draw.text((30,20),'规模测试：三份同分布输入的进程墙钟时间中位数',fill='black',font=font)
    left,top,width,height=115,100,780,410
    ymax=max(10,math.ceil(max(s['median_wall_ms'] for s in summary['sizes'])/10)*10)
    for tick in range(6):
        value=ymax*tick/5; y=top+height-height*tick/5
        draw.line((left,y,left+width,y),fill='#dce1e6',width=1)
        draw.text((left-12,y),f'{value:.0f}',fill='black',font=small,anchor='rm')
    draw.text((15,76),'毫秒',fill='black',font=small)
    dimensions=[(2,50),(10,10),(25,25),(50,50)]
    for i,(n,m) in enumerate(dimensions):
        x=left+i*width/3
        draw.text((x,top+height+30),f'{n}×{m}',fill='black',font=font,anchor='mm')
    draw.rectangle((925,100,1100,370),outline='#c4ccd3',width=1)
    draw.text((980,114),'图例',fill='black',font=small)
    for index,(probability,color) in enumerate(((.15,'#20639b'),(.4,'#d66a20'),(.75,'#25834b'),(1.,'#754a9b'))):
        values=[next(s['median_wall_ms'] for s in summary['sizes'] if (s['rows'],s['columns'],s['probability'])==(n,m,probability)) for n,m in dimensions]
        points=[(left+i*width/3,top+height-height*value/ymax) for i,value in enumerate(values)]
        draw.line(points,fill=color,width=3)
        for x,y in points:
            draw.ellipse((x-5,y-5,x+5,y+5),fill=color)
        y=174+index*52
        draw.line((938,y,968,y),fill=color,width=4)
        draw.text((980,y),f'p={probability:g}',fill='black',font=small,anchor='lm')
    draw.text((115,590),'p 为生成单位边的概率；计时包含进程启动与输入输出。',fill='black',font=small)
    image.save(destination/'runtime.png')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validation',required=True,type=Path)
    parser.add_argument('--font',type=Path,default=Path('C:/Windows/Fonts/simsun.ttc'))
    parser.add_argument('--bold-font',type=Path,default=Path('C:/Windows/Fonts/simhei.ttf'))
    args=parser.parse_args(); validation=args.validation.resolve(); destination=PROJECT/'documentation'
    s=json.loads((validation/'summary.json').read_text(encoding='utf-8'))
    assert s['failed']==0
    with (validation/'cases.csv').open(encoding='utf-8-sig',newline='') as f:
        cases=list(csv.DictReader(f))
    labels={'sample':'题目样例','curated':'专项边界','exhaustive_2x2':'2×2 全部度数组合','matching_3x3':'3×3 全部 0/1 组合','random_small':'随机小规模对拍','witness_large':'已知布局反推的大规模输入','dense_cycles':'满网格二度连接器','large_unsat':'大规模不可行分量'}
    groups=table(['测试组','数量','可解','无解','结论'],[(labels[g['group']],g['count'],g['sat'],g['unsat'],'全部通过') for g in s['groups']])
    selected=[r for r in cases if r['group'] in ('sample','curated') or r['name'] in ('cycles_25','bipartite_imbalance_50')]
    details=table(['用例','目的','预期','实测'],[(r['name'],r['purpose'],'可解' if r['expected']=='True' else '无解','通过') for r in selected])
    sizes=table(['尺寸','生成概率 p','输入数','中位墙钟 ms','最大候选边','最大冲突数'],[(f"{z['rows']}×{z['columns']}",z['probability'],z['runs'],f"{z['median_wall_ms']:.3f}",z['max_variables'],z['max_conflicts']) for z in s['sizes']])
    sample=(validation/'outputs/sample_1.txt').read_text().strip()
    sat=s['sat_core']
    figures(validation,destination,args.font)
    report=f'''# Project 3：栅栏布局恢复

作者：陈昱年，宋诗雨，王宇轩
第四组。
陈昊老师。

完成日期：2026 年 10 月 20 日

采用候选图建模与冲突驱动的布尔约束求解，恢复满足度数和几何限制的任意一组栅栏布局。程序以 C99 实现，报告依据逐例测试记录编写。

## Chapter 1 问题描述

### 1.1 任务与输入输出

花园是 n 行 m 列的网格，2 <= n,m <= 50。非零格点放置度数为 1 至 4 的连接器，零格点表示没有连接器。栅栏必须水平或竖直，不能自行转弯，也不能在没有连接器的位置相交。本项目根据连接器位置和度数恢复布局；无法满足约束时输出 `No Solution`。

每个连接器需要输出所在行、列及上、下、左、右四个方向的 0/1 状态，采用从 1 开始的行列编号，按行优先排序。多解时输出任意合法布局，不要求与样例逐字相同。题目没有要求所有连接器构成一个连通分量，也没有最小化总长度的目标。

### 1.2 问题中的两类约束

度数约束只规定连接器使用多少个方向，不能单独保证几何合法。例如 3×3 花园四条边中点各有一个一度连接器、中心为空时，水平和竖直两条线都被迫选取，虽然端点度数均满足，却在中心交叉，因此仍应判为无解。

程序将“恰好满足度数”与“空位置不交叉”分别编码。连接器处允许多个方向相接，包括四路交汇。没有连接器的花园对应空布局，标准输出为空；输入格式错误与合法输入无解分开处理，前者写入标准错误并以非零状态退出。

## Chapter 2 数据结构与算法

### 2.1 候选边的完备构造

沿每一行和每一列扫描，仅连接相邻的非零格点，得到候选边集合。若一条直线经过另一个连接器，它可以在该连接器处分成两条候选边；因此无需添加跨越中间连接器的跳跃边。每个连接器至多关联四条候选边。

令候选边 e 的布尔变量为 x[e]，1 表示选取该边。内部文字编码采用 `2*e` 表示 x[e]，`2*e+1` 表示它的否定。边的两个端点、端口方向和经过的空格都由建模阶段确定。

| 数据结构 | 内容及用途 |
| --- | --- |
| Garden | 行列数及每个格点要求的度数 |
| Model.edges | 候选边的两个端点和正向端口 |
| Model.incident | 每个连接器四个方向对应的边编号，无边为 -1 |
| horizontal / vertical | 各空格经过的水平、竖直候选边，用于发现交叉 |
| Clause / watches | 子句文字数组及按文字编号组织的双监视表 |
| values / levels / reasons | 当前真值、决策层及推导原因子句 |
| trail / limits | 赋值轨迹及各决策层起点，支持撤销赋值 |
| activity / heap | 变量活动度与最大堆，只改变搜索顺序 |

### 2.2 度数、交叉与必要条件

对于度数要求 k、可用候选边数 d 的连接器，要求选边数恰好为 k。若 k>d，直接加入空子句。否则，对任意 k+1 条关联边加入“不能全真”的子句，确保至多 k 条；对任意 d-k+1 条关联边加入“不能全假”的子句，确保至少 k 条。d<=4，因此最多枚举 16 个子集，每个连接器最多产生 8 个子句。

若一个空格同时经过水平候选边 h 与竖直候选边 v，加入 `NOT x[h] OR NOT x[v]`。同一空格每个轴至多存在一条候选边，故无需枚举任意两条边来寻找交叉。

此外，每个候选图连通分量的度数和必须为偶数。若该分量能够二染色，两侧所需度数之和还必须相等，因为每条选中边都对两侧各贡献 1。这些条件只用于提前判定矛盾；并未假定所有候选图都是二分图。测试中的五连接器矩形布局，在一条边上插入一个连接器后便形成可解的奇环。

### 2.3 建模伪代码

```text
BUILD(garden):
  edges = consecutive nonzero cells in every row and column
  create one Boolean variable per edge
  for each candidate component:
    reject odd degree sum
    if bipartite: reject unequal degree sums on the two sides
  for each connector with target k and incident edges S:
    if k > size(S): add empty clause
    else:
      for each subset A of S with size k+1:
        add clause: at least one edge in A is false
      for each subset B of S with size size(S)-k+1:
        add clause: at least one edge in B is true
  for each empty cell crossed by candidate edges h and v:
    add clause: NOT h OR NOT v
  return formula
```

### 2.4 约束求解

求解器使用冲突驱动子句学习（CDCL）。赋值后只检查刚刚变假的文字所在监视表。若子句能找到另一个非假的文字，就迁移监视；否则剩余监视文字必须被推导为真，或形成冲突。单位条件保存在赋值队列中，空子句立即表示矛盾。

冲突发生后，沿赋值轨迹反向分析原因子句，并消解到学习子句中只剩一个当前层文字，即 First UIP。回跳到学习子句其他文字的最高层后，新的子句会立刻推导一个赋值。变量活动度增加，使近期冲突涉及的变量优先被选择；堆的比较规则相同时优先较小编号，保证运行可复现。

重启在冲突预算达到阈值后执行，保留学习子句和已保存的分支相位。初始预算为 100，此后按 1.5 倍增长，达到上限附近后停止增长。当前版本不清理学习子句。所有内存分配均检查失败；运行资源错误不能被当作无解。

```text
SOLVE(formula):
  enqueue original unit clauses at level 0
  repeat:
    conflict = propagate all queued assignments
    if conflict exists:
      if current level == 0: return UNSAT
      learned = resolve reasons backwards until one current-level literal
      target = highest level among the other learned literals
      undo assignments above target
      store learned clause and enqueue its asserting literal
    else:
      restart to level 0 when the conflict budget is reached
      if every variable is assigned: return SAT
      choose an unassigned variable using the activity heap
      begin a new level and assign its saved phase
```

### 2.5 正确性说明

必要性：任意合法栅栏都可分解为同一行或列相邻连接器之间的边，故对应候选边的一个赋值。每个连接器恰好使用 k 个方向，满足基数子句；没有空位置交叉，满足所有交叉互斥子句。分量必要条件由边对端点度数的贡献直接得到，不会排除合法布局。

充分性：任意满足公式的赋值都在每个连接器上选出恰好 k 条边。候选边是端点之间没有其他连接器的直线，故没有悬空终点或无连接器转弯。互斥子句排除了所有内部空格上的水平、竖直交叉。将每条选中边同时写入两个端点的相反方向，便得到合法且互反一致的输出。

搜索层面，单位传播只采用子句的逻辑蕴含，学习子句由冲突原因消解产生，不改变原公式的满足模型。回溯撤销赋值而不撤销约束；第 0 层出现矛盾时可判无解。双监视机制保证不会在存在全假子句时返回完整模型。算法思想参考文献 [1]，C 程序未调用外部 SAT 库。

## Chapter 3 测试与结果

### 3.1 环境和验证方法

测试日期为 2026 年 10 月 20 日。平台：{s['environment']['platform']}；Python：{s['environment']['python']}；编译器：{s['environment']['compiler']}。编译选项为 `-std=c99 -O2 -Wall -Wextra -Wpedantic`，主程序与 SAT 测试入口均零告警编译。固定随机种子为 {s['seed']}。

验证分为两层。花园层的小规模参考程序通过两两枚举连接器及直接选边搜索判断可行性，不使用 C 程序的子句编码。对于可解输出，再沿四个方向追踪真实端点，检查行序、字段格式、0/1 状态、度数、端点互反和空格交叉；这允许程序返回不同于样例的合法解。

对于 50×50 等大规模可解用例，先在完整网格上随机选择单位边，再从已知合法布局反推度数。零度连接器删除后，原选中边仍构成合法见证，因此可以独立确定输入可解。统计中每个概率使用三份不同的同分布输入，计时采用这三份输入的进程墙钟中位数，包含进程启动、读入、求解和输出。

### 3.2 完整测试分组

{groups}

上述 {s['garden_cases']} 个花园用例全部通过，另有 {s['invalid_inputs']} 个非法输入检查和 {s['error_paths']} 个接口错误路径检查通过。非法输入包括行列数越界、缺失数据、非法度数、负数、整数溢出和多余 token；要求返回 1、标准输出为空，并给出明确的输入错误。未知参数必须返回 1；标准输出连接到只读句柄时，显式刷新须发现写入失败并返回 2。

逐例完整数据表为压缩包内的 `cases.csv`，每行包含用例编号、测试目的、尺寸、预期、实际、是否通过、墙钟时间及搜索统计。每个合法输入另附输入文件、原始输出和退出码；非法输入记录在 `logs/invalid_*.json`。下表列出题目样例和几何、图论边界用例，其余穷举及随机用例逐行保存在 CSV 中。

{details}

### 3.3 样例恢复结果

样例 1 的一次实际输出如下。样例 2 返回 `No Solution`；样例 3 通过几何校验。由于题目允许多解，判断依据是约束是否满足，而非文本是否与给定输出完全相同。

```text
{sample}
```

![图 1 样例 1 实际输出对应的布局](sample_solution.png)

### 3.4 SAT 核心独立测试

SAT 核心另使用 {sat['cases']} 个公式验证：3 个空公式、空子句与矛盾单位条件的基础用例，3,000 个 1 至 10 变量的固定随机公式，以及一个 7 鸽 6 孔不可满足公式。随机公式逐一枚举全部真值赋值；若 C 求解器返回 SAT，还逐条检查其模型是否满足所有原始子句。

鸽巢公式中，每只鸽子至少占用一个孔，每个孔至多容纳一只鸽子，因此 7 只鸽子不能放入 6 个孔。该用例实测产生 {sat['pigeonhole_conflicts']} 次冲突、{sat['pigeonhole_learned']} 条学习子句和 {sat['pigeonhole_restarts']} 次重启，覆盖了冲突学习、非顺序回溯和重启路径。逐例预期及实际结果见 `sat_results.csv`，公式与原始输出分别见 `sat_cases.txt` 和 `sat_stdout.txt`。

总计 {s['passed']} 项检查通过、{s['failed']} 项失败。该总数包含花园、非法输入、接口错误路径和 SAT 核心检查，不表示相同数量的不同花园。

### 3.5 规模测试数据

{sizes}

![图 2 不同尺寸与生成概率下的进程墙钟时间](runtime.png)

计时包含系统调度和进程启动成本，毫秒级差异不能单独用来证明算法阶数。概率 p=1 时所有可用单位边均被选取，连接器度数往往直接强制候选边；较低密度可能引入更多选择和冲突，因此输入更稠密并不必然更难。

## Chapter 4 复杂度与讨论

### 4.1 建模复杂度

令 V 为连接器数，E 为候选边数，Q 为空格交叉点数。每个连接器至多四条关联边；按完整网格上界，`E <= n*(m-1)+m*(n-1)`，在 50×50 时最多 4,900 条。逐行、逐列扫描均为 O(nm)。每行水平边内部区间互不重叠，每列竖直边同理，因此登记内部空格的总工作量也是 O(nm)，而不是逐边扫描整个花园。

每个连接器枚举至多 16 个子集，加入至多 8 个长度不超过 4 的子句。每个空格至多产生一个交叉子句，Q<=nm。分量遍历为 O(V+E)。因此初始公式的子句数与文字总数 L0 均为 O(nm)，建模时间与空间同为 O(nm)。程序中的格点数组按题目上限 50 分配，固定上限下占用有界；若将行列上限作为参数，其规模随网格面积线性增长。

### 4.2 搜索复杂度与内存

布尔搜索没有多项式最坏时间保证。活动度、学习和重启可以减少重复冲突，但不能将所有合法尺寸的输入都视为同等难度。程序的分支空间以候选边为变量，直接枚举已有 2 的 E 次方个可能赋值；本实现不承诺对任意 50×50 输入在固定时限内结束。

更具体地，令 R 为累计处理的赋值队列项数，B 为分支次数，U 为撤销后重新入堆的变量次数，C 为冲突分析次数，Lmax 为搜索期间保留子句的最大文字总数。单次监视扫描最坏可检查 O(Lmax) 个文字；堆更新为 O(log E)；一次反向冲突分析至多处理 O(E) 个变量及相关原因子句。因此可用 `O(nm + R*Lmax + (E+B+U)*log E + C*(Lmax+E*log E))` 表示按实际搜索操作数计的保守上界，E=0 时搜索为空公式的常数开销。

模型、赋值数组、堆和轨迹需要 O(nm+E) 空间。子句文字和监视项需要 O(Lmax) 空间，合计 O(nm+E+Lmax)。当前版本保留全部学习子句，Lmax 可能随困难实例显著增长，不能把搜索全过程的内存仍写成初始公式的线性规模。

### 4.3 实测现象与限制

本次最大尺寸 50×50 的已知可解布局全部恢复成功，并检查了最大 4,900 条候选边的输入。稀疏输入、长边和空格交叉由专项及小规模穷举覆盖；奇环用例验证了没有错误地将任意候选图当作二分图。

无解判定必须同时考虑度数和几何条件。四个一度端点的十字交叉用例即使忽略交叉限制也能满足度数，但实际无解；四路连接器处则允许交汇。输出校验器分别处理这两种情形。

测试覆盖不能代替完整输入空间的证明。大规模试验主要采用已知合法布局反推输入，尚未穷举所有大规模不可满足布局。程序不设置“搜索超时就输出无解”的规则；测试驱动中的超时会作为测试失败抛出。题面未设置 Bonus，本报告不另行虚构扩展评分项。

## Chapter 5 复现与提交组织

### 5.1 编译和运行

在 `pr3` 目录运行以下命令。程序只依赖 C99 标准库，不链接第三方求解器。

```bash
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic \\
    code/main.c code/fence.c code/sat.c -o fence
./fence < input.txt
./fence --stats < input.txt
```

`--stats` 将变量数、原始子句数、交叉点、分支、传播、冲突、学习及重启计数以 JSON 写入标准错误，不改变标准输出。Windows PowerShell 中可先生成 `fence.exe`，然后使用 `Get-Content input.txt | ./fence.exe`。

### 5.2 重新验证与生成报告

```bash
python code/tests/run_tests.py --output testresult/run
python documentation/assets/build_report.py --validation testresult/run
```

测试仅依赖 Python 标准库与 gcc；图表和 PDF 生成另依赖 Pillow、ReportLab 及中文字体，详见 `documentation/assets/README.md`。这两项文档库不参与求解和正确性判定；图像画布存储随像素数量线性增长。

`code/` 保存源码、接口与验证程序；`documentation/` 保存 Markdown、PDF、结果图及生成工具；`testresult/validation-20261020.zip` 只收录测试材料和结果，不重复打包代码或报告。该 ZIP 中包含测试环境、完整逐例 CSV、输入输出、SAT 测试公式、原始搜索统计、编译命令和源码 SHA-256 校验清单。各评分条目与章节的映射见 `pr3/readme.md`。

## 参考文献

[1] Niklas Eén, Niklas Sörensson. An Extensible SAT-solver. SAT 2003, LNCS 2919, pp. 502-518. https://doi.org/10.1007/978-3-540-24605-3_37 。作者公开稿：https://minisat.se/downloads/MiniSat.pdf 。参考其双监视文字、冲突学习及动态变量选择的算法思想，未链接 MiniSat 库。

[2] ADS 第四组. Project 3 题面、样例及布局图. 本仓库 `pr3/readme.md`、`pr3/image.png`，读取日期：2026-10-20。
'''
    report=typeset_math(report)
    path=destination/'report.md'; path.write_text(report,encoding='utf-8')
    render(path,destination/'report.pdf',args.font,args.bold_font)
    print(json.dumps({'report':str(path),'pdf':str(destination/'report.pdf'),'checks':s['passed']},ensure_ascii=False))


if __name__=='__main__':
    main()
