"""Generate the browser deck directly from the authoring data (stdlib only)."""
from __future__ import annotations

import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'data'
FILES = ['cards.json', 'knowledge.json', 'sources.json', 'review_policy.json']


def t(value):
    return escape(str(value)).replace('\n', '<br>')


def build(output):
    data={name:json.loads((SNAPSHOT/name).read_text()) for name in FILES}
    knowledge={item['id']:item for item in data['knowledge.json']}
    sources=data['sources.json']
    policy=data['review_policy.json']
    sections={s['id']:s['title'] for s in policy['sections']}
    cards=[]
    for c in sorted(data['cards.json'],key=lambda c:(knowledge[c['knowledge_ids'][0]]['section'],c['knowledge_ids'][0],not c['id'].endswith('-B'),c['id'])):
        facts=[knowledge[k] for k in c['knowledge_ids']]
        links=list(dict.fromkeys(sources[s]['url'] for f in facts for s in f['source_ids']))
        required=''.join('<li>'+t(value)+'</li>' for value in c['required'])
        answer='<div class="answer-text">'+t(c['answer'])+'</div>'
        answer+='<div class="answer-criteria"><div class="answer-heading">正解に必要な要素</div><ul>'+required+'</ul></div>'
        if c['accepted']:
            answer+='<div class="answer-accepted"><div class="answer-heading">許容表現の例</div>'+t('、'.join(c['accepted']))+'</div>'
        answer+='<div class="answer-explanation"><div class="answer-heading">補足</div>'+t(c['explanation'])+'</div>'
        answer+='<details class="answer-details"><summary>前提・対応する知識</summary><p>カード：'+t(c['id'])+'<br>知識：'+t('、'.join(c['knowledge_ids']))+'</p>'
        answer+=''.join('<p>'+t(f['conditions'])+'</p>' for f in facts)
        answer+='</details>'
        cards.append({'id':c['id'],'question':t(c['question']),'answer':answer,'html':True,
                      'section':facts[0]['section'],'section_title':sections[facts[0]['section']],
                      'sources':links,'kind':c['kind'],'knowledge_ids':c['knowledge_ids']})
    assert len({c['id'] for c in cards})==len(cards)
    # Content hash changes on any source edit, including a correction within one day.
    digest=sha256(b'\0'.join((SNAPSHOT/name).read_bytes() for name in FILES)).hexdigest()
    seed={'deck_id':'chapter-03-v2','revision':digest,'title':'Ethernet LAN 改訂版',
          'subtitle':'ネスペイージス 第3章','knowledge_count':len(knowledge),
          'question_count':len(cards),'sections':len(sections),'cards':cards}
    target=Path(output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(seed,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'file':str(target),'cards':len(cards),'knowledge':len(knowledge),'revision':digest},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist/deck.json')
    build(parser.parse_args().output)
