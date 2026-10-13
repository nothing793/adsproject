/*
 * tests/test.c —— 不依赖第三方库的 C 正确性测试程序。
 *
 * 本文件实现的功能：
 *   1. next_random()：固定种子的线性同余发生器，保证测试输入可复现；
 *   2. key_less()：与两种堆一致的比较规则（距离优先，其次顶点编号）；
 *   3. audit_ring() / audit_heaps()：独立审计堆结构不变量——双向链表互逆、
 *      父指针、孩子度数、mark/active 标记、堆序、position 映射与最小根；
 *   4. heap_tests()：在 128 个槽位上执行 30000 次插入 / 减小键值 / 删除最小值，
 *      每一步都与线性扫描得到的最小值比较，并显式触发级联切割与重置复用；
 *   5. parser_tests()：15 个非法 DIMACS 输入必须被拒绝，另校验零权边、重边、
 *      自环、不可达顶点与 64 位距离边界；
 *   6. check_path() / graph_tests()：在 100 张小型随机有向图上用独立的
 *      Floyd–Warshall 作为真值，逐个起终点比较距离并检查由 previous 还原的路径。
 *
 * 用法约定：断言本身承担验证职责，因此编译时不得定义 NDEBUG；运行时会在当前
 * 目录临时创建并删除 test_graph.tmp，请在可写目录执行，且不要并行启动多个实例。
 */

#include "dijkstra.h"
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 堆测试的固定槽位数：顶点编号取 0..HEAP_N-1。 */
#define HEAP_N 128
/* 固定初始种子，使每次运行的键值序列完全一致。 */
static uint32_t random_state = UINT32_C(20261013);
/* 线性同余发生器：测试追求可复现，不追求随机性质量。 */
static uint32_t next_random(void)
{
    random_state = random_state * UINT32_C(1664525) + UINT32_C(1013904223);
    return random_state;
}

/* 与两种堆实现相同的比较规则，用于独立判断"哪个是当前最小值"。 */
static int key_less(const uint64_t *keys, int a, int b)
{
    return keys[a] < keys[b] || (keys[a] == keys[b] && a < b);
}

/* 独立遍历所有环和树，检查链表互逆、父指针、度数、堆序与唯一性。
 * 递归返回该环的兄弟个数，供父节点与 degree 对照；seen 保证每个节点只被访问
 * 一次，从而同时验证没有环被重复串联。 */
static int audit_ring(const FibonacciHeap *heap, int first, int parent, unsigned char *seen)
{
    int node = first, siblings = 0;
    if (first < 0) return 0;
    do {
        const FibonacciNode *entry;
        assert(node >= 0 && node < heap->capacity && !seen[node]);
        entry = &heap->nodes[node];
        seen[node] = 1;
        assert(entry->active && entry->parent == parent);
        assert(entry->left >= 0 && entry->left < heap->capacity);
        assert(entry->right >= 0 && entry->right < heap->capacity);
        assert(heap->nodes[entry->left].right == node);
        assert(heap->nodes[entry->right].left == node);
        if (parent >= 0) assert(!key_less(heap->distance, node, parent));   /* 孩子不小于父亲 */
        else assert(!entry->mark);                                          /* 根不带丢孩子标记 */
        assert(audit_ring(heap, entry->child, node, seen) == entry->degree);
        node = entry->right;
        assert(++siblings <= heap->capacity);   /* 防止链表自我串联导致死循环 */
    } while (node != first);
    return siblings;
}

/* 以外部维护的 active 数组为真值，交叉核对两种堆的可见状态：
 * Fibonacci 堆的根链表覆盖集合、二叉堆的 position 映射、size、minimum，
 * 以及二叉堆的堆序（每个节点不大于其父亲）。 */
static void audit_heaps(const BinaryHeap *binary, const FibonacciHeap *fibonacci, const unsigned char *active)
{
    unsigned char seen[HEAP_N] = {0};
    int size = 0, minimum = -1;
    audit_ring(fibonacci, fibonacci->minimum, -1, seen);
    for (int i = 0; i < HEAP_N; ++i) {
        /* 三种"在堆内"的表示必须完全一致。 */
        assert((seen[i] != 0) == (active[i] != 0));
        assert((fibonacci->nodes[i].active != 0) == (active[i] != 0));
        assert((binary->position[i] >= 0) == (active[i] != 0));
        if (active[i]) {
            ++size;
            assert(binary->position[i] < binary->size);
            assert(binary->items[binary->position[i]] == i);
            if (minimum < 0 || key_less(binary->distance, i, minimum)) minimum = i;
        }
    }
    assert(binary->size == size && fibonacci->size == size);
    assert(fibonacci->minimum == minimum);
    if (size) assert(binary->items[0] == minimum);
    for (int i = 1; i < size; ++i)
        assert(!key_less(binary->distance, binary->items[i], binary->items[(i - 1) / 2]));
}

