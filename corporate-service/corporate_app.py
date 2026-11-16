"""Отдельный корпоративный HTTP-сервис. Только внутренние вызовы backend buddy."""
import hmac
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel, Field
import profiles
import access
import feedback

@asynccontextmanager
async def lifespan(app):
    profiles.initialize()
    access.initialize()
    feedback.initialize()
    yield

def internal_key(x_service_key: str = Header(default='')):
    expected=os.environ.get('CORPORATE_SERVICE_KEY','buddy-local-development')
    if not hmac.compare_digest(x_service_key,expected):
        raise HTTPException(403,'Доступ к сервису запрещён')

app=FastAPI(title='Корпоративный сервис',lifespan=lifespan,dependencies=[Depends(internal_key)])
class Credentials(BaseModel):
    login: str = Field(min_length=1,max_length=100)
    password: str = Field(min_length=1,max_length=200)

@app.post('/auth')
def authenticate(data:Credentials):
    user=profiles.authenticate(data.login,data.password)
    if user is None:
        raise HTTPException(401,'Неверный логин или пароль')
    return user

@app.get('/employees/{employee_id}')
def employee(employee_id:int):
    user=profiles.profile(employee_id)
    if user is None:
        raise HTTPException(404,'Сотрудник не найден')
    return user

@app.post('/employees/{employee_id}/access')
def create_access(employee_id:int):
    employee(employee_id)
    return access.create(employee_id)

@app.get('/employees/{employee_id}/access')
def latest_access(employee_id:int):
    return access.latest(employee_id)

@app.get('/employees/{employee_id}/access/{job_id}')
def read_access(employee_id:int,job_id:int):
    job=access.get(job_id,employee_id)
    if job is None:
        raise HTTPException(404,'Заявка не найдена')
    return job

class Feedback(BaseModel):
    satisfied: bool
    comment: str = Field(default='',max_length=2000)

@app.post('/employees/{employee_id}/access/{job_id}/feedback')
def add_feedback(employee_id:int,job_id:int,data:Feedback):
    job=read_access(employee_id,job_id)
    if job['status']!='done':
        raise HTTPException(409,'Задача ещё в обработке')
    return feedback.save(employee_id,job_id,data.satisfied,data.comment)

import goals

@app.post('/employees/{employee_id}/goals')
def create_goals(employee_id:int):
    employee(employee_id)
    return goals.create(employee_id)

@app.get('/employees/{employee_id}/goals')
def read_goals(employee_id:int):
    return goals.get(employee_id)

@app.post('/employees/{employee_id}/goals/feedback')
def goals_feedback(employee_id:int,data:Feedback):
    job=goals.get(employee_id)
    if not job or job['status']!='done':
        raise HTTPException(409,'Заявка ещё не выполнена')
    return goals.save_feedback(employee_id,data.satisfied,data.comment)

import information_group

@app.get('/checklist/information/{task_id}')
def information_task(task_id:str):
    task=information_group.task(task_id)
    if task is None:
        raise HTTPException(404,'Задача не найдена')
    return task

@app.get('/checklist/documents/{document_id}')
def information_document(document_id:str):
    doc=information_group.document(document_id)
    if doc is None:
        raise HTTPException(404,'Документ не найден')
    return doc

@app.get('/checklist/work-tools')
def work_tools_content():
    return information_group.work_tools()

import mentor_meetings

@app.post('/employees/{employee_id}/mentor-meeting')
def create_mentor_meeting(employee_id:int):
    employee(employee_id)
    return mentor_meetings.create(employee_id)

@app.get('/employees/{employee_id}/mentor-meeting')
def get_mentor_meeting(employee_id:int):
    employee(employee_id)
    return mentor_meetings.get(employee_id)
