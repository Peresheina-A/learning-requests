"""Файловый источник реакций группы «информация + подтверждение»."""
import json
from pathlib import Path

ROOT=Path(__file__).with_name('checklist_files')
DOCUMENTS={
    'personal-data':('Основы работы с персональными данными','personal-data.txt'),
    'internal-materials':('Работа с внутренними материалами Авито','internal-materials.txt'),
}

def task(task_id):
    data=json.loads((ROOT/'information_group.json').read_text(encoding='utf-8-sig'))
    item=data.get(task_id)
    if item is not None:
        item=dict(item)
        item['required_documents']=[{'id':key,'title':DOCUMENTS[key][0]} for key in item.get('required_documents',[])]
    return item

def document(document_id):
    if document_id not in DOCUMENTS:
        return None
    title,filename=DOCUMENTS[document_id]
    return {'title':title,'text':(ROOT/filename).read_text(encoding='utf-8-sig')}

def work_tools():
    return json.loads((ROOT/'work-tools.json').read_text(encoding='utf-8-sig'))
