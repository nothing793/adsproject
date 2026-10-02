/* Compile with -ftrapv to check signed arithmetic at the position boundary. */
#include <stdio.h>
#include "index.h"
int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    FILE *in = fopen(argv[1], "rb");
    if (!in) return 1;
    inverted_index *idx = index_load(in);
    fclose(in);
    if (!idx) return 1;
    FILE *out = fopen(argv[2], "wb");
    if (!out) { index_free(idx); return 1; }
    long terms = index_save(idx, out);
    int close_status = fclose(out);
    index_free(idx);
    return terms < 0 || close_status ? 1 : 0;
}
