/* Link with -Wl,--wrap=malloc to fail the first position allocation.
 * With one input document, the first 16-byte allocation is doc_source;
 * the second is Position on the tested 64-bit Windows ABI. */
#include <stddef.h>
void *__real_malloc(size_t size);
void *__wrap_malloc(size_t size)
{
    static int calls = 0;
    if (size == 16 && ++calls == 2)
        return NULL;
    return __real_malloc(size);
}
