#!/usr/bin/env python3
"""将报告 Markdown 转为 HTML，使用 LaTeX 公式和代码高亮后打印矢量 PDF。"""
import argparse
import html
import os
import re
import shutil
import subprocess
from pathlib import Path


def inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',text)
    return re.sub(r'\[([^]]+)\]\(([^)]+)\)',lambda m: m[1]+' ('+m[2]+')',text)


def markdown_body(source):
    lines=source.read_text(encoding='utf-8').splitlines(); blocks=[]; i=0; cover=True
    blocks.append('<header class="cover">')
    while i<len(lines):
        line=lines[i].strip()
        if not line:
            i+=1; continue
        if line=='$$':
            math=[]; i+=1
            while i<len(lines) and lines[i].strip()!='$$':
                math.append(lines[i]); i+=1
            assert i<len(lines),'缺少公式结束分隔符'
            blocks.append('<div class="equation">$$'+html.escape('\n'.join(math))+'$$</div>'); i+=1; continue
        if line.startswith('```'):
            language=line[3:].strip() or 'text'; code=[]; i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i+=1
            labels={'python':'Python 风格伪代码', 'c':'C99 · 实现片段',
                    'bash':'Bash · 复现命令', 'text':'样例输出'}
            label=labels.get(language,language)
            code_class='nohighlight' if language=='text' else 'language-'+language
            blocks.append('<div class="code-block"><div class="code-label">'+html.escape(label)+
                          '</div><pre><code class="'+html.escape(code_class)+'">'+
                          html.escape('\n'.join(code))+'</code></pre></div>'); i+=1; continue
        image=re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)',line)
        if image:
            blocks.append('<figure><img src="'+html.escape(image[2],quote=True)+'"><figcaption>'+inline(image[1])+'</figcaption></figure>'); i+=1; continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                values=[v.strip() for v in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',v.replace(' ','')) for v in values):
                    rows.append(values)
                i+=1
            markup='<table><thead><tr>'+''.join('<th>'+inline(v)+'</th>' for v in rows[0])+'</tr></thead><tbody>'
            for row in rows[1:]:
                markup+='<tr>'+''.join('<td>'+inline(v)+'</td>' for v in row)+'</tr>'
            blocks.append(markup+'</tbody></table>'); continue
        if line.startswith('# '):
            blocks.append('<h1>'+inline(line[2:])+'</h1>'); i+=1; continue
        if line.startswith('## '):
            if cover:
                blocks.append('</header><main>'); cover=False
            blocks.append('<h2>'+inline(line[3:])+'</h2>'); i+=1; continue
        if line.startswith('### '):
            blocks.append('<h3>'+inline(line[4:])+'</h3>'); i+=1; continue
        paragraph=[line]; i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','![','$$')):
            paragraph.append(lines[i].strip()); i+=1
        following=i
        while following<len(lines) and not lines[following].strip():
            following+=1
        classes=[]
        if following<len(lines) and lines[following].strip()=='$$':
            classes.append('math-lead')
        if following<len(lines) and lines[following].startswith('```'):
            classes.append('code-lead')
        if re.match(r'^\[\d+\]',paragraph[0]):
            classes.append('reference')
        attribute=' class="'+' '.join(classes)+'"' if classes else ''
        blocks.append('<p'+attribute+'>'+'<br>'.join(inline(p) for p in paragraph)+'</p>')
    blocks.append('</main>' if not cover else '</header>')
    return '\n'.join(blocks)


TEMPLATE=r'''<!DOCTYPE html>
<html lang="zh-CN"><meta charset="utf-8"><title>Project 3 栅栏布局恢复</title>
<style>
@page {size:A4; margin:20mm 18mm 18mm}
* {box-sizing:border-box}
:root {--ink:#202020; --syntax:#274b6b; --paper:#fff; --panel:#f7f8f9; --rule:#d7d7d7}
body {max-width:174mm; margin:0 auto; font:400 11pt/1.7 "Microsoft YaHei","Noto Sans CJK SC",sans-serif; color:var(--ink); background:var(--paper)}
.cover {min-height:240mm; break-after:page; display:flex; flex-direction:column; align-items:center; justify-content:center}
.cover h1 {font-size:23pt; font-weight:600; margin-bottom:25mm}
.cover p {max-width:150mm; text-align:center; font-size:12pt}
h2 {font:600 16pt/1.5 "Microsoft YaHei","Noto Sans CJK SC",sans-serif; margin:22pt 0 13pt; break-after:avoid; color:var(--ink)}
h3 {font:600 11.5pt/1.6 "Microsoft YaHei","Noto Sans CJK SC",sans-serif; margin:16pt 0 8pt; break-after:avoid; color:var(--ink)}
p {margin:6pt 0 8pt; orphans:3; widows:3; text-align:justify}
p.math-lead,p.code-lead {break-after:avoid}
p.reference {text-align:left; overflow-wrap:anywhere}
table {width:100%; border-collapse:collapse; font-size:9.5pt; line-height:1.5; margin:10pt 0 14pt; table-layout:auto; color:var(--ink)}
thead {display:table-header-group}
tr {break-inside:avoid}
th,td {padding:5pt 6pt; border-bottom:.4pt solid var(--rule); text-align:left; overflow-wrap:anywhere; vertical-align:top; color:var(--ink)}
th {background:#f0f0f0; font-family:inherit; font-weight:600}
code {font:400 10pt/1.6 Consolas,"Microsoft YaHei",monospace; color:var(--ink); overflow-wrap:anywhere}
.code-block {background:var(--panel); border:.5pt solid var(--rule); border-radius:3pt; margin:10pt 0 14pt; break-inside:avoid; overflow:hidden}
.code-label {font-size:8.5pt; font-weight:600; line-height:1.4; color:var(--ink); padding:6pt 11pt; border-bottom:.5pt solid var(--rule); background:#eef0f2}
pre {padding:9pt 11pt 11pt; margin:0; white-space:pre; tab-size:4; color:var(--ink)}
pre code {display:block; font-size:9.4pt; line-height:1.55; white-space:pre; overflow-wrap:normal}
.hljs,.hljs * {color:var(--ink)}
.hljs .hljs-keyword,.hljs .hljs-type,.hljs .hljs-literal {color:var(--syntax); font-weight:600}
.hljs-comment {font-style:normal; font-weight:400}
.equation {font-size:11.5pt; font-weight:400; color:var(--ink); margin:13pt 0 15pt; break-inside:avoid; overflow:visible}
mjx-container {font-weight:400!important; color:var(--ink)!important}
mjx-container[jax="SVG"] {font-size:100%!important}
mjx-container[display="true"] {margin:.5em 0!important}
figure {margin:14pt 0 18pt; break-inside:avoid}
figure img {display:block; width:100%; max-height:84mm; object-fit:contain}
figcaption {font-size:9.5pt; margin-top:6pt; color:var(--ink)}
@media screen {body {padding:20px 0; background:#fff}}
</style>
<script>
window.MathJax={tex:{inlineMath:[['$','$']],displayMath:[['$$','$$']],processEscapes:true},svg:{fontCache:'global'},options:{enableMenu:false}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg.js"></script>
<script defer src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.12.0/build/highlight.min.js"></script>
<body>__CONTENT__</body></html>'''


def render(source, destination, font=None, bold_font=None):
    # font 参数保留与图表入口兼容；报告采用统一字族及单一文字颜色。
    page=destination.with_suffix('.html')
    page.write_text(TEMPLATE.replace('__CONTENT__',markdown_body(source)),encoding='utf-8')
    node=os.environ.get('NODE_EXE') or shutil.which('node')
    if not node:
        raise RuntimeError('需要 Node.js、Playwright 和 Edge 才能导出 PDF')
    command=[node,str(Path(__file__).with_name('render_report.cjs')),str(page),str(destination)]
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    print(result.stdout.strip())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path); parser.add_argument('destination',type=Path)
    args=parser.parse_args(); render(args.source.resolve(),args.destination.resolve())


if __name__=='__main__':
    main()
