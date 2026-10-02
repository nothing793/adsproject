/* Stress the EXISTING index.h backend, without modifying the submitted algorithm.
 * docs = logical document IDs, not physical files. Vocabulary keys are already stems.
 * vocabulary: one occurrence per distinct key; common: one long posting list.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "../index.h"

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "types") == 0)
    {
        printf("{\"pointer\":%zu,\"long\":%zu,\"int\":%zu,\"position\":%zu,\"posting\":%zu,\"index\":%zu,\"hashsize\":%d,\"long_max\":%ld}\n",
               sizeof(void *), sizeof(long), sizeof(int), sizeof(Position), sizeof(Posting),
               sizeof(inverted_index), hashsize, LONG_MAX);
        return 0;
    }
    if (argc != 3) return 2;
    int n = atoi(argv[2]);
    if (n <= 0) return 2;
    inverted_index *idx = index_create();
    if (!idx) return 1;
    clock_t start = clock();
    if (strcmp(argv[1], "docs") == 0)
    {
        for (int i = 0; i < n; i++)
            if (index_add_doc(&idx->docs, i) != 1) return 1;
    }
    else if (strcmp(argv[1], "vocabulary") == 0)
    {
        int ndocs = n < 500000 ? n : 500000;
        for (int i = 0; i < ndocs; i++)
            if (index_add_doc(&idx->docs, i) != 1) return 1;
        for (int i = 0; i < n; i++)
        {
            char key[64];
            snprintf(key, sizeof(key), "term%010dx", i);
            if (index_add_position(idx, key, i % ndocs, i / ndocs) != 1) return 1;
        }
    }
    else if (strcmp(argv[1], "common") == 0)
    {
        if (index_add_doc(&idx->docs, 0) != 1) return 1;
        for (int i = 0; i < n; i++)
            if (index_add_position(idx, "common", 0, i) != 1) return 1;
    }
    else return 2;
    double insert_seconds = (double)(clock() - start) / CLOCKS_PER_SEC;
    FILE *out = fopen("index.bin", "wb");
    if (!out) return 1;
    long terms = index_save(idx, out);
    int close_result = fclose(out);
    int ndocs = idx->docs.count;
    index_free(idx);
    if (terms < 0 || close_result != 0) return 1;
    printf("{\"mode\":\"%s\",\"n\":%d,\"documents\":%d,\"terms\":%ld,\"insert_cpu_seconds\":%.6f}\n",
           argv[1], n, ndocs, terms, insert_seconds);
    return 0;
}
