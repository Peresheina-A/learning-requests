"""Отдельный сценарий подготовки целей и ожиданий."""
import time
from database import database

def initialize():
    with database() as c:
        c.execute('CREATE TABLE IF NOT EXISTS goals_jobs (id INTEGER PRIMARY KEY,employee_id INTEGER UNIQUE,created REAL,status TEXT,result TEXT,feedback INTEGER,comment TEXT)')

def create(employee_id):
    initialize()
    with database() as c:
        c.execute('INSERT OR IGNORE INTO goals_jobs(employee_id,created,status) VALUES (?,?,?)',(employee_id,time.time(),'processing'))
    return get(employee_id)

def get(employee_id):
    initialize()
    with database() as c:
        row=c.execute('SELECT * FROM goals_jobs WHERE employee_id=?',(employee_id,)).fetchone()
        if row is None:
            return None
        if row['status']=='processing' and time.time()-row['created']>=5:
            result='Цели и ожидания на стажировку\n\n1. Изучить задачи команды и доступные источники данных.\nРезультат: краткое описание процесса и список вопросов.\n\n2. Подготовить первый аналитический результат.\nРезультат: анализ тестовых данных, выводы и описание ограничений.\n\n3. Обсуждать прогресс с наставником.\nРезультат: фиксировать решения и дальнейшие шаги после встреч.\n\nОжидания: задавать уточняющие вопросы, обозначать затруднения и показывать промежуточный результат.'
            c.execute('UPDATE goals_jobs SET status=?,result=? WHERE id=? AND status=?',('done',result,row['id'],'processing'))
            row=c.execute('SELECT * FROM goals_jobs WHERE employee_id=?',(employee_id,)).fetchone()
        return {'id':row['id'],'status':row['status'],'result':row['result'],'feedback_received':row['feedback'] is not None}

def save_feedback(employee_id,satisfied,comment):
    with database() as c:
        c.execute('UPDATE goals_jobs SET feedback=?,comment=? WHERE employee_id=?',(int(satisfied),comment,employee_id))
    return {'saved':True}
