/* SAT 核心的测试入口：读取变量数、子句数和每行的带符号文字（0 结束）。
 * 与花园建模分开验证冲突学习；仅供测试，不参与最终评测程序。 */
#include "../sat.h"
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int variables, clauses, i;
    Sat *solver;
    while (scanf("%d%d",&variables,&clauses)==2) {
    if (variables<0 || variables>1000 || clauses<0) return 1;
    solver=sat_create(variables);
    for (i=0;i<clauses;++i) {
        int literals[1000], count=0, literal;
        while (scanf("%d",&literal)==1 && literal) {
            if (count>=1000 || literal < -variables || literal>variables) { sat_destroy(solver); return 1; }
            literals[count++]=literal>0 ? 2*(literal-1) : 2*(-literal-1)+1;
        }
        sat_add_clause(solver,literals,count);
    }
    if (!sat_solve(solver)) puts("UNSAT");
    else {
        printf("SAT");
        for (i=0;i<variables;++i) printf(" %d",sat_value(solver,i));
        putchar('\n');
    }
    {
        SatStats stats=sat_stats(solver);
        fprintf(stderr,"%llu %llu %llu\n",(unsigned long long)stats.conflicts,
            (unsigned long long)stats.learned,(unsigned long long)stats.restarts);
    }
    sat_destroy(solver);
    }
    return 0;
}
