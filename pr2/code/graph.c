/*
 * graph.c —— DIMACS 最短路文件（.gr）的解析与 CSR 邻接表构建。
 *
 * 本文件实现的功能：
 *   1. array_alloc()：带乘法回绕检查的零初始化数组分配；
 *   2. parse_uint64()：严格解析十进制非负整数（拒绝负号、溢出、尾随字符）；
 *   3. graph_free()：释放图的全部数组并把结构体清零；
 *   4. graph_load()：逐行解析 c 注释、p sp n m 头与 a u v w 弧记录，完成全部
 *      合法性校验后构造 CSR；任何错误都返回 0、写出"出错行号 + 原因"，并
 *      回收已分配的临时内存，保证失败路径不泄漏、不留下半成品图。
 *
 * 关键设计：
 *   - 所有校验都在解析阶段一次做完（记录类型、编号范围、弧计数、权值上限），
 *     后续算法可以无条件信任图数据；
 *   - 弧先暂存到 Arc 数组并统计各起点出度，再做前缀和、按起点二次填入，
 *     因此只需顺序扫描文件一遍，构造复杂度 O(n+m)；
 *   - 弧权上限 (UINT64_MAX-1)/max(n-1,1) 保证任意简单路径的距离都能用
 *     uint64_t 表示，于是 DIST_INF 可以专用于"不可达"语义。
 */

#include "graph.h"

#include <ctype.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 解析阶段的临时弧记录（起点、终点、权值），CSR 填好后立即释放。 */
typedef struct { int source, target; uint64_t weight; } Arc;

/* 见 graph.h：先做溢出检查再交给 calloc，因此返回的指针总能安全 free。
 * count 为 0 时 calloc(1, size) 仍返回有效指针，便于统一释放路径。 */
void *array_alloc(size_t count, size_t element_size)
{
    if (element_size == 0 || count > SIZE_MAX / element_size) return NULL;
    return calloc(count ? count : 1, element_size);
}

/* 见 graph.h：逐字符解析，每次乘 10 之前先判断是否会越过 UINT64_MAX，
 * 因此超长数字串只会被判为非法，不会发生无符号回绕。 */
int parse_uint64(const char *text, uint64_t *value)
{
    uint64_t result = 0;
    if (!text || !*text) return 0;
    while (*text) {
        unsigned digit;
        if (*text < '0' || *text > '9') return 0;
        digit = (unsigned)(*text++ - '0');
        /* 等价于 result * 10 + digit > UINT64_MAX，但不产生回绕。 */
        if (result > (UINT64_MAX - digit) / 10) return 0;
        result = result * 10 + digit;
    }
    *value = result;
    return 1;
}

/* 释放三个数组并整体清零。free(NULL) 无副作用，故可重复调用、也可作用于
 * 只被 memset 过还没加载成功的对象。 */
void graph_free(Graph *graph)
{
    free(graph->offset);
    free(graph->target);
    free(graph->weight);
    memset(graph, 0, sizeof(*graph));
}

/* 读取并校验图文件，构造 CSR。返回 1 表示成功，0 表示失败并在 error 中
 * 给出 "line N: 原因"。局部变量分工：
 *   arcs   —— 弧的暂存数组（成功路径上先填 CSR 再释放）；
 *   cursor —— 每个起点的下一个待填位置，用于二次填入时保持稳定顺序；
 *   count  —— 已读入的弧数，必须与 p 头声明的 m 完全相等；
 *   header —— 是否已读到 p 头（缺失、重复或出现在弧之后都非法）；
 *   reason —— 失败原因字符串，统一在 done 标签处附带行号输出。 */
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
        /* 读满缓冲区但未取到换行，说明该行超过 1023 字节，直接拒绝。 */
        if (!strchr(line, '\n') && !feof(file)) {
            reason = "line exceeds 1023 bytes"; goto done;
        }
        while (isspace((unsigned char)*p)) ++p;
        if (!*p || *p == 'c') continue;   /* 空行与注释行直接跳过。 */
        /* 记录类型字符后必须跟空白，避免把 "pxx" 之类误判为 p 记录。 */
        if (!isspace((unsigned char)p[1])) { reason = "record type must be followed by whitespace"; goto done; }
        if (*p == 'p') {
            /* 头部必须唯一、格式为 "p sp n m"，且 1 <= n <= INT_MAX、m 可用
             * size_t 表示；这里顺带完成顶点数与弧数的分配。 */
            if (header || sscanf(p, "p %63s %63s %63s %c", a, b, c, &extra) != 3 ||
                strcmp(a, "sp") || !parse_uint64(b, &u) || !parse_uint64(c, &v) ||
                u == 0 || u > INT_MAX || v > SIZE_MAX) {
                reason = "expected one 'p sp n m' header (1 <= n <= INT_MAX)"; goto done;
            }
            graph->vertices = (int)u;
            graph->arcs = (size_t)v;
            /* offset 需要 n+1 项以便 offset[n] 收尾；arcs 允许为 0。 */
            graph->offset = array_alloc((size_t)u + 1, sizeof(*graph->offset));
            arcs = array_alloc(graph->arcs, sizeof(*arcs));
            if (!graph->offset || !arcs) { reason = "allocation failed"; goto done; }
            header = 1;
        } else if (*p == 'a') {
            /* 弧记录：必须先有头、不能超过声明的弧数，且端点编号在 1..n。 */
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
            /* 暂存弧，同时把出度累加到 offset[u]（此处 offset 暂存计数）。 */
            arcs[count].source = (int)u - 1;
            arcs[count].target = (int)v - 1;
            arcs[count++].weight = w;
            ++graph->offset[(size_t)u];
        } else { reason = "unknown DIMACS record"; goto done; }
    }
    if (ferror(file)) { reason = "graph read failed"; goto done; }
    /* 头必须出现，且实际弧数必须与声明严格一致。 */
    if (!header || count != graph->arcs) { reason = "missing header or arc count mismatch"; goto done; }
    graph->target = array_alloc(count, sizeof(*graph->target));
    graph->weight = array_alloc(count, sizeof(*graph->weight));
    cursor = array_alloc((size_t)graph->vertices, sizeof(*cursor));
    if (!graph->target || !graph->weight || !cursor) { reason = "allocation failed"; goto done; }
    /* offset 由出度计数转成前缀和，得到每个起点的区间下界；
     * cursor 复制下界作为二次填入的写指针。 */
    for (int i = 0; i < graph->vertices; ++i) {
        graph->offset[i + 1] += graph->offset[i];
        cursor[i] = graph->offset[i];
    }
    /* 按原始顺序填入弧，使同一顶点的出弧保持文件中的先后次序。 */
    for (size_t i = 0; i < count; ++i) {
        size_t index = cursor[arcs[i].source]++;
        graph->target[index] = arcs[i].target;
        graph->weight[index] = arcs[i].weight;
    }
    success = 1;
done:
    /* 成功时临时弧与 cursor 也一并释放；失败时额外输出原因并清空半成品图。 */
    free(cursor);
    free(arcs);
    fclose(file);
    if (!success) {
        snprintf(error, error_size, "line %zu: %s", line_number, reason);
        graph_free(graph);
    }
    return success;
}
