#ifndef DIJKSTRA_H
#define DIJKSTRA_H
#include "graph.h"
#include "binary_heap.h"
#include "fibonacci_heap.h"

typedef enum { HEAP_BINARY, HEAP_FIBONACCI } HeapKind;
typedef struct {
    uint64_t settled, scanned, inserted, decreased;
} SearchStats;
typedef struct {
    int capacity;
    HeapKind kind;
    uint64_t *distance;
    int *previous;
    unsigned char *settled;
    BinaryHeap binary;
    FibonacciHeap fibonacci;
    SearchStats stats;
} Search;

/* 每个工作区只分配所选堆；工作区可跨查询复用，非线程共享。 */
int search_init(Search *search, int vertices, HeapKind kind);
void search_free(Search *search);
/* target=-1 求单源全部距离；否则只保证目标距离与前驱链已最终确定。 */
int dijkstra(const Graph *graph, Search *search, int source, int target);
const char *heap_name(HeapKind kind);
#endif
