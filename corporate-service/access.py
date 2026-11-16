"""Сценарий рабочих доступов; завершение через 5 секунд."""
import json
import secrets
import time
from database import database

ACCESS_LIST=['Корпоративная почта','Рабочее пространство команды','Система задач','Аналитическая база данных']

def initialize():
    with database() as c:
        c.execute('CREATE TABLE IF NOT EXISTS access_jobs (id INTEGER PRIMARY KEY,employee_id INTEGER UNIQUE,tools TEXT,created REAL,status TEXT,code TEXT)')

def create(employee_id):
    with database() as c:
        c.execute('INSERT OR IGNORE INTO access_jobs(employee_id,tools,created,status) VALUES (?,?,?,?)',(employee_id,json.dumps(ACCESS_LIST,ensure_ascii=False),time.time(),'processing'))
        row=c.execute('SELECT id FROM access_jobs WHERE employee_id=?',(employee_id,)).fetchone()
    return get(row['id'],employee_id)

def get(job_id,employee_id):
    with database() as c:
        row=c.execute('SELECT * FROM access_jobs WHERE id=? AND employee_id=?',(job_id,employee_id)).fetchone()
        if row is None:
            return None
        if row['status']=='processing' and time.time()-row['created']>=5:
            c.execute('UPDATE access_jobs SET status=?,code=? WHERE id=? AND status=?',('done','AB-'+secrets.token_hex(6).upper(),job_id,'processing'))
            row=c.execute('SELECT * FROM access_jobs WHERE id=?',(job_id,)).fetchone()
        feedback_received=bool(c.execute('SELECT 1 FROM task_feedback WHERE employee_id=? AND job_id=?',(employee_id,job_id)).fetchone())
        return {'feedback_received':feedback_received,'id':row['id'],'tools':json.loads(row['tools']),'status':row['status'],'code':row['code'] if row['status']=='done' else None,'ready_after_seconds':max(0,5-(time.time()-row['created']))}

def latest(employee_id):
    with database() as c:
        row=c.execute('SELECT id FROM access_jobs WHERE employee_id=?',(employee_id,)).fetchone()
    return get(row['id'],employee_id) if row else None