/* 堆的三个阶段：装满并核对、显式级联切割、30000 次随机操作与清空。 */
static void heap_tests(void)
{
    uint64_t keys[HEAP_N] = {0};
    unsigned char active[HEAP_N] = {0};
    BinaryHeap binary;
    FibonacciHeap fibonacci;
    int cascade = -1;
    assert(binary_init(&binary, HEAP_N, keys));
    assert(fibonacci_init(&fibonacci, HEAP_N, keys));
    /* 阶段一：全部节点以递增键值插入，两种堆的操作与状态必须逐步一致。 */
    for (int i = 0; i < HEAP_N; ++i) {
        keys[i] = UINT64_C(1000000) + (uint64_t)i;
        binary_update(&binary, i); fibonacci_update(&fibonacci, i); active[i] = 1;
    }
    assert(binary_pop(&binary) == 0 && fibonacci_pop(&fibonacci) == 0);
    active[0] = 0;
    /* 找一个度数 >= 2 的非根节点，用它制造级联切割。 */
    for (int i = 1; i < HEAP_N; ++i)
        if (fibonacci.nodes[i].parent >= 0 && fibonacci.nodes[i].degree >= 2) { cascade = i; break; }
    assert(cascade >= 0);
    /* 显式触发同一非根节点失去两个孩子，覆盖 mark 和级联切割。 */
    for (int cut = 0; cut < 2; ++cut) {
        int child = fibonacci.nodes[cascade].child;
        keys[child] = (uint64_t)(2 - cut);
        binary_update(&binary, child); fibonacci_update(&fibonacci, child);
        /* 第一次丢孩子只应留下 mark；第二次丢孩子自己被切走并失去 mark。 */
        if (!cut) assert(fibonacci.nodes[cascade].mark && fibonacci.nodes[cascade].parent >= 0);
        else assert(fibonacci.nodes[cascade].parent == -1 && !fibonacci.nodes[cascade].mark);
        audit_heaps(&binary, &fibonacci, active);
    }
    /* 阶段二：随机操作。每 7 步做一次删除最小值（与线性扫描真值比较），
     * 其余步做插入或"键值减半"的 decrease-key；每步都审计不变量。 */
    for (int step = 0; step < 30000; ++step) {
        int vertex = (int)(next_random() % HEAP_N);
        if (step % 7 == 0) {
            int expected = -1;
            for (int i = 0; i < HEAP_N; ++i)
                if (active[i] && (expected < 0 || key_less(keys, i, expected))) expected = i;
            assert(binary_pop(&binary) == expected);
            assert(fibonacci_pop(&fibonacci) == expected);
            if (expected >= 0) active[expected] = 0;
        } else {
            /* 未插入的顶点给一个大键值（模拟首次发现），已插入的键值减半
             * （模拟放松后键值严格减小）。 */
            if (!active[vertex]) keys[vertex] = UINT64_C(1000000000) + next_random();
            else keys[vertex] /= 2;
            binary_update(&binary, vertex); fibonacci_update(&fibonacci, vertex); active[vertex] = 1;
        }
        audit_heaps(&binary, &fibonacci, active);
        /* 约每 997 步清空一次堆，覆盖 reset 之后继续复用同一块内存的情形。 */
        if (step % 997 == 0) {
            binary_reset(&binary); fibonacci_reset(&fibonacci);
            memset(active, 0, sizeof(active));
            audit_heaps(&binary, &fibonacci, active);
        }
    }
    /* 阶段三：全部按序弹出，两种堆必须给出完全相同的顺序，最后都为空。 */
    while (binary.size) {
        int result = binary_pop(&binary);
        assert(fibonacci_pop(&fibonacci) == result);
        active[result] = 0;
        audit_heaps(&binary, &fibonacci, active);
    }
    assert(binary_pop(&binary) == -1 && fibonacci_pop(&fibonacci) == -1);
    binary_free(&binary); fibonacci_free(&fibonacci);
    puts("PASS heap: 30000 operations, invariants, cascade, reset, empty");
}

