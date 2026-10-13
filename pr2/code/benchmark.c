/*
 * benchmark.c —— 二叉堆与 Fibonacci 堆的性能对比评测程序。
 *
 * 本文件实现的功能：
 *   1. random_next() / random_vertex()：可复现的 xorshift64* 伪随机数发生器与
 *      无模偏差的顶点采样（拒绝采样）；
 *   2. 读取一张 DIMACS 图，为两种堆各建一个工作区并各自预热一次；
 *   3. 用固定种子生成至少 1000 对 (s,t) 查询，按查询奇偶交替两种堆的执行
 *      顺序，分别用 clock() 计时执行同一查询；
 *   4. 逐对比较两种堆的目标距离，不一致立即失败；
 *   5. 汇总总时间、平均时间、可达查询数、距离摘要与操作次数，写入 CSV。
 *
 * 计时口径：只累计"状态重置 + 搜索"的时间，不包含图加载、初次内存分配、
 * 预热、随机数生成与 CSV 写出；两种堆工作区同时存在，因此本程序比较的是
 * 运行时间而不是峰值内存。使用 clock() 测量，CSV 中同时记录其分辨率。
 */

#include "dijkstra.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* 固定算法的 PRNG，避免不同平台 rand() 产生不同查询。
 * xorshift64* ：状态不为 0 时周期为 2^64-1，输出质量足够生成测试查询。 */
static uint64_t random_next(uint64_t *state)
{
    uint64_t x = *state;
    x ^= x >> 12; x ^= x << 25; x ^= x >> 27;
    *state = x;
    return x * UINT64_C(2685821657736338717);
}

/* 在 [0, vertices) 上均匀采样：先丢弃小于 2^64 mod vertices 的取值，再做取模，
 * 避免简单取模带来的顶点分布偏差。 */
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
    Search searches[2];                 /* [0] 二叉堆，[1] Fibonacci 堆 */
    double elapsed[2] = {0, 0};         /* 累计计时（秒） */
    uint64_t count, seed, state, reachable = 0, checksum = 0;
    uint64_t settled[2] = {0, 0}, scanned[2] = {0, 0}, decreased[2] = {0, 0};
    char error[256];
    FILE *output;
    int status = EXIT_FAILURE;
    /* 参数：图路径、查询数（1000..UINT32_MAX）、非零种子、输出 CSV。
     * 查询数下限与题目"至少 1000 对"一致；非零种子保证查询序列可复现。 */
    if (argc != 5 || !parse_uint64(argv[2], &count) || count < 1000 || count > UINT32_MAX ||
        !parse_uint64(argv[3], &seed) || !seed) {
        fprintf(stderr, "Usage: %s graph.gr queries(1000..4294967295) nonzero_seed output.csv\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (!graph_load(&graph, argv[1], error, sizeof(error))) {
        fprintf(stderr, "%s\n", error); return EXIT_FAILURE;
    }
    /* 需要两个不同顶点作为起终点，因此至少要有两个顶点。 */
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
        /* 起点与终点用拒绝采样保证不同；不同查询之间允许重复。 */
        int source = random_vertex(&state, graph.vertices), target;
        do { target = random_vertex(&state, graph.vertices); } while (source == target);
        /* 奇偶查询交替执行顺序，减轻固定顺序引入的缓存偏差。 */
        for (int order = 0; order < 2; ++order) {
            int i = (order + (int)(query & 1)) % 2;
            /* 计时区间只覆盖一次 Dijkstra（含其内部 O(n) 状态重置）。 */
            clock_t start = clock(), stop;
            dijkstra(&graph, &searches[i], source, target);
            stop = clock();
            /* clock() 失败返回 -1；回绕会让 stop < start，同样按错误处理。 */
            if (start == (clock_t)-1 || stop == (clock_t)-1 || stop < start) {
                fprintf(stderr, "clock unavailable or wrapped\n"); goto cleanup;
            }
            elapsed[i] += (double)(stop - start) / CLOCKS_PER_SEC;
            settled[i] += searches[i].stats.settled;
            scanned[i] += searches[i].stats.scanned;
            decreased[i] += searches[i].stats.decreased;
        }
        /* 正确性核对放在计时区间之外：同一查询两种堆的目标距离必须一致。 */
        if (searches[0].distance[target] != searches[1].distance[target]) {
            fprintf(stderr, "distance mismatch at query %" PRIu64 " (%d,%d)\n", query, source + 1, target + 1);
            goto cleanup;
        }
        if (searches[0].distance[target] != DIST_INF) ++reachable;
        /* 无符号溢出是模 2^64；摘要用于重跑核对，不替代逐对比较。 */
        checksum = checksum * UINT64_C(1099511628211) ^ searches[0].distance[target];
        /* 进度输出到 stderr，避免污染 CSV。 */
        if ((query + 1) % 100 == 0) fprintf(stderr, "verified %" PRIu64 "/%" PRIu64 " queries\n", query + 1, count);
    }
    /* 全部查询通过核对后才写 CSV：一行表头 + 每种堆一行。 */
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
    /* 统一的清理出口：任何失败路径都在这里释放两个工作区与图。 */
    search_free(&searches[0]);
    search_free(&searches[1]);
    graph_free(&graph);
    return status;
}
