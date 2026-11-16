"""Необязательная обратная связь о выполненной задаче."""
import time
from database import database

def initialize():
    with database() as c:
        c.execute('CREATE TABLE IF NOT EXISTS task_feedback (id INTEGER PRIMARY KEY,employee_id INTEGER,job_id INTEGER,satisfied INTEGER,comment TEXT,created REAL, UNIQUE(employee_id,job_id))')

def save(employee_id,job_id,satisfied,comment):
    with database() as c:
        c.execute('INSERT INTO task_feedback(employee_id,job_id,satisfied,comment,created) VALUES (?,?,?,?,?) ON CONFLICT(employee_id,job_id) DO UPDATE SET satisfied=excluded.satisfied,comment=excluded.comment',(employee_id,job_id,int(satisfied),comment,time.time()))
        return {'saved':True}
