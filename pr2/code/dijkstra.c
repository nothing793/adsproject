#include "dijkstra.h"
#include <stdlib.h>
#include <string.h>

const char *heap_name(HeapKind kind)
{
    return kind == HEAP_BINARY ? "binary" : "fibonacci";
}

int search_init(Search *search, int vertices, HeapKind kind)
{
    memset(search, 0, sizeof(*search));
    if (vertices <= 0 || (kind != HEAP_BINARY && kind != HEAP_FIBONACCI)) return 0;
    search->capacity = vertices;
    search->kind = kind;
    search->distance = array_alloc((size_t)vertices, sizeof(*search->distance));
    search->previous = array_alloc((size_t)vertices, sizeof(*search->previous));
    search->settled = array_alloc((size_t)vertices, sizeof(*search->settled));
    if (!search->distance || !search->previous || !search->settled) goto fail;
    if (kind == HEAP_BINARY) {
        if (!binary_init(&search->binary, vertices, search->distance)) goto fail;
    } else if (!fibonacci_init(&search->fibonacci, vertices, search->distance)) goto fail;
    return 1;
fail:
    search_free(search);
    return 0;
}

void search_free(Search *search)
{
    binary_free(&search->binary);
    fibonacci_free(&search->fibonacci);
    free(search->distance);
    free(search->previous);
    free(search->settled);
    memset(search, 0, sizeof(*search));
}

static void update(Search *search, int vertex)
{
    if (search->kind == HEAP_BINARY) binary_update(&search->binary, vertex);
    else fibonacci_update(&search->fibonacci, vertex);
}

int dijkstra(const Graph *graph, Search *search, int source, int target)
{
    if (search->capacity != graph->vertices || source < 0 || source >= graph->vertices ||
        target < -1 || target >= graph->vertices) return 0;
    memset(&search->stats, 0, sizeof(search->stats));
    for (int i = 0; i < graph->vertices; ++i) {
        search->distance[i] = DIST_INF;
        search->previous[i] = -1;
        search->settled[i] = 0;
    }
    if (search->kind == HEAP_BINARY) binary_reset(&search->binary);
    else fibonacci_reset(&search->fibonacci);
    search->distance[source] = 0;
    update(search, source);
    search->stats.inserted = 1;
    for (;;) {
        int vertex = search->kind == HEAP_BINARY ? binary_pop(&search->binary) : fibonacci_pop(&search->fibonacci);
        if (vertex < 0) break;
        search->settled[vertex] = 1;
        ++search->stats.settled;
        /* 必须在目标出堆后停止，首次发现目标不能保证最短。 */
        if (vertex == target) break;
        for (size_t i = graph->offset[vertex]; i < graph->offset[vertex + 1]; ++i) {
            int next = graph->target[i];
            uint64_t candidate;
            ++search->stats.scanned;
            if (search->settled[next]) continue;
            if (graph->weight[i] >= DIST_INF - search->distance[vertex]) continue;
            candidate = search->distance[vertex] + graph->weight[i];
            if (candidate < search->distance[next]) {
                if (search->distance[next] == DIST_INF) ++search->stats.inserted;
                else ++search->stats.decreased;
                search->distance[next] = candidate;
                search->previous[next] = vertex;
                update(search, next);
            }
        }
    }
    return 1;
}
