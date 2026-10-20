/* Project 3 入口：严格读取单个花园，调用求解器，并按行优先输出方向状态。
 * 正常的无解返回 0 并输出 No Solution；输入错误返回 1，运行资源错误返回 2。
 * --stats 仅向标准错误输出实验统计，不改变题目规定的标准输出。 */
#include "fence.h"
#include <ctype.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

/* 逐字符解析有界非负整数，避免 scanf 在超出 int 范围时的未定义行为。
 * 不接受负数、非整数或一个 token 内夹杂字符。 */
static int read_integer(int maximum, int *value)
{
    int ch, number=0, digits=0, invalid=0;
    do { ch=getchar(); } while (ch!=EOF && isspace((unsigned char)ch));
    if (ch=='+') ch=getchar();
    while (ch!=EOF && !isspace((unsigned char)ch)) {
        if (ch<'0' || ch>'9') invalid=1;
        else {
            int digit=ch-'0'; digits=1;
            if (digit>maximum || number>(maximum-digit)/10) invalid=1;
            else if (!invalid) number=number*10+digit;
        }
        ch=getchar();
    }
    if (invalid || !digits) return 0;
    *value=number; return 1;
}

/* 标准输出仅含题目规定的结果，统计和输入错误均写入标准错误。 */
int main(int argc, char **argv)
{
    Garden garden;
    FenceResult result;
    int statistics=0, r,c,ch,solved;
    if (argc==2 && !strcmp(argv[1],"--stats")) statistics=1;
    else if (argc!=1) { fputs("用法: fence [--stats]\n",stderr); return 1; }
    if (!read_integer(FENCE_LIMIT,&garden.rows) || garden.rows<2 ||
        !read_integer(FENCE_LIMIT,&garden.columns) || garden.columns<2) {
        fputs("输入错误: 行列数须在 2 到 50 之间\n",stderr); return 1;
    }
    for (r=0;r<garden.rows;++r) for (c=0;c<garden.columns;++c)
        if (!read_integer(4,&garden.degree[r][c])) {
            fputs("输入错误: 缺少网格数值或度数不在 0 到 4 之间\n",stderr); return 1;
        }
    do { ch=getchar(); } while (ch!=EOF && isspace((unsigned char)ch));
    if (ch!=EOF || ferror(stdin)) { fputs("输入错误: 多余数据或读取失败\n",stderr); return 1; }
    solved=fence_solve(&garden,&result);
    if (!solved) puts("No Solution");
    else for (r=0;r<garden.rows;++r) for (c=0;c<garden.columns;++c)
        if (garden.degree[r][c]) printf("%d %d %d %d %d %d\n",r+1,c+1,
            result.state[r][c][0],result.state[r][c][1],
            result.state[r][c][2],result.state[r][c][3]);
    if (statistics) {
        SatStats s=result.search;
        fprintf(stderr,"{\"satisfiable\":%s,\"connectors\":%d,\"variables\":%d,"
            "\"clauses\":%d,\"crossings\":%d,\"decisions\":%" PRIu64 ","
            "\"propagations\":%" PRIu64 ",\"conflicts\":%" PRIu64 ","
            "\"learned\":%" PRIu64 ",\"restarts\":%" PRIu64 "}\n",
            solved?"true":"false",result.connectors,s.variables,s.clauses,
            result.crossings,s.decisions,s.propagations,s.conflicts,s.learned,s.restarts);
    }
    /* 显式刷新后检查写入失败；不能只检查尚未落到输出句柄的缓冲区。 */
    if (fflush(stdout)==EOF) return 2;
    return ferror(stdout) ? 2 : 0;
}
