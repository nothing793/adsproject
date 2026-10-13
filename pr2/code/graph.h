#ifndef GRAPH_H
#define GRAPH_H

#include <stddef.h>
#include <stdint.h>

#define DIST_INF UINT64_MAX

/* DIMACS 编号在文件中为 1..n，内存中为 0..n-1；弧保留方向。 */
typedef struct {
    int vertices;
    size_t arcs;
    size_t *offset;
    int *target;
    uint64_t *weight;
} Graph;

/* 失败时返回 0，将原因写到 error；调用者无需释放失败的对象。 */
int graph_load(Graph *graph, const char *path, char *error, size_t error_size);
void graph_free(Graph *graph);
/* 严格解析十进制非负整数，拒绝负号、溢出、尾随字符。 */
int parse_uint64(const char *text, uint64_t *value);
void *array_alloc(size_t count, size_t element_size);

#endif
