/*
 * fibonacci_heap.c —— 数组化 Fibonacci 最小堆的实现。
 *
 * 本文件实现的功能：
 *   1. 链表原语：detach()（从双向循环链表摘下节点）与 insert_after()（把节点
 *      插到指定节点之后）；
 *   2. add_root()：把节点设为根并接入根链表，必要时更新 minimum；
 *   3. fibonacci_init() / fibonacci_reset() / fibonacci_free()：分配、清空与释放；
 *   4. cut()：把节点从父亲的孩子链表切到根链表（decrease-key 与级联切割共用）；
 *   5. fibonacci_update()：新顶点插入根链表；已入堆顶点则在键值小于父亲时切割，
 *      并对父亲执行级联切割；
 *   6. consolidate()：删除最小值后按度数合并根链表，重建最小根；
 *   7. fibonacci_pop()：把孩子提升为根、摘除最小根，再调用 consolidate()。
 *
 * 关键设计与不变量：
 *   - 节点存放在大小为图顶点数的数组里，下标即顶点编号（稳定句柄），插入与
 *     decrease-key 都不分配新节点；
 *   - 根链表和每个孩子链表都是双向循环链表，left/right 必须互逆；
 *   - 只有非根节点会带 mark，表示它已丢失一个孩子（第二个孩子被切走时切除；
 *     该节点本身，从而把成本沿树向上摊还）；
 *   - active 表示节点在堆内，size 与 active 为真的节点数一致，minimum 指向
 *     这些节点中真正的最小根（空堆为 -1）。
 */

#include "fibonacci_heap.h"
#include "graph.h"
#include <assert.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

/* 按度合并时度数表的槽数；最大度数 < 2 log2(n)；容量由 int 表示，表长因此
 * 有静态上界，可以放在栈上而无需动态分配。 */
#define DEGREE_SLOTS (2 * sizeof(int) * CHAR_BIT + 1)

/* 与二叉堆完全相同的比较规则：距离优先，距离相同时按顶点编号升序。 */
static int less(const FibonacciHeap *heap, int a, int b)
{
    return heap->distance[a] < heap->distance[b] ||
        (heap->distance[a] == heap->distance[b] && a < b);
}

/* 从双向循环链表摘下 x，使它成为单节点循环链表（x 自身的父亲/孩子字段不动，
 * 由调用者负责重设，例如 add_root() 或挂到新父亲下之前）。 */
static void detach(FibonacciHeap *heap, int x)
{
    FibonacciNode *nodes = heap->nodes;
    nodes[nodes[x].left].right = nodes[x].right;
    nodes[nodes[x].right].left = nodes[x].left;
    nodes[x].left = nodes[x].right = x;
}

/* 把单节点环 x 插到 anchor 之后，保持 anchor 所在环的循环结构。 */
static void insert_after(FibonacciHeap *heap, int anchor, int x)
{
    FibonacciNode *nodes = heap->nodes;
    nodes[x].left = anchor;
    nodes[x].right = nodes[anchor].right;
    nodes[nodes[anchor].right].left = x;
    nodes[anchor].right = x;
}

/* 把 x 接入根链表：清父亲、清 mark（根不带标记）。
 * 空堆时 x 自成环并成为 minimum，否则插到原 minimum 之后并按需更新 minimum。 */
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
    heap->minimum = -1;   /* memset 后为 0，先置为"空堆"状态。 */
    if (capacity <= 0) return 0;
    heap->capacity = capacity;
    heap->distance = distance;
    heap->nodes = array_alloc((size_t)capacity, sizeof(*heap->nodes));
    return heap->nodes != NULL;
}

/* 复用内存的清空：只需要清 active（插入时会重新初始化其余节点字段），
 * 因此不必遍历重置所有兄弟指针，清空开销为 O(n)。 */
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

/* 把 x 从父亲 parent 的孩子链表中切下并挂到根链表：
 * 若 x 原是唯一孩子，则父亲的孩子指针置 -1，否则改指其右兄弟；
 * 摘链后父亲度数减一，x 成为新根。mark 由 add_root() 清除。 */
