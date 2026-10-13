/*
 * dijkstra.c —— 两种优先队列共用的 Dijkstra 最短路径实现。
 *
 * 本文件实现的功能：
 *   1. heap_name()：堆类型到 CSV 分组名的转换；
 *   2. search_init() / search_free()：工作区分配与释放，只分配被选中的堆；
 *   3. update()：把"插入或减小键值"分派到对应堆，是两种实现唯一的差异点；
 *   4. dijkstra()：重置状态、初始化源点、反复取出最小顶点并松弛出弧，
 *      同时统计定型顶点数、扫描弧数、插入次数与 decrease-key 次数。
 *
 * 正确性要点：
 *   - 弧权非负，因此一个顶点出堆时其距离即为最终最短距离，可以定型；
 *   - 提前停止必须发生在目标顶点出堆之后，首次发现目标不代表已最短；
 *   - 堆内不会出现过期条目：首次发现才插入，之后只做 decrease-key，
 *     已定型顶点不再入堆；
 *   - 距离用 uint64_t，接近 DIST_INF 时的加法会先做上界检查，
 *     保证不会溢出，也不会把有限距离写成"不可达"。
 */

#include "dijkstra.h"
#include <stdlib.h>
#include <string.h>

const char *heap_name(HeapKind kind)
{
    return kind == HEAP_BINARY ? "binary" : "fibonacci";
}

/* 分配工作区；失败时统一走 search_free()，避免残留半分配状态。
 * 只有被选中的堆会被初始化，另一种保持全零，释放时同样安全。 */
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

/* 释放两种堆（未初始化的那种为空壳）与三个共享数组，最后整体清零。 */
void search_free(Search *search)
{
    binary_free(&search->binary);
    fibonacci_free(&search->fibonacci);
    free(search->distance);
    free(search->previous);
    free(search->settled);
    memset(search, 0, sizeof(*search));
}

/* 唯一的差异分派点：调用者先更新 distance，再由此处转入具体堆。
 * 未被选中的堆结构体保持全零，不会被访问。 */
static void update(Search *search, int vertex)
{
    if (search->kind == HEAP_BINARY) binary_update(&search->binary, vertex);
    else fibonacci_update(&search->fibonacci, vertex);
}

/* 单次搜索。source 为 0 起始编号；target 为 -1 时求完整单源最短路径，
 * 否则在目标出堆后停止。返回 0 仅表示参数非法（容量不匹配或编号越界）。 */
int dijkstra(const Graph *graph, Search *search, int source, int target)
{
    /* 前置条件检查：工作区容量必须与图一致，编号必须在范围内。 */
    if (search->capacity != graph->vertices || source < 0 || source >= graph->vertices ||
        target < -1 || target >= graph->vertices) return 0;
    memset(&search->stats, 0, sizeof(search->stats));
    /* 重置为初始状态：全部未发现，堆清空。这一步是 O(n)，计入本次搜索成本。 */
    for (int i = 0; i < graph->vertices; ++i) {
        search->distance[i] = DIST_INF;
        search->previous[i] = -1;
        search->settled[i] = 0;
    }
    if (search->kind == HEAP_BINARY) binary_reset(&search->binary);
    else fibonacci_reset(&search->fibonacci);
    /* 源点距离为 0 并入堆。 */
    search->distance[source] = 0;
    update(search, source);
    search->stats.inserted = 1;
    for (;;) {
        /* 取出当前距离最小的候选顶点；堆空表示剩余顶点都不可达。 */
        int vertex = search->kind == HEAP_BINARY ? binary_pop(&search->binary) : fibonacci_pop(&search->fibonacci);
        if (vertex < 0) break;
        search->settled[vertex] = 1;   /* 出堆即定型：距离不会再被改进。 */
        ++search->stats.settled;
        /* 必须在目标出堆后停止，首次发现目标不能保证最短。 */
        if (vertex == target) break;
        /* 松弛 vertex 的全部出弧，区间由 CSR 的 offset 给出。 */
        for (size_t i = graph->offset[vertex]; i < graph->offset[vertex + 1]; ++i) {
            int next = graph->target[i];
            uint64_t candidate;
            ++search->stats.scanned;
            if (search->settled[next]) continue;   /* 已定型顶点不可能再被改进。 */
            /* 上界检查：若相加会达到或超过 DIST_INF，则跳过该弧，
             * 保证有限距离不会和"不可达"标记混淆。 */
            if (graph->weight[i] >= DIST_INF - search->distance[vertex]) continue;
            candidate = search->distance[vertex] + graph->weight[i];
            if (candidate < search->distance[next]) {
                /* 首次发现计入 inserted，改进已有候选计入 decreased。 */
                if (search->distance[next] == DIST_INF) ++search->stats.inserted;
                else ++search->stats.decreased;
                search->distance[next] = candidate;
                search->previous[next] = vertex;
                update(search, next);   /* 新插入或 decrease-key，由 update 分派。 */
            }
        }
    }
    return 1;
}
