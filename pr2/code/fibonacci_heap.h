/*
 * fibonacci_heap.h —— 数组化 Fibonacci 堆接口与节点结构声明。
 *
 * 本文件实现的功能：
 *   1. 定义堆节点 FibonacciNode：父亲、一个孩子、左右兄弟、孩子度数 degree、
 *      丢孩子标记 mark 与在堆标记 active；
 *   2. 定义堆结构 FibonacciHeap：节点数组、堆内元素个数与最小根编号；
 *   3. 声明生命周期接口 fibonacci_init() / fibonacci_reset() / fibonacci_free()；
 *   4. 声明 Dijkstra 需要的两个操作：fibonacci_update()（插入或减小键值）与
 *      fibonacci_pop()（取出并删除最小顶点）。
 *
 * 设计要点：节点存放在大小为"图顶点数"的数组里，顶点编号即句柄，因此插入
 * 和 decrease-key 都不需要额外分配节点；根链表与每组兄弟节点都是双向循环
 * 链表，用左右兄弟下标表达链接关系（见 fibonacci_heap.c）。
 */
#ifndef FIBONACCI_HEAP_H
#define FIBONACCI_HEAP_H
#include <stdint.h>

/* Fibonacci 堆节点。
 * parent/child/left/right：父亲下标、一个孩子下标、左右兄弟下标；-1 表示无。
 * degree：该节点的孩子数，consolidate() 的度数表以它为索引；
 * mark：非根节点是否已经丢失过一个孩子（用于级联切割的摊还分析）；
 * active：该顶点当前是否在堆内，同时区分"未插入"与"已插入"两种更新请求。 */
typedef struct {
    int parent, child, left, right, degree;
    unsigned char mark, active;
} FibonacciNode;

/* Fibonacci 堆。
 * capacity：节点数组长度，等于图顶点数，也等于可同时存在的句柄数；
 * size：当前堆内元素个数；
 * minimum：最小根（按距离、顶点编号比较）的下标，空堆为 -1；
 * nodes：节点数组，下标即顶点编号；
 * distance：指向外部距离数组的只读指针，堆必须比它先释放。 */
typedef struct {
    int capacity, size, minimum;
    FibonacciNode *nodes;
    const uint64_t *distance;
} FibonacciHeap;

/* 初始化：绑定距离数组并分配节点数组；capacity <= 0 或分配失败时返回 0
 * （此时堆为可安全释放的空壳）。distance 必须比堆活得更久。 */
int fibonacci_init(FibonacciHeap *heap, int capacity, const uint64_t *distance);

/* 清空堆：minimum 置 -1、size 置 0，并清除所有节点的 active 标记。
 * 搜索结束时堆里可能仍有未定型的候选节点，因此下一次插入必须重新初始化
 * 被复用的节点字段。 */
void fibonacci_reset(FibonacciHeap *heap);

/* 释放节点数组并清零结构体；可重复调用。 */
void fibonacci_free(FibonacciHeap *heap);

/* 插入顶点或减小其键值；顶点编号即句柄，distance 已由调用者严格减小，
 * 或顶点尚未插入（由 active 标记区分）。前置条件：0 <= vertex < capacity。 */
void fibonacci_update(FibonacciHeap *heap, int vertex);

/* 取出并删除最小顶点，返回其编号；空堆返回 -1。
 * 删除时把孩子提升为根并做按度合并，摊还 O(log n)。 */
int fibonacci_pop(FibonacciHeap *heap);
#endif
