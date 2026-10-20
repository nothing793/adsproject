/* 实现带双监视文字、First-UIP 冲突学习、非顺序回溯和活动度分支的 CDCL。
 * 子句和赋值轨迹分开存放；回溯只撤销赋值，不撤销逻辑蕴含的学习子句。
 * 算法说明参考 Een、Sorensson 的 SAT 2003 论文；本文件为独立 C99 实现。 */
#include "sat.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { int *data, count, capacity; } IntVector;
typedef struct { int *literals, count; } Clause;
struct Sat {
    int variables, inconsistent, solved;
    Clause *clauses;
    int clause_count, clause_capacity;
    IntVector *watches, trail, limits, learned;
    int head;
    signed char *values, *phases;
    int *levels, *reasons;
    unsigned char *seen;
    double *activity, increment;
    IntVector heap;
    int *heap_position;
    SatStats stats;
};

/* 所有分配统一检查。容量翻倍前检查整数范围，失败不能伪装成不可满足。 */
static void *checked_alloc(size_t count, size_t size)
{
    void *p;
    if (size && count > SIZE_MAX / size) {
        fputs("内存大小溢出\n", stderr); exit(2);
    }
    p = calloc(count ? count : 1, size);
    if (!p) { fputs("内存分配失败\n", stderr); exit(2); }
    return p;
}

/* 摊还常数时间追加；扩容复制后再释放旧缓冲区。 */
static void vector_push(IntVector *vector, int value)
{
    if (vector->count == vector->capacity) {
        int capacity;
        int *data;
        if (vector->capacity > INT_MAX / 2) {
            fputs("向量容量溢出\n", stderr); exit(2);
        }
        capacity = vector->capacity ? 2 * vector->capacity : 8;
        data = checked_alloc((size_t)capacity, sizeof(*data));
        if (vector->count) memcpy(data, vector->data,
                                 (size_t)vector->count * sizeof(*data));
        free(vector->data); vector->data = data; vector->capacity = capacity;
    }
    vector->data[vector->count++] = value;
}

/* 最大堆只决定搜索顺序，不参与正确性判定；同活动度时优先小编号。 */
static int preferred(const Sat *s, int a, int b)
{
    return s->activity[a] > s->activity[b] ||
           (s->activity[a] == s->activity[b] && a < b);
}

/* 同时维护反向位置表，保证活动度增加后能直接定位堆元素。 */
static void heap_swap(Sat *s, int a, int b)
{
    int x = s->heap.data[a];
    s->heap.data[a] = s->heap.data[b]; s->heap.data[b] = x;
    s->heap_position[s->heap.data[a]] = a;
    s->heap_position[s->heap.data[b]] = b;
}

/* 插入或增大活动度时，仅沿父链修复最大堆。 */
static void heap_up(Sat *s, int index)
{
    while (index && preferred(s, s->heap.data[index], s->heap.data[(index-1)/2])) {
        int parent = (index-1)/2;
        heap_swap(s, index, parent); index = parent;
    }
}

/* 同一变量最多在堆中出现一次；回溯时允许将已弹出的变量重新入堆。 */
static void heap_insert(Sat *s, int variable)
{
    if (s->heap_position[variable] >= 0) return;
    vector_push(&s->heap, variable);
    s->heap_position[variable] = s->heap.count-1;
    heap_up(s, s->heap.count-1);
}

/* 删除最高优先级变量，以末项补根并向下调整。调用前堆必须非空。 */
static int heap_remove_top(Sat *s)
{
    int result = s->heap.data[0], index = 0;
    s->heap_position[result] = -1;
    --s->heap.count;
    if (!s->heap.count) return result;
    s->heap.data[0] = s->heap.data[s->heap.count];
    s->heap_position[s->heap.data[0]] = 0;
    for (;;) {
        int left = 2*index+1, best = index;
        if (left < s->heap.count && preferred(s, s->heap.data[left], s->heap.data[best])) best=left;
        if (left+1 < s->heap.count && preferred(s, s->heap.data[left+1], s->heap.data[best])) best=left+1;
        if (best == index) break;
        heap_swap(s, index, best); index=best;
    }
    return result;
}

/* 初始所有变量未赋值，默认分支相位为假，原因编号 -1 表示无推导原因。 */
Sat *sat_create(int variables)
{
    Sat *s;
    int i;
    assert(variables >= 0 && variables <= INT_MAX/2);
    s = checked_alloc(1, sizeof(*s)); s->variables=variables; s->increment=1.0;
    s->watches=checked_alloc((size_t)variables*2, sizeof(*s->watches));
    s->values=checked_alloc((size_t)variables, sizeof(*s->values));
    s->phases=checked_alloc((size_t)variables, sizeof(*s->phases));
    s->levels=checked_alloc((size_t)variables, sizeof(*s->levels));
    s->reasons=checked_alloc((size_t)variables, sizeof(*s->reasons));
    s->seen=checked_alloc((size_t)variables, sizeof(*s->seen));
    s->activity=checked_alloc((size_t)variables, sizeof(*s->activity));
    s->heap_position=checked_alloc((size_t)variables, sizeof(*s->heap_position));
    for (i=0; i<variables; ++i) {
        s->values[i]=-1; s->reasons[i]=-1; s->heap_position[i]=-1;
    }
    s->stats.variables=variables;
    return s;
}