/* 把一段文本写成临时图文件，供解析测试使用。 */
static void write_fixture(const char *text)
{
    FILE *file = fopen("test_graph.tmp", "w");
    assert(file && fputs(text, file) >= 0);
    assert(fclose(file) == 0);
}

/* 输入校验测试：非法输入必须被拒绝，合法输入的距离必须正确。
 * invalid[] 依次覆盖空文件、缺头、弧数不符、端点 0 / 越界、负权、数字溢出、
 * 重复头、多余字段、非 sp 类型、负顶点数、未知记录与超限权值等情形。 */
static void parser_tests(void)
{
    const char *invalid[] = {
        "", "p sp 0 0\n", "a 1 2 3\n", "p sp 2 1\n", "p sp 2 0\na 1 2 1\n",
        "p sp 2 1\na 0 2 1\n", "p sp 2 1\na 1 3 1\n", "p sp 2 1\na 1 2 -1\n",
        "p sp 2 1\na 1 2 18446744073709551616\n", "p sp 2 0\np sp 2 0\n",
        "p sp 2 1\na 1 2 1 garbage\n", "p xx 2 0\n", "p sp -2 0\n",
        "p sp 2 1\nx 1 2 1\n", "p sp 3 1\na 1 2 18446744073709551614\n"
    };
    Graph graph;
    Search search;
    char error[256];
    uint64_t number;
    /* 解析器边界：UINT64_MAX 可接受，多一位即溢出，负号与尾随字符非法。 */
    assert(parse_uint64("18446744073709551615", &number) && number == UINT64_MAX);
    assert(!parse_uint64("18446744073709551616", &number));
    assert(!parse_uint64("-1", &number) && !parse_uint64("1x", &number));
    for (size_t i = 0; i < sizeof(invalid) / sizeof(invalid[0]); ++i) {
        write_fixture(invalid[i]);
        assert(!graph_load(&graph, "test_graph.tmp", error, sizeof(error)));
    }
    /* 合法图：含重边（1->2 权 10 与 3）、零权边（2->3、3->3 自环）、
     * 前导空格的记录以及没有末尾换行的最后一行。 */
    write_fixture("c test\n p sp 4 6\na 1 2 10\na 1 2 3\na 2 3 0\na 1 3 9\na 3 3 0\na 3 1 4");
    assert(graph_load(&graph, "test_graph.tmp", error, sizeof(error)));
    for (int kind = 0; kind < 2; ++kind) {
        assert(search_init(&search, graph.vertices, (HeapKind)kind));
        /* 完整单源：从 0 出发，1 取重边中的较小值 3，2 经零权边得 3，
         * 3 不可达。 */
        assert(dijkstra(&graph, &search, 0, -1));
        assert(search.distance[0] == 0 && search.distance[1] == 3 && search.distance[2] == 3 && search.distance[3] == DIST_INF);
        /* 源点等于目标返回 0；非法编号必须被拒绝并返回 0。 */
        assert(dijkstra(&graph, &search, 3, 3) && search.distance[3] == 0);
        assert(!dijkstra(&graph, &search, -1, 0) && !dijkstra(&graph, &search, 0, 4));
        search_free(&search);
    }
    graph_free(&graph);
    /* 64 位边界：两条 2^63-1 的弧相加恰为 UINT64_MAX-1，仍须与 DIST_INF 区分。 */
    write_fixture("p sp 3 2\na 1 2 9223372036854775807\na 2 3 9223372036854775807\n");
    assert(graph_load(&graph, "test_graph.tmp", error, sizeof(error)));
    for (int kind = 0; kind < 2; ++kind) {
        assert(search_init(&search, 3, (HeapKind)kind));
        assert(dijkstra(&graph, &search, 0, 2));
        assert(search.distance[2] == UINT64_MAX - 1);
        search_free(&search);
    }
    graph_free(&graph);
    assert(remove("test_graph.tmp") == 0);
    puts("PASS parser: 15 rejected inputs, zero/parallel/self edges, unreachable, 64-bit boundary");
}

/* 检查 previous 链确实构成一条从 source 到 target 的路径，且沿路径各弧最小权值
 * 之和等于报告的最短距离。不可达顶点直接跳过。 */
