#include "fibonacci_heap.h"
#include "graph.h"
#include <assert.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

/* 最大度数 < 2 log2(n)；容量由 int 表示，表长因此有静态上界。 */
#define DEGREE_SLOTS (2 * sizeof(int) * CHAR_BIT + 1)

static int less(const FibonacciHeap *heap, int a, int b)
{
    return heap->distance[a] < heap->distance[b] ||
        (heap->distance[a] == heap->distance[b] && a < b);
}

/* 从双向循环链表摘下 x，使它成为单节点循环链表。 */
static void detach(FibonacciHeap *heap, int x)
{
    FibonacciNode *nodes = heap->nodes;
    nodes[nodes[x].left].right = nodes[x].right;
    nodes[nodes[x].right].left = nodes[x].left;
    nodes[x].left = nodes[x].right = x;
}

static void insert_after(FibonacciHeap *heap, int anchor, int x)
{
    FibonacciNode *nodes = heap->nodes;
    nodes[x].left = anchor;
    nodes[x].right = nodes[anchor].right;
    nodes[nodes[anchor].right].left = x;
    nodes[anchor].right = x;
}

static void add_root(FibonacciHeap *heap, int x)
{
    heap->nodes[x].parent = -1;
    heap->nodes[x].mark = 0;
    if (heap->minimum < 0) {
        heap->nodes[x].left = heap->nodes[x].right = x;
        heap->minimum = x;
    } else {
        insert_after(heap, heap->minimum, x);
        if (less(heap, x, heap->minimum)) heap->minimum = x;
    }
}

int fibonacci_init(FibonacciHeap *heap, int capacity, const uint64_t *distance)
{
    memset(heap, 0, sizeof(*heap));
    heap->minimum = -1;
    if (capacity <= 0) return 0;
    heap->capacity = capacity;
    heap->distance = distance;
    heap->nodes = array_alloc((size_t)capacity, sizeof(*heap->nodes));
    return heap->nodes != NULL;
}

void fibonacci_reset(FibonacciHeap *heap)
{
    heap->minimum = -1;
    heap->size = 0;
    /* 查询结束可能仍有候选节点；清 active 后插入时重新初始化节点。 */
    for (int i = 0; i < heap->capacity; ++i) heap->nodes[i].active = 0;
}

void fibonacci_free(FibonacciHeap *heap)
{
    free(heap->nodes);
    memset(heap, 0, sizeof(*heap));
    heap->minimum = -1;
}

static void cut(FibonacciHeap *heap, int x, int parent)
{
    FibonacciNode *nodes = heap->nodes;
    if (nodes[parent].child == x)
        nodes[parent].child = nodes[x].right == x ? -1 : nodes[x].right;
    detach(heap, x);
    --nodes[parent].degree;
    add_root(heap, x);
}

void fibonacci_update(FibonacciHeap *heap, int vertex)
{
    FibonacciNode *nodes = heap->nodes;
    int parent;
    if (!nodes[vertex].active) {
        nodes[vertex].parent = nodes[vertex].child = -1;
        nodes[vertex].left = nodes[vertex].right = vertex;
        nodes[vertex].degree = 0;
        nodes[vertex].mark = 0;
        nodes[vertex].active = 1;
        ++heap->size;
        add_root(heap, vertex);
        return;
    }
    parent = nodes[vertex].parent;
    if (parent >= 0 && less(heap, vertex, parent)) {
        cut(heap, vertex, parent);
        /* 非根第一次丢孩子只标记；第二次丢孩子切断并向上继续。 */
        while (nodes[parent].parent >= 0) {
            int ancestor = nodes[parent].parent;
            if (!nodes[parent].mark) { nodes[parent].mark = 1; break; }
            cut(heap, parent, ancestor);
            parent = ancestor;
        }
    }
    if (less(heap, vertex, heap->minimum)) heap->minimum = vertex;
}

static void consolidate(FibonacciHeap *heap)
{
    int table[DEGREE_SLOTS];
    FibonacciNode *nodes = heap->nodes;
    for (size_t i = 0; i < DEGREE_SLOTS; ++i) table[i] = -1;
    /* 逐个消耗原根链表，再由度数表重建，避免遍历中合并破坏迭代器。 */
    while (heap->minimum >= 0) {
        int x = heap->minimum, degree;
        heap->minimum = nodes[x].right == x ? -1 : nodes[x].right;
        detach(heap, x);
        degree = nodes[x].degree;
        assert((size_t)degree < DEGREE_SLOTS);
        while (table[degree] >= 0) {
            int y = table[degree];
            if (less(heap, y, x)) { int swap = x; x = y; y = swap; }
            table[degree] = -1;
            nodes[y].parent = x;
            nodes[y].mark = 0;
            if (nodes[x].child < 0) nodes[x].child = y;
            else insert_after(heap, nodes[x].child, y);
            degree = ++nodes[x].degree;
            assert((size_t)degree < DEGREE_SLOTS);
        }
        table[degree] = x;
    }
    for (size_t i = 0; i < DEGREE_SLOTS; ++i)
        if (table[i] >= 0) add_root(heap, table[i]);
}

int fibonacci_pop(FibonacciHeap *heap)
{
    int result = heap->minimum;
    FibonacciNode *nodes = heap->nodes;
    if (result < 0) return -1;
    /* 最小根的孩子全部提升为根，根不保留 mark。 */
    while (nodes[result].child >= 0) {
        int child = nodes[result].child;
        nodes[result].child = nodes[child].right == child ? -1 : nodes[child].right;
        detach(heap, child);
        add_root(heap, child);
    }
    heap->minimum = nodes[result].right == result ? -1 : nodes[result].right;
    detach(heap, result);
    nodes[result].active = 0;
    nodes[result].degree = 0;
    --heap->size;
    if (heap->minimum >= 0) consolidate(heap);
    return result;
}
