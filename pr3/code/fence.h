/* 栅栏模型：同一行/列相邻的非零连接器之间建立一条候选边。
 * state 顺序固定为上、下、左、右；数组使用从 0 开始的内部下标。 */
#ifndef PR3_FENCE_H
#define PR3_FENCE_H
#include "sat.h"
#define FENCE_LIMIT 50
typedef struct {
    int rows, columns;
    int degree[FENCE_LIMIT][FENCE_LIMIT];
} Garden;
typedef struct {
    int state[FENCE_LIMIT][FENCE_LIMIT][4];
    int connectors, edges, crossings;
    SatStats search;
} FenceResult;

/* 返回 1 表示构造成功，0 表示已证明无解；输入须通过 main 的范围检查。 */
int fence_solve(const Garden *garden, FenceResult *result);
#endif
