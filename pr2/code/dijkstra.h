/*
 * dijkstra.h —— 两种优先队列共用的 Dijkstra 搜索接口声明。
 *
 * 本文件实现的功能：
 *   1. 定义堆种类枚举 HeapKind（二叉堆 / Fibonacci 堆）与操作计数结构
 *      SearchStats（定型顶点、扫描弧、首次插入、减小键值次数）；
 *   2. 定义搜索工作区 Search：距离、前驱、定型标记，两种堆各一份实例，
 *      初始化时只分配被选中的那一种；
 *   3. 声明工作区生命周期接口 search_init() / search_free()；
 *   4. 声明统一的搜索入口 dijkstra() 与堆名字转换 heap_name()。
 *
 * 设计要点：两种堆共用同一份距离数组与同一段松弛流程，只有堆操作不同，
 * 因此两条代码路径的差异只来自优先队列本身；工作区可跨查询复用，重置开销
 * 计入每次搜索。
 */
#ifndef DIJKSTRA_H
#define DIJKSTRA_H
#include "graph.h"
#include "binary_heap.h"
#include "fibonacci_heap.h"

/* 选择使用哪种优先队列，取值同时用于统计结果的分组。 */
typedef enum { HEAP_BINARY, HEAP_FIBONACCI } HeapKind;

/* 单次搜索的规模指标，用于核对两种实现是否探索了相同的工作量。
 * settled：已定型顶点数；scanned：扫描过的出弧数；
 * inserted：首次发现并入堆的次数；decreased：成功的 decrease-key 次数。 */
typedef struct 
{
    uint64_t settled, scanned, inserted, decreased;
} SearchStats;

/* 搜索工作区，可跨查询反复复用（顺序使用，不可多线程共享）。
 * capacity：顶点数，必须与所搜索图的顶点数一致；
 * kind：本工作区使用的堆类型；
 * distance：当前距离，DIST_INF 表示尚未发现；
 * previous：前驱顶点，-1 表示无（源点与不可达点均为 -1）；
 * settled：是否已定型（已出堆）；
 * binary/fibonacci：两种堆的实例，初始化时只有被选中的一种真正分配内存；
 * stats：本次搜索的计数，每次 dijkstra() 开始时清零。 */
typedef struct 
{
    int capacity;
    HeapKind kind;
    uint64_t *distance;
    int *previous;
    unsigned char *settled;
    BinaryHeap binary;
    FibonacciHeap fibonacci;
    SearchStats stats;
} Search;

/* 分配工作区并绑定堆与距离数组；顶点数非法或分配失败时返回 0。
 * 每个工作区只分配所选堆；工作区可跨查询复用，非线程共享。 */
int search_init(Search *search, int vertices, HeapKind kind);

/* 释放工作区（含两种堆的空壳）并清零；可重复调用。 */
void search_free(Search *search);

/* 执行一次 Dijkstra。返回 1 表示完成，0 表示参数不合法
 * （工作区容量与图不符，或 source/target 越界）。
 * target=-1 求单源全部距离；否则只保证目标距离与前驱链已最终确定。 */
int dijkstra(const Graph *graph, Search *search, int source, int target);

/* 返回堆类型对应的英文名（"binary"/"fibonacci"），用于 CSV 输出。 */
const char *heap_name(HeapKind kind);
#endif
