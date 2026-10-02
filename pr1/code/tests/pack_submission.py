#!/usr/bin/env python3
"""Make a GitHub-ready overlay ZIP, excluding generated stress binaries/databases."""
import json
import zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[2]
outputs=root.parent
archive=outputs/'adsproject_作业补充_可上传.zip'
excluded=[]
included=[]
def keep(rel):
    parts=rel.parts
    if '__pycache__' in parts or parts[0]=='bin': return False
    if len(parts)>1 and parts[0]=='results' and parts[1] in ['bonus','edge_cases']: return False
    if rel.suffix in ['.exe','.pyc','.sqlite']: return False
    if rel.name in ['index.bin','roundtrip.bin','tokens.txt','output.txt','index.bin.tmp']: return False
    return True

gitignore='''# Generated program binaries / large experiment scratch
pr1/bin/
pr1/code/*.exe
pr1/code/index_gen
pr1/code/query
**/__pycache__/
**/*.pyc
**/index.bin
**/roundtrip.bin
**/index.bin.tmp
**/tokens.txt
**/output.txt
pr1/results/bonus/
pr1/results/edge_cases/
work/
*.sqlite
'''
project_readme='''# ADS Project

作业与完整报告在 [pr1](pr1/readme.md)。

- [完整实验报告](pr1/documentation.md)
- [实验过程素材](pr1/实验记录与报告素材.md)
- [截图说明](pr1/evidence/截图说明.md)

真实 MIT 全集：42 文档、956,647 tokens；独立正确性检查 78 项通过。
Bonus 实测为 50 万逻辑文档 / 100 万不同词；4 亿不同词仅做估算，未宣称完整规模已跑过。
'''
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.writestr('.gitignore',gitignore)
    z.writestr('README.md',project_readme)
    for file in sorted(root.rglob('*')):
        if not file.is_file(): continue
        rel=file.relative_to(root)
        if not keep(rel):
            excluded.append(str(rel));continue
        z.write(file,('pr1/'+rel.as_posix()))
        included.append(dict(path='pr1/'+rel.as_posix(),bytes=file.stat().st_size))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert 'pr1/evidence/screenshots/08.png' in z.namelist()
    assert 'pr1/documentation.md' in z.namelist()
(outputs/'提交文件清单.json').write_text(json.dumps(dict(repository='nothing793/adsproject',base_commit='5d36a46145236b406eb37643db4e5cefcb351f3a',
    archive=archive.name,archive_bytes=archive.stat().st_size,included=included,excluded=excluded,
    remote_upload_status='not uploaded: GitHub connector write requests returned 403 Resource not accessible by integration; target repository is not available through the current app installation'),ensure_ascii=False,indent=2),encoding='utf-8')
(outputs/'上传说明.md').write_text('''# 作业补充文件包

目标： https://github.com/nothing793/adsproject ，main 基线为 5d36a46145236b406eb37643db4e5cefcb351f3a。

当前已完成本地修改、78 项全集检查、Bonus 实测与 8 张截图。GitHub 插件已确认连接 believeSong55；账号对目标仓库的元数据显示 push=true，但创建 Git tree 和上传 README.md 的实际请求均返回 403 Resource not accessible by integration。当前安装位于 believeSong55 账号，其可访问仓库列表为空，目标仓库属于 nothing793；**尚未上传远程仓库**。远程 main 经再次检查仍为上述基线。

需要仓库所有者 nothing793 为此仓库安装或授权当前 GitHub 连接使用的应用，并授予 Contents 写权限；随后可继续上传。账号本身的协作者写权限与 GitHub App 的仓库授权是两个独立条件。

`adsproject_作业补充_可上传.zip` 是覆盖包：解压后含仓库根 README.md、.gitignore 和 pr1/。如果自行上传，应上传解压后的目录内容，而不是只将 ZIP 存进仓库。它保留全部源码、真实语料、来源 HTML、报告、测量、原始日志和截图；排除 exe、token dump 与大型临时压力索引。

本地完整结果仍在 pr1/，包括已构建索引和 exe。源码修改 diff 在 pr1/evidence/source_changes.patch。若后续发现远程基线有新提交，应先对比差异后再提交，不能直接覆盖别人的新改动。

完整报告：pr1/documentation.md；报告素材：pr1/实验记录与报告素材.md；截图：pr1/evidence/screenshots/01.png 至 08.png。
''',encoding='utf-8')
print(f'PASS: {archive.name}; {len(included)+2} files; {archive.stat().st_size} bytes; ZIP integrity OK')
