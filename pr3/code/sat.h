/* 布尔可满足性求解接口。正文字编码为 2*v，负文字为 2*v+1；
 * 变量从 0 编号。内存分配失败写入标准错误并以非零状态退出，绝不报告无解。 */
#ifndef PR3_SAT_H
#define PR3_SAT_H
#include <stdint.h>

typedef struct Sat Sat;
typedef struct {
    uint64_t decisions, propagations, conflicts, learned, restarts;
    int variables, clauses;
} SatStats;

/* 一个实例仅求解一次；添加的子句须无重复变量和互补文字。空子句表示矛盾。 */
Sat *sat_create(int variables);
void sat_add_clause(Sat *solver, const int *literals, int count);
int sat_solve(Sat *solver);
/* 只在可满足时读取模型，返回变量的 0/1 值。 */
int sat_value(const Sat *solver, int variable);
SatStats sat_stats(const Sat *solver);
void sat_destroy(Sat *solver);
#endif
