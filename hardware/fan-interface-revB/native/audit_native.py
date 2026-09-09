"""Read the saved JLCEDA documents without changing the originals."""
import json
from collections import Counter
from pathlib import Path


def parse(path):
    docs = []
    for line in Path(path).read_text().splitlines():
        if '||' not in line:
            continue
        head, data = line.split('||', 1)
        h = json.loads(head)
        if not data.rstrip('|').strip():
            continue
        d = json.loads(data.rstrip('|'))
        if h['type'] == 'DOCHEAD':
            docs.append([])
        docs[-1].append((h, d))
    return docs


if __name__ == '__main__':
    docs = parse(Path(__file__).with_name('PCB1-geometry-fixed.epru'))
    page = next(d for d in docs if d[0][1].get('docType') == 'PCB')
    libs = {d[0][1].get('uuid'): d for d in docs}
    attrs = {}
    for h, d in page:
        if h['type'] == 'ATTR':
            attrs.setdefault(d['parentId'], {})[d['key']] = d['value']
    print('page record types:', dict(Counter(h['type'] for h, d in page)))
    for h, d in page:
        if h['type'] != 'COMPONENT':
            continue
        a = attrs[h['id']]
        fp = libs.get(a.get('Footprint'), [])
        print(a.get('Designator'), d['x'], d['y'], d['angle'], a)
        for ph, pd in fp:
            if ph['type'] == 'PAD':
                print(' PAD', pd)
        dev = libs.get(a.get('Device'), [])
        for dh, dd in dev:
            if dh['type'] == 'ATTR':
                print(' DEV', dd.get('key'), dd.get('value'))
