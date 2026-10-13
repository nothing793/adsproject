#include "dijkstra.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    Graph graph;
    Search search;
    HeapKind kind;
    uint64_t source, target;
    char error[256];
    int *path, count = 0, vertex;
    if (argc != 5 || (strcmp(argv[2], "binary") && strcmp(argv[2], "fibonacci")) ||
        !parse_uint64(argv[3], &source) || !parse_uint64(argv[4], &target)) {
        fprintf(stderr, "Usage: %s graph.gr binary|fibonacci source target\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (!graph_load(&graph, argv[1], error, sizeof(error))) {
        fprintf(stderr, "%s\n", error); return EXIT_FAILURE;
    }
    if (!source || source > (uint64_t)graph.vertices || !target || target > (uint64_t)graph.vertices) {
        fprintf(stderr, "source and target must be in 1..%d\n", graph.vertices);
        graph_free(&graph); return EXIT_FAILURE;
    }
    kind = !strcmp(argv[2], "binary") ? HEAP_BINARY : HEAP_FIBONACCI;
    if (!search_init(&search, graph.vertices, kind)) {
        fprintf(stderr, "allocation failed\n"); graph_free(&graph); return EXIT_FAILURE;
    }
    dijkstra(&graph, &search, (int)source - 1, (int)target - 1);
    if (search.distance[target - 1] == DIST_INF) puts("distance=INF\npath=unreachable");
    else {
        printf("distance=%" PRIu64 "\npath=", search.distance[target - 1]);
        path = array_alloc((size_t)graph.vertices, sizeof(*path));
        if (!path) {
            fprintf(stderr, "allocation failed\n"); search_free(&search); graph_free(&graph);
            return EXIT_FAILURE;
        }
        vertex = (int)target - 1;
        while (vertex >= 0 && count < graph.vertices) {
            path[count++] = vertex;
            vertex = search.previous[vertex];
        }
        for (int i = count - 1; i >= 0; --i) printf("%d%s", path[i] + 1, i ? " -> " : "\n");
        free(path);
    }
    printf("settled=%" PRIu64 " scanned=%" PRIu64 " inserted=%" PRIu64 " decreased=%" PRIu64 "\n",
        search.stats.settled, search.stats.scanned, search.stats.inserted, search.stats.decreased);
    search_free(&search);
    graph_free(&graph);
    return EXIT_SUCCESS;
}
