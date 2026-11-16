"""Учётная запись и профиль стажёра. Руководитель и куратор ещё не заведены."""
import hashlib
import hmac
import secrets
from database import database

def password_hash(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),200_000).hex()

def initialize():
    with database() as c:
        c.execute('CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY, full_name TEXT, login TEXT UNIQUE, password_hash TEXT, salt TEXT, start_date TEXT, end_date TEXT, position TEXT)')
        if not c.execute('SELECT 1 FROM employees WHERE login=?',('Anastasia',)).fetchone():
            salt=secrets.token_hex(16)
            c.execute('INSERT INTO employees VALUES (?,?,?,?,?,?,?,?)',(1,'Перешеина Анастасия Владиславовна','Anastasia',password_hash('1234',salt),salt,'2026-11-09','2026-12-09','Аналитик данных'))

def profile(employee_id):
    with database() as c:
        row=c.execute('SELECT id,full_name,login,start_date,end_date,position FROM employees WHERE id=?',(employee_id,)).fetchone()
        return dict(row) if row else None

def authenticate(login,password):
    with database() as c:
        row=c.execute('SELECT * FROM employees WHERE login=?',(login,)).fetchone()
    if row is None or not hmac.compare_digest(row['password_hash'],password_hash(password,row['salt'])):
        return None
    return profile(row['id'])

