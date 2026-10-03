# ADS 第四组 · 公用 Project 工作空间

本仓库是 ADS 课程第四组的公用 project 工作空间，用于存放各次 project 的源码、报告与测试材料。
集成分支为 `main`，仓库地址：<https://github.com/nothing793/adsproject>。
指导老师：陈昊。仓库内文档与提交说明一律使用中文。

| 角色 | 姓名 | GitHub | 权限范围 |
| --- | --- | --- | --- |
| admin | 陈昱年 | [@nothing793](https://github.com/nothing793) | 本仓库全部文件，含根目录 `readme.md`、`AGENTS.md`、`.gitignore`、`CODEOWNERS` |
| collaborator | 宋诗雨 | [@believeSong55](https://github.com/believeSong55) | `prN/` 下全部文件；根目录 `readme.md` 的第 1 节项目索引 |
| collaborator | 王宇轩 | [@uwindow](https://github.com/uwindow) | 同上 |

## 1. 项目索引

| 项目 | 状态 | 题目 | 源码 | 报告 |
| --- | --- | --- | --- | --- |
| [pr1](pr1/readme.md) | 已完成 | Roll Your Own Mini Search Engine（迷你搜索引擎） | [pr1/code/](pr1/code/README.md) | [pr1/documentation.md](pr1/documentation.md) |

新增 project 后必须在本表追加一行，并把「项目」列链接到该项目的 `prN/readme.md`。

## 2. 目录结构

每个 project 一个 `prN/` 目录，统一结构如下：

```
adsproject/
├── readme.md      # 本文件：仓库公约、结构与权限（仅 admin 可改）
├── AGENTS.md      # AI 助手在本仓库的工作约定（仅 admin 可改）
├── CODEOWNERS     # 评审归属：根目录公约文件由 admin 评审（见第 6 节）
├── .gitignore     # 追踪白名单，见第 4 节
└── prN/           # 第 N 次 project
    ├── readme.md       # 题面、结构介绍、编译与运行方法
    ├── code/           # C 源码，必须另有 code/README.md
    ├── documentation/  # 报告（Markdown 编写，定稿后转 PDF）
    └── testresult/     # 测试材料与测试结果，仅以压缩包形式提交
```

目录约定：

1. 新建文件夹时必须同时在该文件夹内创建 `README.md`，说明该目录的用途与包含内容。
2. 文件夹内容发生变化（新增、删除、重命名文件或调整功能）后，必须同步更新该文件夹下的 `README.md`。
3. `pr1` 属既有状态：报告是单文件 `pr1/documentation.md`，未使用 `documentation/` 目录、未转 PDF；后续 project 按上表结构执行。

## 3. 提交物规范

### 3.1 code

- 使用 C 语言，按 gcc 标准编译（`-std=c99`，编译告警必须清零）。
- 变量名尽量使用英文名词；注释与说明文档使用中文。
- `code/README.md` 必须写明：目录结构、变量与接口的使用情况、已实现的功能、题目要求实现的功能、未实现的功能。

### 3.2 documentation

- 报告开头固定注明：

  ```
  作者：陈昱年，宋诗雨，王宇轩
  第四组。
  陈昊老师。
  ```

- 章节结构：Chapter 1 问题描述；Chapter 2 设计结构；Chapter 3 测试及分析。
- 编写或修改 code 部分后，必须同步更新 Chapter 2；测试完成后必须补充 Chapter 3，并把测试材料与结果按 3.3 节提交。
- 先用 Markdown 编写，定稿后转为 PDF。

### 3.3 testresult

- 存放测试文件与测试结果：题目未要求提交、但测试过程中使用的材料，例如输入生成脚本、input、output、日志等。
- 过程性文件不保留；上传一律使用压缩包（zip / rar），不上传散文件。
- 测试材料与结果同时上传到 <https://github.com/nothing793/adsproject>。

### 3.4 readme

- 每个 `prN/readme.md` 需包含题面、结构介绍、编译与运行方法。
- 根目录 `readme.md` 只放仓库级公约（本文件），项目细节写进各自的 `prN/readme.md`。

## 4. 上传：追踪规则

`git` 只提交「交付物 + 仓库公约文件」，具体范围如下（实现见根目录 `.gitignore`）：

| 路径 | 追踪 | 说明 |
| --- | --- | --- |
| `readme.md`、`AGENTS.md`、`CODEOWNERS`、`.gitignore` | ✅ | 仓库级公约文件，仅 admin 可改 |
| `prN/code/**` | ✅ | C 源码、头文件、测试脚本，无条件追踪 |
| `prN/documentation/**` 与 `prN/documentation.md` | ✅ | 报告，无条件追踪 |
| `prN/readme.md` | ✅ | 项目 readme：题面、结构介绍、编译与运行方法 |
| `prN/testresult/*.zip`、`*.rar`、`*.7z` | ✅ | 仅压缩包形式 |
| `prN/testresult/**` 的其他文件 | ❌ | 过程文件、散文件不上传 |
| `prN/data/**`、`prN/results/**`、`prN/evidence/**` 等 | ❌ | 语料、实验结果、证据、截图、日志、临时索引、可执行文件 |

规则：

1. 每次 git 上传前必须逐条说明本次改动了哪些文件、为什么改；`git push` 的说明同样要求。
2. `.gitignore` 是追踪范围唯一的实现，改动白名单属仓库级变更，仅 admin 可执行，并须同步更新本节表格。
3. 未在本公约内规定的产物，放进该项目的 `prN/testresult/`，并在提交说明中注明。

## 5. 拉取：同步规则

1. 默认同步范围：`prN/code/**`、`prN/documentation/**`、各 `prN/readme.md`，以及仓库级文件（`readme.md`、`AGENTS.md`、`CODEOWNERS`、`.gitignore`）。
2. `prN/testresult/**` 体积较大，默认不拉取；需要时按需获取（`git sparse-checkout` 或单独下载压缩包）。
3. 需要全量内容时直接 `git clone` / `git pull`。

## 6. 权限与评审

- 仅 admin 可修改根目录 `readme.md`、`AGENTS.md`、`CODEOWNERS`、`.gitignore` 白名单。
- collaborator 可修改根目录 `readme.md` 的「介绍部分」，即第 1 节项目索引中与本人负责项目相关的行；以及 `prN/` 下的全部文件。
- 除第 1 节外，collaborator 不要直接修改根目录 `readme.md` 与 `AGENTS.md`，请按第 7 节提交修改意见。
- 根目录公约文件的改动由根目录 `CODEOWNERS` 指定评审人 `@nothing793`；要让评审成为合并的硬性条件，需 admin 在 GitHub 仓库设置的分支保护中开启 `Require a pull request before merging` 与 `Require review from Code Owners`。该设置只在 GitHub 网页端可改。

## 7. 未规定、冲突、歧义的处理

1. **未规定**：先按自己的判断完成，同时给出 readme 修改意见。
2. **与明文规定冲突**：以本 readme 为准；若确实无法执行，可先按自己的方案解决，但必须同时联系 admin 并给出修改意见。
3. **有歧义**：先联系 admin，不要自行决定。
4. 修改意见以根目录文件形式提交，命名为 `readme-feedback-<GitHub 用户名>-<YYYYMMDD>.md`，内容需写明：问题、复现方式、修改方案。admin 阅读后决定是否采纳，采纳并合并后由 admin 删除该文件。
