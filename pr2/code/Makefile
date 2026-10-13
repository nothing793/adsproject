CC = gcc
CFLAGS = -std=c99 -O2 -Wall -Wextra -Wpedantic
COMMON = graph.c binary_heap.c fibonacci_heap.c dijkstra.c
HEADERS = graph.h binary_heap.h fibonacci_heap.h dijkstra.h

.PHONY: all test clean
all: shortest_path benchmark

shortest_path: main.c $(COMMON) $(HEADERS)
	$(CC) $(CFLAGS) main.c $(COMMON) -o $@

benchmark: benchmark.c $(COMMON) $(HEADERS)
	$(CC) $(CFLAGS) benchmark.c $(COMMON) -o $@

test: test_runner
	./test_runner

test_runner: tests/test.c $(COMMON) $(HEADERS)
	$(CC) $(CFLAGS) -I. tests/test.c $(COMMON) -o $@

clean:
	rm -f shortest_path shortest_path.exe benchmark benchmark.exe test_runner test_runner.exe
