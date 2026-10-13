#include "dijkstra.h"
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define HEAP_N 128
static uint32_t random_state = UINT32_C(20261013);
static uint32_t next_random(void)
{
    random_state = random_state * UINT32_C(1664525) + UINT32_C(1013904223);
    return random_state;
}

static int key_less(const uint64_t *keys, int a, int b)
{
    return keys[a] < keys[b] || (keys[a] == keys[b] && a < b);
}

/* 独立遍历所有环和树，检查链表互逆、父指针、度数、堆序与唯一性。 */
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
        if (parent >= 0) assert(!key_less(heap->distance, node, parent));
        else assert(!entry->mark);
        assert(audit_ring(heap, entry->child, node, seen) == entry->degree);
        node = entry->right;
        assert(++siblings <= heap->capacity);
    } while (node != first);
    return siblings;
}

static void audit_heaps(const BinaryHeap *binary, const FibonacciHeap *fibonacci, const unsigned char *active)
{
    unsigned char seen[HEAP_N] = {0};
    int size = 0, minimum = -1;
    audit_ring(fibonacci, fibonacci->minimum, -1, seen);
    for (int i = 0; i < HEAP_N; ++i) {
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

static void heap_tests(void)
{
    uint64_t keys[HEAP_N] = {0};
    unsigned char active[HEAP_N] = {0};
    BinaryHeap binary;
    FibonacciHeap fibonacci;
    int cascade = -1;
    assert(binary_init(&binary, HEAP_N, keys));
    assert(fibonacci_init(&fibonacci, HEAP_N, keys));
    for (int i = 0; i < HEAP_N; ++i) {
        keys[i] = UINT64_C(1000000) + (uint64_t)i;
        binary_update(&binary, i); fibonacci_update(&fibonacci, i); active[i] = 1;
    }
    assert(binary_pop(&binary) == 0 && fibonacci_pop(&fibonacci) == 0);
    active[0] = 0;
    for (int i = 1; i < HEAP_N; ++i)
        if (fibonacci.nodes[i].parent >= 0 && fibonacci.nodes[i].degree >= 2) { cascade = i; break; }
    assert(cascade >= 0);
    /* 显式触发同一非根节点失去两个孩子，覆盖 mark 和级联切割。 */
    for (int cut = 0; cut < 2; ++cut) {
        int child = fibonacci.nodes[cascade].child;
        keys[child] = (uint64_t)(2 - cut);
        binary_update(&binary, child); fibonacci_update(&fibonacci, child);
        if (!cut) assert(fibonacci.nodes[cascade].mark && fibonacci.nodes[cascade].parent >= 0);
        else assert(fibonacci.nodes[cascade].parent == -1 && !fibonacci.nodes[cascade].mark);
        audit_heaps(&binary, &fibonacci, active);
    }
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
            if (!active[vertex]) keys[vertex] = UINT64_C(1000000000) + next_random();
            else keys[vertex] /= 2;
            binary_update(&binary, vertex); fibonacci_update(&fibonacci, vertex); active[vertex] = 1;
        }
        audit_heaps(&binary, &fibonacci, active);
        if (step % 997 == 0) {
            binary_reset(&binary); fibonacci_reset(&fibonacci);
            memset(active, 0, sizeof(active));
            audit_heaps(&binary, &fibonacci, active);
        }
    }
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

static void write_fixture(const char *text)
{
    FILE *file = fopen("test_graph.tmp", "w");
    assert(file && fputs(text, file) >= 0);
    assert(fclose(file) == 0);
}

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
    assert(parse_uint64("18446744073709551615", &number) && number == UINT64_MAX);
    assert(!parse_uint64("18446744073709551616", &number));
    assert(!parse_uint64("-1", &number) && !parse_uint64("1x", &number));
    for (size_t i = 0; i < sizeof(invalid) / sizeof(invalid[0]); ++i) {
        write_fixture(invalid[i]);
        assert(!graph_load(&graph, "test_graph.tmp", error, sizeof(error)));
    }
    write_fixture("c test\n p sp 4 6\na 1 2 10\na 1 2 3\na 2 3 0\na 1 3 9\na 3 3 0\na 3 1 4");
    assert(graph_load(&graph, "test_graph.tmp", error, sizeof(error)));
    for (int kind = 0; kind < 2; ++kind) {
        assert(search_init(&search, graph.vertices, (HeapKind)kind));
        assert(dijkstra(&graph, &search, 0, -1));
        assert(search.distance[0] == 0 && search.distance[1] == 3 && search.distance[2] == 3 && search.distance[3] == DIST_INF);
        assert(dijkstra(&graph, &search, 3, 3) && search.distance[3] == 0);
        assert(!dijkstra(&graph, &search, -1, 0) && !dijkstra(&graph, &search, 0, 4));
        search_free(&search);
    }
    graph_free(&graph);
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

static void check_path(const Graph *graph, const Search *search, int source, int target)
{
    uint64_t total = 0;
    int vertex = target, length = 0;
    if (search->distance[target] == DIST_INF) return;
    while (vertex != source) {
        int parent = search->previous[vertex];
        uint64_t edge = DIST_INF;
        assert(parent >= 0 && parent < graph->vertices && ++length < graph->vertices);
        for (size_t i = graph->offset[parent]; i < graph->offset[parent + 1]; ++i)
            if (graph->target[i] == vertex && graph->weight[i] < edge) edge = graph->weight[i];
        assert(edge != DIST_INF);
        total += edge;
        vertex = parent;
    }
    assert(total == search->distance[target]);
}

static void graph_tests(void)
{
    uint64_t comparisons = 0;
    for (int test = 0; test < 100; ++test) {
        Graph graph;
        Search searches[2];
        int n = 1 + test % 32;
        uint64_t oracle[32][32];
        size_t count = 0;
        memset(&graph, 0, sizeof(graph));
        graph.vertices = n;
        graph.offset = array_alloc((size_t)n + 1, sizeof(*graph.offset));
        graph.target = array_alloc((size_t)n * (size_t)n, sizeof(*graph.target));
        graph.weight = array_alloc((size_t)n * (size_t)n, sizeof(*graph.weight));
        assert(graph.offset && graph.target && graph.weight);
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
                assert(dijkstra(&graph, &searches[kind], source, -1));
                for (int target = 0; target < n; ++target) {
                    assert(searches[kind].distance[target] == oracle[source][target]);
                    check_path(&graph, &searches[kind], source, target);
                    ++comparisons;
                }
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
