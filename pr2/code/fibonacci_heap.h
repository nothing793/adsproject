#ifndef FIBONACCI_HEAP_H
#define FIBONACCI_HEAP_H
#include <stdint.h>

typedef struct {
    int parent, child, left, right, degree;
    unsigned char mark, active;
} FibonacciNode;

typedef struct {
    int capacity, size, minimum;
    FibonacciNode *nodes;
    const uint64_t *distance;
} FibonacciHeap;

int fibonacci_init(FibonacciHeap *heap, int capacity, const uint64_t *distance);
void fibonacci_reset(FibonacciHeap *heap);
void fibonacci_free(FibonacciHeap *heap);
/* 顶点编号即句柄；distance 已由调用者严格减小，或顶点尚未插入。 */
void fibonacci_update(FibonacciHeap *heap, int vertex);
int fibonacci_pop(FibonacciHeap *heap);
#endif
