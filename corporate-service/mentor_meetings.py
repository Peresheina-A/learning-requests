"""Заявка на встречу с наставником, подтверждение через пять секунд."""
import secrets
import time
from datetime import datetime,timedelta,timezone
from database import database

def initialize():
    with database() as c:
        c.execute('CREATE TABLE IF NOT EXISTS mentor_meetings (id INTEGER PRIMARY KEY,employee_id INTEGER UNIQUE,created REAL,status TEXT,meeting_at TEXT,meeting_url TEXT)')

def create(employee_id):
    initialize()
    with database() as c:
        c.execute('INSERT OR IGNORE INTO mentor_meetings(employee_id,created,status) VALUES (?,?,?)',(employee_id,time.time(),'waiting'))
    return get(employee_id)

def get(employee_id):
    initialize()
    with database() as c:
        row=c.execute('SELECT * FROM mentor_meetings WHERE employee_id=?',(employee_id,)).fetchone()
        if row is None:
            return None
        if row['status']=='waiting' and time.time()-row['created']>=5:
            meeting_at=(datetime.now(timezone(timedelta(hours=3)))+timedelta(days=1)).replace(hour=11,minute=0,second=0,microsecond=0).isoformat()
            link='https://meet.example.com/mentor/'+secrets.token_urlsafe(8)
            c.execute('UPDATE mentor_meetings SET status=?,meeting_at=?,meeting_url=? WHERE id=? AND status=?',('done',meeting_at,link,row['id'],'waiting'))
            row=c.execute('SELECT * FROM mentor_meetings WHERE employee_id=?',(employee_id,)).fetchone()
        return {'id':row['id'],'status':row['status'],'meeting_at':row['meeting_at'],'meeting_url':row['meeting_url']}
