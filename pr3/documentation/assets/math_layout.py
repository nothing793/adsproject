"""为报告补充 LaTeX 约束、下标及逐步复杂度推导，保留原始实测数据。"""


def replace_section(text, start, end, replacement):
    left=text.index(start); right=text.index(end,left)
    return text[:left]+replacement.strip()+'\n\n'+text[right:]


def typeset_math(report):
    report=report.replace('2 <= n,m <= 50',r'$2\le n,m\le 50$')
    report=replace_section(report,'### 2.1 候选边的完备构造','### 2.2 度数、交叉与必要条件',r'''
### 2.1 候选边的完备构造

沿每一行和每一列扫描，仅连接相邻的非零格点，得到候选图 $G=(V,E)$。若一条直线经过另一个连接器，它可以在该连接器处分成两条候选边；因此无需添加跨越中间连接器的跳跃边。每个连接器至多关联四条候选边。

令 $x_e\in\{0,1\}$ 表示候选边 $e\in E$ 是否被选取。内部文字编码采用 `2*e` 表示 $x_e$，`2*e+1` 表示 $\neg x_e$。端点、端口方向和经过的空格在建模阶段确定。记顶点 $v$ 的关联边集合为 $\delta(v)$，可用方向数为 $d_v=|\delta(v)|$，目标度数为 $k_v$。

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
''')
    report=replace_section(report,'### 2.2 度数、交叉与必要条件','### 2.3 建模伪代码',r'''
### 2.2 度数、交叉与必要条件

每个连接器恰好选择 $k_v$ 条关联边，即

$$
\sum_{e\in\delta(v)}x_e=k_v,\qquad v\in V.
$$

当 $k_v>d_v$ 时加入空子句。否则，先对任意 $k_v+1$ 条关联边规定“不能全真”，得到至多 $k_v$ 条的条件：

$$
\bigwedge_{\substack{A\subseteq\delta(v)\\|A|=k_v+1}}
\left(\bigvee_{e\in A}\neg x_e\right).
$$

再对任意 $d_v-k_v+1$ 条关联边规定“不能全假”，得到至少 $k_v$ 条的条件：

$$
\bigwedge_{\substack{B\subseteq\delta(v)\\|B|=d_v-k_v+1}}
\left(\bigvee_{e\in B}x_e\right).
$$

两组条件合起来等价于精确度数约束。由于 $d_v\le4$，至多枚举 $2^{d_v}\le16$ 个子集，每个连接器最多产生 8 个子句。

若空格同时经过水平候选边 $e_h$ 与竖直候选边 $e_v$，则要求

$$
x_{e_h}+x_{e_v}\le1
\quad\Longleftrightarrow\quad
\neg x_{e_h}\lor\neg x_{e_v}.
$$

同一空格每个轴至多存在一条候选边，因此扫描空格即可发现全部交叉。

此外，每个候选图连通分量 $C$ 都必须满足

$$
\sum_{v\in C}k_v\equiv0\pmod2.
$$

若分量能够二染色，记其两侧为 $A_C$、$B_C$，每条选中边对两侧各贡献 1，故还必须满足

$$
\sum_{v\in A_C}k_v=\sum_{v\in B_C}k_v.
$$

这些必要条件只用于提前判定矛盾，并未假定候选图总是二分图。测试中的五连接器矩形布局，在一条边上插入一个连接器后便形成可解的奇环。
''')
    report=replace_section(report,'### 2.3 建模伪代码','### 2.4 约束求解',r'''
### 2.3 建模伪代码

以下采用 Python 风格伪代码表示集合和循环，实际评测程序由 C99 实现。

```python
def build_formula(garden):
    edges = scan_consecutive_connectors(garden)
    solver = create_solver(len(edges))
    for component in candidate_components(edges):
        add_component_checks(solver, component)
    for vertex in connectors(garden):
        S, k = incident_edges(vertex), degree(vertex)
        if k > len(S):
            add_clause(solver, [])  # 空子句表示矛盾
        else:
            for A in subsets(S, size=k + 1):
                add_clause(solver, [NOT(e) for e in A])
            for B in subsets(S, size=len(S) - k + 1):
                add_clause(solver, [e for e in B])
    for h, v in empty_cell_crossings(edges):
        add_clause(solver, [NOT(h), NOT(v)])
    return solver
```
''')
    start=report.index('```text\nSOLVE(formula):')
    end=report.index('```',start+4)+3
    replacement='''```python
def solve(formula):
    enqueue_original_units(level=0)
    while True:
        conflict = propagate()
        if conflict is not None:
            if current_level() == 0:
                return UNSAT
            learned = first_uip(conflict)
            target = highest_other_level(learned)
            cancel_until(target)
            store_clause(learned)
            enqueue(learned[0], reason=learned)
        else:
            if restart_budget_reached():
                cancel_until(0)
            if all_variables_assigned():
                return SAT
            variable = choose_by_activity()
            begin_level()
            enqueue(saved_phase(variable), reason=None)
```

实际 C 实现中，冲突分析与回跳后的关键语句如下（为便于阅读，调整了空白和分行）。学习子句保存后立即推导其断言文字；相关数组和不变量的中文注释见 `code/sat.c`。

```c
int backtrack, id;

backtrack = analyze(s, conflict);
cancel_until(s, backtrack);
id = store_clause(s, s->learned.data, s->learned.count);
++s->stats.learned;

if (!enqueue(s, s->learned.data[0], id)) {
    return 0;
}
```'''
    report=report[:start]+replacement+report[end:]
    report=report.replace('每个连接器恰好使用 k 个方向',r'每个连接器恰好使用 $k_v$ 个方向')
    report=report.replace('每个连接器上选出恰好 k 条边',r'每个连接器上选出恰好 $k_v$ 条边')
    report=replace_section(report,'### 4.1 建模复杂度','### 4.2 搜索复杂度与内存',r'''
### 4.1 建模复杂度

记连接器数为 $N_v=|V|$，候选边数为 $N_e=|E|$，空格交叉点数为 $N_q$。一行至多有 $m-1$ 条水平候选边，一列至多有 $n-1$ 条竖直候选边，因此

$$
\begin{aligned}
N_e&\le n(m-1)+m(n-1)\\
   &=2nm-n-m.
\end{aligned}
$$

在题目上界 $n=m=50$ 时，进一步得到

$$
N_e\le2\times50\times50-50-50=4900.
$$

逐行、逐列扫描均为 $O(nm)$。同一行水平边的内部区间互不重叠，同一列竖直边同理；故登记经过的空格总共只需 $O(nm)$，不需要对每条边重新扫描整个花园。分量遍历耗时 $O(N_v+N_e)$。

每个连接器至多产生 8 个长度不超过 4 的度数子句；每个空格至多产生一个交叉子句，且 $N_q\le nm$。记因分量必要条件不满足而加入的空子句数为 $N_{\mathrm{bad}}$，则初始子句数和文字总数分别满足

$$
\begin{aligned}
N_{\mathrm{clause},0}&\le8N_v+N_q+N_{\mathrm{bad}},\\
L_0&\le32N_v+2N_q.
\end{aligned}
$$

因为 $N_{\mathrm{bad}}\le N_v\le nm$，且每个候选边的两个端点共占用关联表中的两个方向，所以 $N_e=O(nm)$。代入扫描、分量检查及子句生成的工作量，得到

$$
\begin{aligned}
T_{\mathrm{build}}
 &=O(nm+N_v+N_e+L_0)=O(nm),\\
S_{\mathrm{initial}}
 &=O(nm+N_e+L_0)=O(nm).
\end{aligned}
$$

程序按上限 50 分配格点数组，固定上限下占用有界；若将行列上限作为参数，其规模随网格面积线性增长。
''')
    report=replace_section(report,'### 4.2 搜索复杂度与内存','### 4.3 实测现象与限制',r'''
### 4.2 搜索复杂度与内存

布尔搜索没有多项式最坏时间保证。候选边构成 $N_e$ 个布尔变量，直接枚举的赋值总数为

$$
N_{\mathrm{assignment}}=2^{N_e}.
$$

活动度、学习和重启可以减少重复冲突，但不能将所有合法尺寸输入都视为同等难度。本实现不承诺对任意 $50\times50$ 输入在固定时限内结束。

为描述实际搜索工作量，使用下列记号：

| 记号 | 含义 |
| --- | --- |
| $N_p$ | 累计处理的赋值队列项数 |
| $N_b$ | 分支次数 |
| $N_u$ | 撤销赋值后重新入堆的变量次数 |
| $N_c$ | 冲突分析次数 |
| $L_{\max}$ | 搜索期间保留子句的最大文字总数，包含学习子句 |

单次处理赋值的监视扫描最坏检查 $O(L_{\max})$ 个文字；堆更新为 $O(\log(N_e+1))$。一次冲突分析至多处理 $N_e$ 个变量及其相关原因子句，还可能对这些变量更新堆。因此，一个按累计操作数表示的保守上界为

$$
\begin{aligned}
T_{\mathrm{solve}}=O\bigl(&N_pL_{\max}\\
 &+(N_e+N_b+N_u)\log(N_e+1)\\
 &+N_c[L_{\max}+N_e\log(N_e+1)]\bigr).
\end{aligned}
$$

这里使用 $\log(N_e+1)$ 处理空变量集合的边界；空公式的求解额外开销为常数。该表达式刻画实际搜索工作，不构成多项式最坏上界，因为搜索次数和学习子句数量均可能显著增长。

模型、赋值数组、堆和轨迹占用 $O(nm+N_e)$；子句文字和监视项占用 $O(L_{\max})$。相加得到

$$
S_{\mathrm{total}}=O(nm+N_e+L_{\max}).
$$

当前版本不清理学习子句，$L_{\max}$ 可能随困难实例增长，故不能将搜索全过程内存仍写成初始公式的线性规模 $O(nm)$。
''')
    report=report.replace('图表和 PDF 生成另依赖 Pillow、ReportLab 及中文字体',
        '图表生成依赖 Pillow；PDF 排版依赖 Node.js、Playwright、Edge 和 MathJax、highlight.js，浏览器采用系统中文字体')
    report=report.replace('这两项文档库不参与求解和正确性判定；图像画布存储随像素数量线性增长。',
        '文档工具不参与求解和正确性判定。公式使用 LaTeX 语法，由 MathJax 生成矢量字形；代码由 highlight.js 着色。图像画布存储随像素数量线性增长，文字和公式排版量随文档内容增长。')
    return report
