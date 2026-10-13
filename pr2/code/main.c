/*
 * main.c —— 单对查询的命令行入口（输出最短距离与一条最短路径）。
 *
 * 本文件实现的功能：
 *   1. 解析命令行 "graph.gr binary|fibonacci source target"（顶点编号 1 起始）；
 *   2. 加载 DIMACS 图，校验端点编号是否落在 1..n；
 *   3. 初始化所选堆的搜索工作区并执行一次 Dijkstra；
 *   4. 由 previous 数组回溯出一条最短路径并按 "1 -> 3 -> 2" 形式打印，
 *      不可达时打印 distance=INF 与 path=unreachable；
 *   5. 打印定型顶点数、扫描弧数、插入次数与 decrease-key 次数，便于核对。
 *
 * 退出码：成功为 EXIT_SUCCESS；参数错误、图加载失败、编号越界或分配失败
 * 会打印原因到 stderr 并返回 EXIT_FAILURE。
 */

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
    /* 参数必须是四个：图路径、堆名与两个十进制顶点编号；堆名只接受
     * binary / fibonacci，编号用严格解析以便提前拒绝负号与非法字符。 */
    if (argc != 5 || (strcmp(argv[2], "binary") && strcmp(argv[2], "fibonacci")) ||
        !parse_uint64(argv[3], &source) || !parse_uint64(argv[4], &target)) 
    {
        fprintf(stderr, "Usage: %s graph.gr binary|fibonacci source target\n", argv[0]);
        return EXIT_FAILURE;
    }

    /* 图加载失败时不保留半成品，graph_load() 已负责清理。 */
    if (!graph_load(&graph, argv[1], error, sizeof(error))) 
    {
        fprintf(stderr, "%s\n", error); return EXIT_FAILURE;
    }

    /* 命令行使用 1 起始编号，需在此转换为范围内的值。 */
    if (!source || source > (uint64_t)graph.vertices || !target || target > (uint64_t)graph.vertices) 
    {
        fprintf(stderr, "source and target must be in 1..%d\n", graph.vertices);
        graph_free(&graph); return EXIT_FAILURE;
    }

    kind = !strcmp(argv[2], "binary") ? HEAP_BINARY : HEAP_FIBONACCI;
    if (!search_init(&search, graph.vertices, kind)) 
    {
        fprintf(stderr, "allocation failed\n"); graph_free(&graph); return EXIT_FAILURE;
    }
    /* 顶点编号在此统一减去 1，转为内存编号。 */
    dijkstra(&graph, &search, (int)source - 1, (int)target - 1);
    if (search.distance[target - 1] == DIST_INF) puts("distance=INF\npath=unreachable");
    else {
        printf("distance=%" PRIu64 "\npath=", search.distance[target - 1]);
        /* 回溯路径：从目标沿 previous 走到源点，数组是逆序存放的。 */
        path = array_alloc((size_t)graph.vertices, sizeof(*path));
        if (!path) 
        {
            fprintf(stderr, "allocation failed\n"); search_free(&search); graph_free(&graph);
            return EXIT_FAILURE;
        }
        vertex = (int)target - 1;
        /* count 的上限检查保证即使前驱链异常也不会越界写 path。 */
        while (vertex >= 0 && count < graph.vertices) 
        {
            path[count++] = vertex;
            vertex = search.previous[vertex];
        }
        /* 逆序打印还原为源点→目标，并把编号转回 1 起始。 */
        for (int i = count - 1; i >= 0; --i) printf("%d%s", path[i] + 1, i ? " -> " : "\n");
        free(path);
    }
    /* 统计信息用于核对两种堆是否探索了相同的工作量。 */
    printf("settled=%" PRIu64 " scanned=%" PRIu64 " inserted=%" PRIu64 " decreased=%" PRIu64 "\n",
        search.stats.settled, search.stats.scanned, search.stats.inserted, search.stats.decreased);
    search_free(&search);
    graph_free(&graph);
    return EXIT_SUCCESS;
}
