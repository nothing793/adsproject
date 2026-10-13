#include "binary_heap.h"
#include "graph.h"
#include <stdlib.h>
#include <string.h>

static int less(const BinaryHeap *heap, int a, int b)
{
    return heap->distance[a] < heap->distance[b] ||
        (heap->distance[a] == heap->distance[b] && a < b);
}

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

void binary_update(BinaryHeap *heap, int vertex)
{
    int index = heap->position[vertex];
    if (index < 0) index = heap->size++;
    /* position 数组让 decrease-key 无需扫描或插入重复元素。 */
    while (index > 0) {
        int parent = (index - 1) / 2;
        if (!less(heap, vertex, heap->items[parent])) break;
        place(heap, index, heap->items[parent]);
        index = parent;
    }
    place(heap, index, vertex);
}

int binary_pop(BinaryHeap *heap)
{
    int result, vertex, index = 0;
    if (!heap->size) return -1;
    result = heap->items[0];
    vertex = heap->items[--heap->size];
    heap->position[result] = -1;
    /* 使用 size/2 避免计算不存在的孩子时发生整数溢出。 */
    while (index < heap->size / 2) {
        int child = index * 2 + 1;
        if (child + 1 < heap->size && less(heap, heap->items[child + 1], heap->items[child])) ++child;
        if (!less(heap, heap->items[child], vertex)) break;
        place(heap, index, heap->items[child]);
        index = child;
    }
    /* 偶数大小的堆可能在最后一层只有一个左孩子。 */
    if (heap->size) place(heap, index, vertex);
    return result;
}