static void check_path(const Graph *graph, const Search *search, int source, int target)
{
    uint64_t total = 0;
    int vertex = target, length = 0;
    if (search->distance[target] == DIST_INF) return;
    while (vertex != source) {
        int parent = search->previous[vertex];
        uint64_t edge = DIST_INF;
        /* 步数上限设为顶点数，若前驱链成环会立即触发断言而不是死循环。 */
        assert(parent >= 0 && parent < graph->vertices && ++length < graph->vertices);
        /* 重边时取 parent->vertex 的最小权值作为路径上的实际弧权。 */
        for (size_t i = graph->offset[parent]; i < graph->offset[parent + 1]; ++i)
            if (graph->target[i] == vertex && graph->weight[i] < edge) edge = graph->weight[i];
        assert(edge != DIST_INF);
        total += edge;
        vertex = parent;
    }
    assert(total == search->distance[target]);
}

/* 独立对拍：手工构造 100 张 1..32 个顶点的随机有向图（含不可达与零权弧），
 * 用 Floyd–Warshall 算出全源最短路真值，再逐个起终点核对两种堆的距离与路径，
 * 并分别覆盖"完整单源"与"目标出堆提前终止"两种终止方式。 */
static void graph_tests(void)
{
    uint64_t comparisons = 0;
    for (int test = 0; test < 100; ++test) {
        Graph graph;
        Search searches[2];
        /* 顶点数在 1..32 之间循环，弧密度随 test % 4 递增（0%、25%、50%、75%）。 */
        int n = 1 + test % 32;
        uint64_t oracle[32][32];
        size_t count = 0;
        memset(&graph, 0, sizeof(graph));
        graph.vertices = n;
        graph.offset = array_alloc((size_t)n + 1, sizeof(*graph.offset));
        graph.target = array_alloc((size_t)n * (size_t)n, sizeof(*graph.target));
        graph.weight = array_alloc((size_t)n * (size_t)n, sizeof(*graph.weight));
        assert(graph.offset && graph.target && graph.weight);
        /* 直接以 CSR 形式构造图：offset 递增记录弧数，同时初始化真值矩阵。 */
        for (int i = 0; i < n; ++i) {
            graph.offset[i] = count;
            for (int j = 0; j < n; ++j) {
                oracle[i][j] = i == j ? 0 : DIST_INF;
                if (next_random() % 100 < (uint32_t)(test % 4 * 25)) {
                    uint64_t weight = next_random() % 100;
                    graph.target[count] = j;
                    graph.weight[count++] = weight;
                    if (weight < oracle[i][j]) oracle[i][j] = weight;
                }
            }
        }
        graph.offset[n] = graph.arcs = count;
        /* Floyd-Warshall 与 Dijkstra、两种堆完全独立，作为小图真值。 */
        for (int k = 0; k < n; ++k)
            for (int i = 0; i < n; ++i)
                for (int j = 0; j < n; ++j)
                    if (oracle[i][k] != DIST_INF && oracle[k][j] != DIST_INF && oracle[i][k] + oracle[k][j] < oracle[i][j])
                        oracle[i][j] = oracle[i][k] + oracle[k][j];
        for (int kind = 0; kind < 2; ++kind) {
            assert(search_init(&searches[kind], n, (HeapKind)kind));
            for (int source = 0; source < n; ++source) {
                /* 先跑完整单源（target = -1），核对全部顶点与路径。 */
                assert(dijkstra(&graph, &searches[kind], source, -1));
                for (int target = 0; target < n; ++target) {
                    assert(searches[kind].distance[target] == oracle[source][target]);
                    check_path(&graph, &searches[kind], source, target);
                    ++comparisons;
                }
                /* 再对每个目标单独跑一次提前终止，结果必须与完整单源一致。 */
                for (int target = 0; target < n; ++target) {
                    assert(dijkstra(&graph, &searches[kind], source, target));
                    assert(searches[kind].distance[target] == oracle[source][target]);
                    check_path(&graph, &searches[kind], source, target);
                    ++comparisons;
                }
            }
            search_free(&searches[kind]);
        }
        graph_free(&graph);
    }
    printf("PASS Floyd-Warshall: 100 graphs, %" PRIu64 " distance/path checks, full/early-stop/reuse\n", comparisons);
}

int main(void)
{
    heap_tests();
    parser_tests();
    graph_tests();
    puts("ALL TESTS PASSED");
    return 0;
}