/* 未赋值返回 -1，其他返回文字本身的真值；取反只改变最低位。 */
static int literal_value(const Sat *s, int literal)
{
    int value=s->values[literal/2];
    return value<0 ? -1 : value^(literal&1);
}

/* 已有相同赋值时不重复入队；已有相反赋值时返回冲突。 */
static int enqueue(Sat *s, int literal, int reason)
{
    int variable=literal/2, value=literal_value(s, literal);
    if (value>=0) return value;
    s->values[variable]=(signed char)(1-(literal&1));
    s->phases[variable]=s->values[variable];
    s->levels[variable]=s->limits.count; s->reasons[variable]=reason;
    vector_push(&s->trail, literal);
    return 1;
}

/* 子句独立拥有文字数组；单位子句不需要监视项，由调用方直接入队。 */
static int store_clause(Sat *s, const int *literals, int count)
{
    Clause *clause;
    int id=s->clause_count;
    if (s->clause_count==s->clause_capacity) {
        int capacity;
        Clause *clauses;
        if (s->clause_capacity>INT_MAX/2) {
            fputs("子句容量溢出\n",stderr); exit(2);
        }
        capacity=s->clause_capacity ? 2*s->clause_capacity : 64;
        clauses=checked_alloc((size_t)capacity,sizeof(*clauses));
        if (s->clause_count) memcpy(clauses,s->clauses,
                                  (size_t)s->clause_count*sizeof(*clauses));
        free(s->clauses); s->clauses=clauses; s->clause_capacity=capacity;
    }
    clause=&s->clauses[s->clause_count++]; clause->count=count;
    clause->literals=checked_alloc((size_t)count,sizeof(*literals));
    if (count) memcpy(clause->literals,literals,(size_t)count*sizeof(*literals));
    if (count>=2) {
        vector_push(&s->watches[literals[0]],id);
        vector_push(&s->watches[literals[1]],id);
    }
    return id;
}

/* 记录原始公式，并立即保存单位条件；空子句或相反单位条件使公式矛盾。 */
void sat_add_clause(Sat *s, const int *literals, int count)
{
    int i, id;
    assert(!s->solved && count>=0);
    for (i=0;i<count;++i) {
        assert(literals[i]>=0 && literals[i]<2*s->variables);
        s->activity[literals[i]/2]+=1.0;
    }
    id=store_clause(s,literals,count); ++s->stats.clauses;
    if (!count || (count==1 && !enqueue(s,literals[0],id))) s->inconsistent=1;
}

/* 双监视不变量：非单位子句监视前两个文字。仅在其中一个变假时检查；
 * 找到非假替代项就迁移监视，否则另一个文字必须为真或成为单位推导。 */
static int propagate(Sat *s)
{
    while (s->head<s->trail.count) {
        int false_literal=s->trail.data[s->head++]^1;
        IntVector *watch=&s->watches[false_literal];
        int read, write=0, total=watch->count;
        ++s->stats.propagations;
        for (read=0;read<total;++read) {
            int id=watch->data[read], k, other;
            Clause *clause=&s->clauses[id];
            int *literals=clause->literals;
            if (literals[0]==false_literal) {
                int temp=literals[0]; literals[0]=literals[1]; literals[1]=temp;
            }
            assert(literals[1]==false_literal);
            other=literals[0];
            if (literal_value(s,other)==1) { watch->data[write++]=id; continue; }
            for (k=2;k<clause->count;++k) if (literal_value(s,literals[k])!=0) break;
            if (k<clause->count) {
                int replacement=literals[k]; literals[k]=false_literal; literals[1]=replacement;
                vector_push(&s->watches[replacement],id); continue;
            }
            watch->data[write++]=id;
            if (!enqueue(s,other,id)) {
                /* 冲突时仍须保留尚未扫描的监视项，供回溯后使用。 */
                while (++read<total) watch->data[write++]=watch->data[read];
                watch->count=write; return id;
            }
        }
        watch->count=write;
    }
    return -1;
}

/* 冲突涉及的变量提高优先级；统一缩放避免浮点溢出，不改变大小关系。 */
static void bump_activity(Sat *s, int variable)
{
    int i;
    s->activity[variable]+=s->increment;
    if (s->activity[variable]>1e100) {
        for (i=0;i<s->variables;++i) s->activity[i]*=1e-100;
        s->increment*=1e-100;
    }
    if (s->heap_position[variable]>=0) heap_up(s,s->heap_position[variable]);
}

