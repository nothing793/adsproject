/*
 * graph.h —— DIMACS 最短路图的存储结构与读取接口声明。
 *
 * 本文件实现的功能：
 *   1. 声明只读 CSR（压缩稀疏行）图结构 Graph：顶点数、有向弧数、出弧偏移
 *      数组以及与之平行的弧终点数组、弧权数组；
 *   2. 声明图文件的读取与释放接口 graph_load() 与 graph_free()；
 *   3. 声明被多个模块共用的辅助函数 parse_uint64()（严格十进制解析）与
 *      array_alloc()（带回绕检查的零初始化分配）；
 *   4. 定义"不可达"距离常量 DIST_INF。
 *
 * 约定与限制：
 *   - DIMACS 文件中的顶点编号为 1..n，内存中的编号为 0..n-1；
 *   - 保留输入弧的方向、重边、自环与零权边，不把有向边改成无向边；
 *   - 弧权为非负 64 位整数；负权不满足 Dijkstra 的前提，加载阶段即被拒绝；
 *   - DIST_INF 只用作不可达标记，不是有限距离，不参与距离累加。
 */
#ifndef GRAPH_H
#define GRAPH_H

#include <stddef.h>
#include <stdint.h>

/* 距离上界，同时充当"不可达"标记。graph_load() 限制了弧权大小，
 * 保证任意简单路径的距离都严格小于该值，因此该标记不会被真实距离占用。 */
#define DIST_INF UINT64_MAX

/* CSR 只读图（构造完成后不再修改，多个搜索工作区共享同一份）。
 * vertices：顶点数 n，内存编号为 0..n-1；
 * arcs：有向弧数 m，与 target/weight 的长度一致；
 * offset：长度 n+1；顶点 u 的出弧区间为 [offset[u], offset[u+1])，
 *         且 offset[n] == m，方便用 [offset[u], offset[u+1]) 统一遍历；
 * target/weight：长度 m；第 i 条弧的终点为 target[i]、权为 weight[i]。
 * 弧按起点分组存放，组内保持文件中的出现顺序。 */
typedef struct
{
    int vertices;
    size_t arcs;
    size_t *offset;
    int *target;
    uint64_t *weight;
} Graph;

/* 读取 DIMACS 图文件并构造 CSR。
 * 成功返回 1；失败返回 0，把 "line N: 原因" 写入 error（长度 error_size，
 * 过长时截断），并且已经释放内部临时内存、把 graph 清零，调用者无需再
 * 对其调用 graph_free()。 */
int graph_load(Graph *graph, const char *path, char *error, size_t error_size);

/* 释放图内三个数组并把结构体清零；对已释放对象重复调用是安全的。 */
void graph_free(Graph *graph);

/* 严格解析十进制非负整数：拒绝空串、负号、正号、前导空白、非数字字符和
 * 溢出。成功返回 1 并写回 value；失败返回 0 且不修改 value。 */
int parse_uint64(const char *text, uint64_t *value);

/* 分配 count 个元素、每个 element_size 字节的零初始化数组；count 为 0 时也
 * 返回可安全 free 的指针。乘积溢出或内存不足时返回 NULL。 */
void *array_alloc(size_t count, size_t element_size);

#endif
