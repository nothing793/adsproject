#ifndef BINARY_HEAP_H
#define BINARY_HEAP_H
#include <stdint.h>

typedef struct {
    int capacity, size;
    int *items, *position;
    const uint64_t *distance;
} BinaryHeap;

int binary_init(BinaryHeap *heap, int capacity, const uint64_t *distance);
void binary_reset(BinaryHeap *heap);
void binary_free(BinaryHeap *heap);
/* 调用前先更新 distance；只允许新插入或严格减小键值。 */
void binary_update(BinaryHeap *heap, int vertex);
int binary_pop(BinaryHeap *heap);
#endif
