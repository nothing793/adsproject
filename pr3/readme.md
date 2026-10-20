# 题目：
花园设计师画了一张栅栏布局图，如图1所示。这里我们假设花园是一个由单位方格组成的 \(n \times m\) 的矩形空间。图中所有的栅栏都是水平或垂直的，并通过特定指定位置的连接器连接在一起。当工人们把连接器搬到相应位置时，他们发现设计图纸不见了……所以现在你面临着图2中的情况：几个 k 路连接器被放置在了一些位置上。你的工作是恢复图纸，即从图2恢复出图1。
![alt text](image.png)

**注意**：栅栏不能弯曲，也不能在没有连接器的情况下相互交叉。拐角只能通过连接器形成。

**输入说明：**
每个输入文件包含一个测试用例。对于每个用例，第一行给出两个正整数：\(n\) 和 \(m\)（\(1 < n, m \le 50\)），分别是花园的行数和列数。
接下来有 \(n\) 行，每行包含 \(m\) 个用空格分隔的数字。每个数字要么是一个正整数 \(k\)（\(1 \le k \le 4\)），表示连接器的度数，要么是 \(0\)，表示该位置没有连接器。

**输出说明：**
对于每个用例，如果无解，只需在一行中输出 `No Solution`。否则，逐行扫描花园（每行从左到右），在一行中输出每个连接器的状态。输出格式如下：

`row col up down left right`

其中 `row` 和 `col` 是连接器位置的行号和列号（行号从上到下从 \(1\) 开始计数，列号从左到右从 \(1\) 开始计数）；\(4\) 个方向 `up`（上）、`down`（下）、`left`（左）和 `right`（右）的状态为 \(1\) 或 \(0\)，分别对应该方向上是否连接了栅栏。
另一方面，解可能不唯一。输出任意一个即可。
一行中的数字必须用空格分隔，且行首和行尾不得有多余空格。

```bash
Sample Input 1:
5 6
0 0 2 0 0 2
1 3 3 1 0 0
2 2 1 0 0 2
0 0 0 0 0 1
2 0 2 0 0 2

Sample Output 1:
1 3 0 1 0 1
1 6 0 1 1 0
2 1 0 0 0 1
2 2 0 1 1 1
2 3 1 0 1 1
2 4 0 0 1 0
3 1 0 1 0 1
3 2 1 0 1 0
3 3 0 0 0 1
3 6 1 0 1 0
4 6 0 1 0 0
5 1 1 0 0 1
5 3 0 0 1 1
5 6 1 0 1 0

Sample Input 2:
5 6
0 0 2 0 0 2
1 3 3 1 0 0
2 2 1 0 0 1
0 0 0 0 0 1
2 0 2 0 0 2

Sample Output 2:
No Solution

Sample Input 3:
3 5
1 1 2 0 1
1 0 3 0 2
1 2 1 0 1

Sample Output 3:
1 1 0 0 0 1
1 2 0 0 1 0
1 3 0 1 0 1
1 5 0 0 1 0
2 1 0 0 0 1
2 3 1 0 1 1
2 5 0 1 1 0
3 1 0 0 0 1
3 2 0 0 1 1
3 3 0 0 1 0
3 5 1 0 0 0
```

# 评分细则
Grading Policy:
Programming: Write the program (10 pts.) with sufficient comments.

Testing: Provide a set of test cases to fill in a test report (3 pts.).  Write analysis and comments (3 pts.).

Documentation: Chapter 1 (1 pt.), Chapter 2 (2 pts.), and finally a complete report (1 point for overall style of documentation).