/* 对当前层反向消解，直至只剩一个当前层文字（First UIP）。学习子句是
 * 原公式的逻辑后果；第二个文字置为最高的较低决策层，以确定回跳目标。 */
static int analyze(Sat *s, int conflict)
{
    int pending=0, pivot=-1, index=s->trail.count-1, i, backtrack=0;
    s->learned.count=0; vector_push(&s->learned,0);
    do {
        Clause *clause=&s->clauses[conflict];
        for (i=0;i<clause->count;++i) {
            int literal=clause->literals[i], variable=literal/2;
            if (variable==pivot/2 && pivot>=0) continue;
            if (s->seen[variable] || !s->levels[variable]) continue;
            s->seen[variable]=1; bump_activity(s,variable);
            if (s->levels[variable]==s->limits.count) ++pending;
            else vector_push(&s->learned,literal);
        }
        while (index>=0 && !s->seen[s->trail.data[index]/2]) --index;
        assert(index>=0 && pending>0);
        pivot=s->trail.data[index--]; s->seen[pivot/2]=0; --pending;
        conflict=s->reasons[pivot/2];
        assert(!pending || conflict>=0);
    } while (pending);
    s->learned.data[0]=pivot^1;
    if (s->learned.count>1) {
        int best=1, temp;
        for (i=2;i<s->learned.count;++i)
            if (s->levels[s->learned.data[i]/2]>s->levels[s->learned.data[best]/2]) best=i;
        temp=s->learned.data[1]; s->learned.data[1]=s->learned.data[best];
        s->learned.data[best]=temp; backtrack=s->levels[s->learned.data[1]/2];
    }
    for (i=0;i<s->learned.count;++i) s->seen[s->learned.data[i]/2]=0;
    s->increment/=0.95;
    return backtrack;
}

/* limits[level] 是 level+1 层的首个轨迹位置；0 层单位赋值始终保留。 */
static void cancel_until(Sat *s, int level)
{
    int boundary, i;
    if (s->limits.count<=level) return;
    boundary=s->limits.data[level];
    for (i=s->trail.count-1;i>=boundary;--i) {
        int variable=s->trail.data[i]/2;
        s->values[variable]=-1; s->reasons[variable]=-1;
        heap_insert(s,variable);
    }
    s->trail.count=boundary; s->head=boundary; s->limits.count=level;
}

/* 传播优先；有冲突则学习并回跳，否则选择未赋值变量。重启保留学习子句
 * 和相位，不删除子句；无决策层的冲突才是全局不可满足的证明。 */
int sat_solve(Sat *s)
{
    uint64_t since_restart=0, restart_budget=100;
    int i;
    assert(!s->solved); s->solved=1;
    if (s->inconsistent) return 0;
    for (i=0;i<s->variables;++i) heap_insert(s,i);
    for (;;) {
        int conflict=propagate(s);
        if (conflict>=0) {
            int backtrack, id;
            ++s->stats.conflicts; ++since_restart;
            if (!s->limits.count) return 0;
            backtrack=analyze(s,conflict); cancel_until(s,backtrack);
            id=store_clause(s,s->learned.data,s->learned.count); ++s->stats.learned;
            if (!enqueue(s,s->learned.data[0],id)) return 0;
        } else {
            int variable=-1;
            if (since_restart>=restart_budget) {
                cancel_until(s,0); ++s->stats.restarts; since_restart=0;
                if (restart_budget<50000) restart_budget+=restart_budget/2;
            }
            while (s->heap.count) {
                int next=heap_remove_top(s);
                if (s->values[next]<0) { variable=next; break; }
            }
            if (variable<0) return 1;
            vector_push(&s->limits,s->trail.count); ++s->stats.decisions;
            (void)enqueue(s,2*variable+(s->phases[variable] ? 0 : 1),-1);
        }
    }
}

/* 可满足模型中的变量值；调用者保证变量编号有效。 */
int sat_value(const Sat *s, int variable) { return s->values[variable]; }
/* 复制统计值，调用者可在释放实例后继续使用。 */
SatStats sat_stats(const Sat *s) { return s->stats; }

/* 逐个释放子句和监视向量，再释放求解器拥有的所有工作数组。 */
void sat_destroy(Sat *s)
{
    int i;
    if (!s) return;
    for (i=0;i<s->clause_count;++i) free(s->clauses[i].literals);
    for (i=0;i<2*s->variables;++i) free(s->watches[i].data);
    free(s->clauses); free(s->watches); free(s->values); free(s->phases);
    free(s->levels); free(s->reasons); free(s->seen); free(s->activity);
    free(s->heap.data); free(s->heap_position); free(s->trail.data);
    free(s->limits.data); free(s->learned.data); free(s);
}
