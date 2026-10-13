/*
 * binary_heap.h —— 带位置映射的二叉最小堆接口声明。
 *
 * 本文件实现的功能：
 *   1. 定义二叉堆结构 BinaryHeap：层序数组 items、顶点到下标的反向映射
 *      position，以及指向共享距离数组的只读指针 distance；
 *   2. 声明生命周期接口 binary_init() / binary_reset() / binary_free()；
 *   3. 声明 Dijkstra 需要的两个操作：binary_update()（插入或减小键值）与
 *      binary_pop()（取出并删除最小顶点）。
 *
 * 设计要点：堆内只保存顶点编号，键值一律从共享的 distance 数组读取，因此
 * decrease-key 只需改动 distance 再调用 binary_update()，不需要复制键值。
 * position 的存在使该操作 O(log n) 完成，无需线性查找或插入重复条目。
 */
#ifndef BINARY_HEAP_H
#define BINARY_HEAP_H
#include <stdint.h>

/* 二叉最小堆（层序存储的完全二叉树）。
 * capacity：容量，最大同时存在的顶点数（等于图的顶点数）；
 * size：当前元素个数，items[0..size-1] 有效；
 * items：堆数组，下标 i 的孩子为 2i+1、2i+2，父亲为 (i-1)/2；
 * position：长度为 capacity 的反向映射，position[v] 是顶点 v 在 items 中的
 *           下标，-1 表示 v 不在堆内（这是"是否已入堆"的唯一判据）；
 * distance：指向外部距离数组的只读指针，堆必须比它先释放。
 * 元素之间按 (distance, 顶点编号) 比较，保证同距顶点的出堆顺序唯一。 */
typedef struct 
{
    int capacity, size;
    int *items, *position;
    const uint64_t *distance;
} BinaryHeap;

/* 初始化堆并绑定距离数组；capacity <= 0 或分配失败时返回 0（此时堆为空壳，
 * 仍可安全调用 binary_free()）。distance 必须比堆活得更久。 */
int binary_init(BinaryHeap *heap, int capacity, const uint64_t *distance);

/* 清空堆：size 置 0 并把 position 全部重置为 -1，保留已分配的内存以便复用。 */
void binary_reset(BinaryHeap *heap);

/* 释放内部数组并清零结构体；可重复调用。 */
void binary_free(BinaryHeap *heap);

/* 插入顶点或减小其键值（调用者必须先更新 distance）。
 * 两种情形在 position[vertex] 上区分：不在堆内则新插入，已在堆内则上浮。
 * 前置条件：0 <= vertex < capacity，且已入堆顶点的键值只会严格减小。 */
void binary_update(BinaryHeap *heap, int vertex);

/* 取出并删除最小顶点，返回其编号；空堆返回 -1。 */
int binary_pop(BinaryHeap *heap);
#endif
