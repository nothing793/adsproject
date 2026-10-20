/* 将栅栏恢复转换为布尔约束：连接器恰好选择 k 条边，交叉边不能同时选择。
 * 行列扫描保证候选边内部没有连接器；空格的横、纵占用表用于发现交叉。
 * 求解结果按边的两个端点同时写回方向状态，保持互反一致。 */
#include "fence.h"
#include <assert.h>
#include <string.h>

enum { UP, DOWN, LEFT, RIGHT };
enum { MAX_EDGES=2*FENCE_LIMIT*(FENCE_LIMIT-1) };
typedef struct { int row1, column1, row2, column2, direction; } Edge;
typedef struct {
    Edge edges[MAX_EDGES];
    int edge_count;
    int incident[FENCE_LIMIT][FENCE_LIMIT][4];
    int horizontal[FENCE_LIMIT][FENCE_LIMIT];
    int vertical[FENCE_LIMIT][FENCE_LIMIT];
} Model;

/* 单条候选边拥有两个方向端点，且在所有内部空格上登记相同变量编号。 */
static void add_edge(Model *model, int r1, int c1, int r2, int c2, int direction)
{
    int id=model->edge_count++, i;
    Edge *edge;
    assert(id<MAX_EDGES);
    edge=&model->edges[id]; edge->row1=r1; edge->column1=c1;
    edge->row2=r2; edge->column2=c2; edge->direction=direction;
    model->incident[r1][c1][direction]=id;
    model->incident[r2][c2][direction^1]=id;
    if (direction==RIGHT) {
        for (i=c1+1;i<c2;++i) model->horizontal[r1][i]=id;
    } else {
        for (i=r1+1;i<r2;++i) model->vertical[i][c1]=id;
    }
}

/* 子集至多四位，直接计数即可，无平台相关位运算函数依赖。 */
static int bit_count(unsigned value)
{
    int count=0;
    while (value) { count+=(int)(value&1U); value>>=1; }
    return count;
}

/* d<=4，可直接枚举至多 16 个子集。任意 k+1 条不能全真；
 * 任意 d-k+1 条不能全假。两组子句共同等价于恰好选择 k 条。 */
static void add_degree(Sat *solver, const int *variables, int available, int degree)
{
    unsigned mask;
    if (degree>available) { sat_add_clause(solver,NULL,0); return; }
    for (mask=1;mask<(1U<<available);++mask) {
        int count=bit_count(mask), literals[4], length=0, i;
        if (count==degree+1) {
            for (i=0;i<available;++i) if (mask&(1U<<i)) literals[length++]=2*variables[i]+1;
            sat_add_clause(solver,literals,length);
        }
        length=0;
        if (count==available-degree+1) {
            for (i=0;i<available;++i) if (mask&(1U<<i)) literals[length++]=2*variables[i];
            sat_add_clause(solver,literals,length);
        }
    }
}

/* 每个候选图连通分量的度数和必须为偶数；若分量可二染色，两侧的
 * 度数和还必须相等。这些必要条件只用于提前发现矛盾，不替代交叉约束。 */
static void add_component_checks(const Garden *garden, const Model *model, Sat *solver)
{
    int colors[FENCE_LIMIT][FENCE_LIMIT], queue[FENCE_LIMIT*FENCE_LIMIT];
    int r,c,d;
    for (r=0;r<garden->rows;++r) for (c=0;c<garden->columns;++c) colors[r][c]=-1;
    for (r=0;r<garden->rows;++r) for (c=0;c<garden->columns;++c)
        if (garden->degree[r][c] && colors[r][c]<0) {
            int head=0,tail=0,sum[2]={0,0},bipartite=1;
            colors[r][c]=0; queue[tail++]=r*FENCE_LIMIT+c;
            while (head<tail) {
                int cell=queue[head++], row=cell/FENCE_LIMIT, column=cell%FENCE_LIMIT;
                int color=colors[row][column];
                sum[color]+=garden->degree[row][column];
                for (d=0;d<4;++d) if (model->incident[row][column][d]>=0) {
                    const Edge *edge=&model->edges[model->incident[row][column][d]];
                    int nr=edge->row1,nc=edge->column1;
                    if (nr==row && nc==column) { nr=edge->row2; nc=edge->column2; }
                    if (colors[nr][nc]<0) {
                        colors[nr][nc]=color^1; queue[tail++]=nr*FENCE_LIMIT+nc;
                    } else if (colors[nr][nc]==color) bipartite=0;
                }
            }
            if (((sum[0]+sum[1])&1) || (bipartite && sum[0]!=sum[1]))
                sat_add_clause(solver,NULL,0);
        }
}

/* 完成建模、必要条件检查、精确求解和端点状态重建；空花园自然得到空模型。 */
int fence_solve(const Garden *garden, FenceResult *result)
{
    Model model;
    Sat *solver;
    int r,c,d,i,solved;
    memset(result,0,sizeof(*result)); memset(&model,0,sizeof(model));
    /* 不用 memset(-1) 假设有符号整数的表示；逐项设置无候选边的哨兵。 */
    for (r=0;r<garden->rows;++r) for (c=0;c<garden->columns;++c) {
        model.horizontal[r][c]=-1; model.vertical[r][c]=-1;
        for (d=0;d<4;++d) model.incident[r][c][d]=-1;
    }
    for (r=0;r<garden->rows;++r) {
        int previous=-1;
        for (c=0;c<garden->columns;++c) if (garden->degree[r][c]) {
            ++result->connectors;
            if (previous>=0) add_edge(&model,r,previous,r,c,RIGHT);
            previous=c;
        }
    }
    for (c=0;c<garden->columns;++c) {
        int previous=-1;
        for (r=0;r<garden->rows;++r) if (garden->degree[r][c]) {
            if (previous>=0) add_edge(&model,previous,c,r,c,DOWN);
            previous=r;
        }
    }
    result->edges=model.edge_count; solver=sat_create(model.edge_count);
    add_component_checks(garden,&model,solver);
    for (r=0;r<garden->rows;++r) for (c=0;c<garden->columns;++c) {
        if (garden->degree[r][c]) {
            int variables[4], count=0;
            for (d=0;d<4;++d) if (model.incident[r][c][d]>=0)
                variables[count++]=model.incident[r][c][d];
            add_degree(solver,variables,count,garden->degree[r][c]);
        } else if (model.horizontal[r][c]>=0 && model.vertical[r][c]>=0) {
            int literals[2]={2*model.horizontal[r][c]+1,2*model.vertical[r][c]+1};
            sat_add_clause(solver,literals,2); ++result->crossings;
        }
    }
    solved=sat_solve(solver); result->search=sat_stats(solver);
    if (solved) for (i=0;i<model.edge_count;++i) if (sat_value(solver,i)) {
        const Edge *edge=&model.edges[i];
        result->state[edge->row1][edge->column1][edge->direction]=1;
        result->state[edge->row2][edge->column2][edge->direction^1]=1;
    }
    sat_destroy(solver); return solved;
}