static void cut(FibonacciHeap *heap, int x, int parent)
{
    FibonacciNode *nodes = heap->nodes;
    if (nodes[parent].child == x)
        nodes[parent].child = nodes[x].right == x ? -1 : nodes[x].right;
    detach(heap, x);
    --nodes[parent].degree;
    add_root(heap, x);
}

/* 插入新顶点，或对已入堆顶点执行 decrease-key（含级联切割）。
 * 调用者保证：未入堆顶点是首次被发现；已入堆顶点的距离只会严格减小。 */
void fibonacci_update(FibonacciHeap *heap, int vertex)
{
    FibonacciNode *nodes = heap->nodes;
    int parent;
    if (!nodes[vertex].active) {
        /* 首次插入：节点字段可能是上一次查询的残留，这里整体重新初始化，
         * 再作为单节点根接入根链表。 */
        nodes[vertex].parent = nodes[vertex].child = -1;
        nodes[vertex].left = nodes[vertex].right = vertex;
        nodes[vertex].degree = 0;
        nodes[vertex].mark = 0;
        nodes[vertex].active = 1;
        ++heap->size;
        add_root(heap, vertex);
        return;
    }
    /* decrease-key：只有违反堆序（键值已小于父亲）才需要切割。 */
    parent = nodes[vertex].parent;
    if (parent >= 0 && less(heap, vertex, parent)) {
        cut(heap, vertex, parent);
        /* 非根第一次丢孩子只标记；第二次丢孩子切断并向上继续。 */
        while (nodes[parent].parent >= 0) {
            int ancestor = nodes[parent].parent;
            if (!nodes[parent].mark) { nodes[parent].mark = 1; break; }
            cut(heap, parent, ancestor);   /* 级联切割：父节点已被标记过。 */
            parent = ancestor;
        }
    }
    /* 键值减小后顶点可能成为新的最小根（也可能仍在别人孩子下，不参与比较）。 */
    if (less(heap, vertex, heap->minimum)) heap->minimum = vertex;
}

/* 按度合并根链表，使每个度数最多保留一个根，并重建 minimum。
 * 做法：逐个把根从根链表摘下（每摘一个就更新 heap->minimum 指向剩余根），
 * 度数冲突时把较大的根挂到较小的根下；最后按度数表重建根链表。 */
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
            /* 同度合并：small 为较小的根，big 被挂到它名下成为孩子。 */
            int y = table[degree];
            if (less(heap, y, x)) { int swap = x; x = y; y = swap; }
            table[degree] = -1;
            nodes[y].parent = x;
            nodes[y].mark = 0;   /* 成为孩子后重新开始计丢失的孩子数。 */
            if (nodes[x].child < 0) nodes[x].child = y;
            else insert_after(heap, nodes[x].child, y);
            degree = ++nodes[x].degree;
            assert((size_t)degree < DEGREE_SLOTS);
        }
        table[degree] = x;
    }
    /* 度数表里每个槽至多一个根，按槽序接回根链表，顺带确定 minimum。 */
    for (size_t i = 0; i < DEGREE_SLOTS; ++i)
        if (table[i] >= 0) add_root(heap, table[i]);
}

/* 删除最小根：先把它所有孩子提升为根，再从根链表摘除并标记为非活跃，
 * 最后做一次按度合并。返回被删除的顶点编号。 */
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
    /* 摘下 result 本身：没有兄弟则堆变空，否则 minimum 先临时指向右兄弟。 */
    heap->minimum = nodes[result].right == result ? -1 : nodes[result].right;
    detach(heap, result);
    nodes[result].active = 0;
    nodes[result].degree = 0;
    --heap->size;
    /* 堆非空时按度合并，恢复"每个度数至多一个根"的不变量并得到新 minimum。 */
    if (heap->minimum >= 0) consolidate(heap);
    return result;
}
