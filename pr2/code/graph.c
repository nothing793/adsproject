#include "graph.h"

#include <ctype.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { int source, target; uint64_t weight; } Arc;

void *array_alloc(size_t count, size_t element_size)
{
    if (element_size == 0 || count > SIZE_MAX / element_size) return NULL;
    return calloc(count ? count : 1, element_size);
}

int parse_uint64(const char *text, uint64_t *value)
{
    uint64_t result = 0;
    if (!text || !*text) return 0;
    while (*text) {
        unsigned digit;
        if (*text < '0' || *text > '9') return 0;
        digit = (unsigned)(*text++ - '0');
        if (result > (UINT64_MAX - digit) / 10) return 0;
        result = result * 10 + digit;
    }
    *value = result;
    return 1;
}

void graph_free(Graph *graph)
{
    free(graph->offset);
    free(graph->target);
    free(graph->weight);
    memset(graph, 0, sizeof(*graph));
}

int graph_load(Graph *graph, const char *path, char *error, size_t error_size)
{
    FILE *file;
    Arc *arcs = NULL;
    size_t *cursor = NULL, count = 0, line_number = 0;
    int header = 0, success = 0;
    char line[1024];
    const char *reason = "invalid graph";
    memset(graph, 0, sizeof(*graph));
    file = fopen(path, "r");
    if (!file) {
        snprintf(error, error_size, "cannot open graph: %s", path);
        return 0;
    }
    while (fgets(line, sizeof(line), file)) {
        char *p = line, a[64], b[64], c[64], extra;
        uint64_t u, v, w;
        ++line_number;
        if (!strchr(line, '\n') && !feof(file)) {
            reason = "line exceeds 1023 bytes"; goto done;
        }
        while (isspace((unsigned char)*p)) ++p;
        if (!*p || *p == 'c') continue;
        if (!isspace((unsigned char)p[1])) { reason = "record type must be followed by whitespace"; goto done; }
        if (*p == 'p') {
            if (header || sscanf(p, "p %63s %63s %63s %c", a, b, c, &extra) != 3 ||
                strcmp(a, "sp") || !parse_uint64(b, &u) || !parse_uint64(c, &v) ||
                u == 0 || u > INT_MAX || v > SIZE_MAX) {
                reason = "expected one 'p sp n m' header (1 <= n <= INT_MAX)"; goto done;
            }
            graph->vertices = (int)u;
            graph->arcs = (size_t)v;
            graph->offset = array_alloc((size_t)u + 1, sizeof(*graph->offset));
            arcs = array_alloc(graph->arcs, sizeof(*arcs));
            if (!graph->offset || !arcs) { reason = "allocation failed"; goto done; }
            header = 1;
        } else if (*p == 'a') {
            if (!header || count >= graph->arcs ||
                sscanf(p, "a %63s %63s %63s %c", a, b, c, &extra) != 3 ||
                !parse_uint64(a, &u) || !parse_uint64(b, &v) || !parse_uint64(c, &w) ||
                !u || u > (uint64_t)graph->vertices || !v || v > (uint64_t)graph->vertices) {
                reason = "invalid arc, endpoint, weight, or arc count"; goto done;
            }
            /* 保证任意简单路径可用 uint64_t 表示，UINT64_MAX 专用于不可达。 */
            if (w > (UINT64_MAX - 1) / (uint64_t)(graph->vertices > 1 ? graph->vertices - 1 : 1)) {
                reason = "weight too large for safe simple-path distances"; goto done;
            }
            arcs[count].source = (int)u - 1;
            arcs[count].target = (int)v - 1;
            arcs[count++].weight = w;
            ++graph->offset[(size_t)u];
        } else { reason = "unknown DIMACS record"; goto done; }
    }
    if (ferror(file)) { reason = "graph read failed"; goto done; }
    if (!header || count != graph->arcs) { reason = "missing header or arc count mismatch"; goto done; }
    graph->target = array_alloc(count, sizeof(*graph->target));
    graph->weight = array_alloc(count, sizeof(*graph->weight));
    cursor = array_alloc((size_t)graph->vertices, sizeof(*cursor));
    if (!graph->target || !graph->weight || !cursor) { reason = "allocation failed"; goto done; }
    for (int i = 0; i < graph->vertices; ++i) {
        graph->offset[i + 1] += graph->offset[i];
        cursor[i] = graph->offset[i];
    }
    for (size_t i = 0; i < count; ++i) {
        size_t index = cursor[arcs[i].source]++;
        graph->target[index] = arcs[i].target;
        graph->weight[index] = arcs[i].weight;
    }
    success = 1;
done:
    free(cursor);
    free(arcs);
    fclose(file);
    if (!success) {
        snprintf(error, error_size, "line %zu: %s", line_number, reason);
        graph_free(graph);
    }
    return success;
}
