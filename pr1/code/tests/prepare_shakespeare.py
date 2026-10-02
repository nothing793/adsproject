#!/usr/bin/env python3
"""Extract the MIT site's corpus from its official Git mirror (no dependencies).

One play/poetry collection = one document. Sonnets are combined in catalogue order.
All original HTML is copied for audit; titles/speakers/stage directions are retained.
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('head', 'script', 'style'):
            self.hidden += 1
        if tag in ('br', 'p', 'blockquote', 'h1', 'h2', 'h3', 'b', 'i', 'tr'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('head', 'script', 'style'):
            self.hidden -= 1
        if tag in ('p', 'blockquote', 'h1', 'h2', 'h3', 'b', 'i', 'tr'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def visible(html, play=False):
    # elegy.html contains </TITLE without a closing '>': repair markup, not content.
    html = re.sub(r'</title\s*(?=<)', '</title>', html, flags=re.I)
    if play:
        # Exclude homepage/play navigation and any HTML metadata before ACT I.
        match = re.search(r'<h3\b', html, re.I)
        assert match, 'play body missing'
        html = html[match.start():]
    parser = VisibleText()
    parser.feed(html)
    lines = [' '.join(line.split()) for line in ''.join(parser.parts).splitlines()]
    return '\n'.join(line for line in lines if line) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mirror', type=Path)
    ap.add_argument('destination', type=Path)
    args = ap.parse_args()
    src, dst = args.mirror.resolve(), args.destination.resolve()
    (dst / 'corpus').mkdir(parents=True, exist_ok=True)
    (dst / 'html').mkdir(exist_ok=True)
    home = (src / 'index.html').read_text(encoding='latin1')
    pairs = re.findall(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', home, re.I | re.S)
    catalogue = [(p, re.sub('<[^>]+>', '', title).strip()) for p, title in pairs
                 if re.fullmatch(r'[^/]+/index.html', p) or p.startswith('Poetry/')]
    assert len(catalogue) == 42, f'unexpected catalogue size: {len(catalogue)}'
    manifest = []
    for doc_id, (link, title) in enumerate(catalogue):
        title = ' '.join(title.split())
        is_play = link.endswith('/index.html')
        if is_play:
            sources = [str(Path(link).parent / 'full.html').replace('\\', '/')]
        elif link == 'Poetry/sonnets.html':
            sonnets = (src / link).read_text(encoding='latin1')
            sources = ['Poetry/' + name for name in re.findall(
                r'href="(sonnet\.[^"]+\.html)"', sonnets, re.I)]
            assert len(sources) == 154 and len(set(sources)) == 154
        else:
            sources = [link]
        text = ''
        checksums = {}
        for name in sources:
            raw = (src / name).read_bytes()
            target = dst / 'html' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / name, target)
            checksums[name] = hashlib.sha256(raw).hexdigest()
            text += visible(raw.decode('latin1'), is_play)
        # Keep UTF-8; the existing C tokenizer splits on ASCII alphanumerics.
        filename = f'{doc_id:02d}_{Path(link).parent.name if is_play else Path(link).stem}.txt'
        target = dst / 'corpus' / filename
        target.write_text(text, encoding='utf-8', newline='\n')
        words = re.findall(r'[A-Za-z0-9]+', text)
        assert len(words) > 100
        assert not re.search(r'Shakespeare homepage|Entire play|Amazon\.com', text, re.I)
        manifest.append(dict(doc_id=doc_id, title=title, filename=filename, kind='play' if is_play else 'poetry',
                             words=len(words), bytes=target.stat().st_size,
                             sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                             urls=['https://shakespeare.mit.edu/' + name for name in sources],
                             html_sha256=checksums))
    commit = subprocess.check_output(['git', '-c', 'safe.directory=' + str(src), '-C', str(src),
                                      'rev-parse', 'HEAD'], text=True).strip()
    (dst / 'manifest.json').write_text(json.dumps(dict(mirror='https://github.com/TheMITTech/shakespeare',
        mirror_commit=commit, extraction='play from first h3; poems visible body; sonnets in catalogue order',
        documents=manifest), ensure_ascii=False, indent=2), encoding='utf-8')
    with (dst / 'documents.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['doc_id', 'title', 'filename', 'kind', 'words', 'bytes', 'sha256'])
        writer.writerows([d[k] for k in ['doc_id', 'title', 'filename', 'kind', 'words', 'bytes', 'sha256']]
                         for d in manifest)
    print(f'PASS: {len(manifest)} documents, {sum(d["words"] for d in manifest)} ASCII tokens; 154 sonnets included')


if __name__ == '__main__':
    main()
