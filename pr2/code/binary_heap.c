/*
 * binary_heap.c —— 带位置映射的二叉最小堆实现。
 *
 * 本文件实现的功能：
 *   1. less()：统一的比较规则，先比距离、距离相同时比顶点编号；
 *   2. place()：把顶点写到堆的指定下标，并同步维护 position 反向映射；
 *   3. binary_init() / binary_reset() / binary_free()：分配、清空与释放；
 *   4. binary_update()：位置不存在时插入到末尾、存在时执行 decrease-key 上浮；
 *   5. binary_pop()：把末尾元素补到根位置后执行下沉，返回原根顶点。
 *
 * 复杂度与不变量：
 *   - 任一时刻堆内最多存在一个顶点条目，position[v] < 0 当且仅当 v 不在堆内；
 *   - items 始终满足堆序：父节点不大于任一孩子（按上述比较规则）；
 *   - items[i] 与 position[items[i]] 互为逆映射，place() 是唯一修改入口；
 *   - 插入、减小键值与删除最小值均为 O(log n)，且不涉及额外内存分配。
 */

#include "binary_heap.h"
#include "graph.h"
#include <stdlib.h>
#include <string.h>

/* 统一的元素比较：距离优先，距离相同时按顶点编号升序。
 * 平局规则固定后，两种堆在相同查询下的出堆顺序完全一致，便于公平比较。 */
static int less(const BinaryHeap *heap, int a, int b)
{
    return heap->distance[a] < heap->distance[b] ||
        (heap->distance[a] == heap->distance[b] && a < b);
}

/* 唯一的写入口：写 items[index] 的同时更新反向映射，避免两者不一致。 */
static void place(BinaryHeap *heap, int index, int vertex)
{
    heap->items[index] = vertex;
    heap->position[vertex] = index;
}

int binary_init(BinaryHeap *heap, int capacity, const uint64_t *distance)
{
    memset(heap, 0, sizeof(*heap));
    if (capacity <= 0) return 0;
    heap->capacity = capacity;
    heap->distance = distance;
    heap->items = array_alloc((size_t)capacity, sizeof(int));
    heap->position = array_alloc((size_t)capacity, sizeof(int));
    if (!heap->items || !heap->position) { binary_free(heap); return 0; }
    binary_reset(heap);
    return 1;
}

/* 复用内存的清空：size 归零，position 全为 -1（等价于"全部不在堆内"）。 */
void binary_reset(BinaryHeap *heap)
{
    heap->size = 0;
    for (int i = 0; i < heap->capacity; ++i) heap->position[i] = -1;
}

void binary_free(BinaryHeap *heap)
{
    free(heap->items);
    free(heap->position);
    memset(heap, 0, sizeof(*heap));
}

/* 插入或减小键值：新元素追加到末尾，已存在的元素从原位置出发上浮。
 * position 数组让 decrease-key 无需扫描或插入重复元素。 */
void binary_update(BinaryHeap *heap, int vertex)
{
    int index = heap->position[vertex];
    if (index < 0) index = heap->size++;
    /* 上浮：只要当前顶点比父亲小（或同距但编号更小）就与父亲交换位置，
     * 每次交换都通过 place() 同步两个方向的映射。 */
    while (index > 0) {
        int parent = (index - 1) / 2;
        if (!less(heap, vertex, heap->items[parent])) break;
        place(heap, index, heap->items[parent]);
        index = parent;
    }
    place(heap, index, vertex);
}

/* 删除最小值：堆顶出堆，末尾元素补到根，再逐层与较小的孩子交换下沉。
 * 返回被删除的顶点编号；空堆返回 -1。 */
int binary_pop(BinaryHeap *heap)
{
    int result, vertex, index = 0;
    if (!heap->size) return -1;
    result = heap->items[0];
    vertex = heap->items[--heap->size];
    heap->position[result] = -1;   /* 出堆顶点立刻与堆解绑。 */
    /* 使用 size/2 避免计算不存在的孩子时发生整数溢出。 */
    while (index < heap->size / 2) {
        int child = index * 2 + 1;
        if (child + 1 < heap->size && less(heap, heap->items[child + 1], heap->items[child])) ++child;
        if (!less(heap, heap->items[child], vertex)) break;
        place(heap, index, heap->items[child]);
        index = child;
    }
    /* 偶数大小的堆可能在最后一层只有一个左孩子，因此下沉循环外仍要补写；
     * size 为 0（原来只有一个元素）时无需写回。 */
    if (heap->size) place(heap, index, vertex);
    return result;
}
