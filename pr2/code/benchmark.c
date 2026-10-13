#include "dijkstra.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* 固定算法的 PRNG，避免不同平台 rand() 产生不同查询。 */
static uint64_t random_next(uint64_t *state)
{
    uint64_t x = *state;
    x ^= x >> 12; x ^= x << 25; x ^= x >> 27;
    *state = x;
    return x * UINT64_C(2685821657736338717);
}

static int random_vertex(uint64_t *state, int vertices)
{
    uint64_t n = (uint64_t)vertices, value;
    uint64_t threshold = (UINT64_C(0) - n) % n;
    do { value = random_next(state); } while (value < threshold);
    return (int)(value % n);
}

int main(int argc, char **argv)
{
    Graph graph;
    Search searches[2];
    double elapsed[2] = {0, 0};
    uint64_t count, seed, state, reachable = 0, checksum = 0;
    uint64_t settled[2] = {0, 0}, scanned[2] = {0, 0}, decreased[2] = {0, 0};
    char error[256];
    FILE *output;
    int status = EXIT_FAILURE;
    if (argc != 5 || !parse_uint64(argv[2], &count) || count < 1000 || count > UINT32_MAX ||
        !parse_uint64(argv[3], &seed) || !seed) {
        fprintf(stderr, "Usage: %s graph.gr queries(1000..4294967295) nonzero_seed output.csv\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (!graph_load(&graph, argv[1], error, sizeof(error))) {
        fprintf(stderr, "%s\n", error); return EXIT_FAILURE;
    }
    if (graph.vertices < 2) {
        fprintf(stderr, "benchmark requires at least two vertices\n");
        graph_free(&graph); return EXIT_FAILURE;
    }
    if (!search_init(&searches[0], graph.vertices, HEAP_BINARY)) {
        fprintf(stderr, "allocation failed\n"); graph_free(&graph); return EXIT_FAILURE;
    }
    if (!search_init(&searches[1], graph.vertices, HEAP_FIBONACCI)) {
        fprintf(stderr, "allocation failed\n"); search_free(&searches[0]); graph_free(&graph); return EXIT_FAILURE;
    }
    state = seed;
    /* 预热不计时、不消耗查询随机序列；两种堆各运行一次。 */
    for (int i = 0; i < 2; ++i) dijkstra(&graph, &searches[i], 0, graph.vertices - 1);
    for (uint64_t query = 0; query < count; ++query) {
        int source = random_vertex(&state, graph.vertices), target;
        do { target = random_vertex(&state, graph.vertices); } while (source == target);
        /* 奇偶查询交替执行顺序，减轻固定顺序引入的缓存偏差。 */
        for (int order = 0; order < 2; ++order) {
            int i = (order + (int)(query & 1)) % 2;
            clock_t start = clock(), stop;
            dijkstra(&graph, &searches[i], source, target);
            stop = clock();
            if (start == (clock_t)-1 || stop == (clock_t)-1 || stop < start) {
                fprintf(stderr, "clock unavailable or wrapped\n"); goto cleanup;
            }
            elapsed[i] += (double)(stop - start) / CLOCKS_PER_SEC;
            settled[i] += searches[i].stats.settled;
            scanned[i] += searches[i].stats.scanned;
            decreased[i] += searches[i].stats.decreased;
        }
        if (searches[0].distance[target] != searches[1].distance[target]) {
            fprintf(stderr, "distance mismatch at query %" PRIu64 " (%d,%d)\n", query, source + 1, target + 1);
            goto cleanup;
        }
        if (searches[0].distance[target] != DIST_INF) ++reachable;
        /* 无符号溢出是模 2^64；摘要用于重跑核对，不替代逐对比较。 */
        checksum = checksum * UINT64_C(1099511628211) ^ searches[0].distance[target];
        if ((query + 1) % 100 == 0) fprintf(stderr, "verified %" PRIu64 "/%" PRIu64 " queries\n", query + 1, count);
    }
    output = fopen(argv[4], "w");
    if (!output) { fprintf(stderr, "cannot open CSV output\n"); goto cleanup; }
    if (fprintf(output, "vertices,arcs,queries,seed,heap,total_seconds,mean_ms,reachable,checksum,settled,scanned,decreased,clock_ticks_per_second\n") < 0) {
        fclose(output); goto cleanup;
    }
    for (int i = 0; i < 2; ++i) {
        if (fprintf(output, "%d,%zu,%" PRIu64 ",%" PRIu64 ",%s,%.9f,%.9f,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%ld\n",
            graph.vertices, graph.arcs, count, seed, heap_name((HeapKind)i), elapsed[i],
            elapsed[i] * 1000.0 / (double)count, reachable, checksum, settled[i], scanned[i], decreased[i], (long)CLOCKS_PER_SEC) < 0) {
            fclose(output); goto cleanup;
        }
    }
    if (fclose(output)) { fprintf(stderr, "CSV write failed\n"); goto cleanup; }
    printf("Verified %" PRIu64 " queries; results: %s\n", count, argv[4]);
    status = EXIT_SUCCESS;
cleanup:
    search_free(&searches[0]);
    search_free(&searches[1]);
    graph_free(&graph);
    return status;
}
