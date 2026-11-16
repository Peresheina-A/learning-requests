from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

import storage
import llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.initialize_database()
    yield


app = FastAPI(
    title="Учебные заявки",
    description=(
        "Учебный сервис заявок на доступ к инструментам. "
        "Заявки сохраняются в локальной базе SQLite. "
        "Это имитация сервиса: реальный доступ к инструментам не выдаётся."
    ),
    lifespan=lifespan,
)


class RequestData(BaseModel):
    model_config = ConfigDict(
        title="Данные заявки", str_strip_whitespace=True
    )

    tool: str = Field(
        min_length=1,
        title="Инструмент",
        description="Название инструмента. Поле обязательно и не может быть пустым.",
        examples=["Учебная Jira"],
    )
    reason: str = Field(
        min_length=1,
        title="Причина запроса",
        description="Для чего нужен доступ. Поле обязательно и не может быть пустым.",
        examples=["Для выполнения первой учебной задачи"],
    )


class SavedRequest(RequestData):
    model_config = ConfigDict(title="Сохранённая заявка")

    id: int = Field(title="Номер заявки", description="Номер записи в учебной базе.")
    status: Literal["created"] = Field(
        title="Статус", description="created — заявка создана; доступ ещё не выдан."
    )


class SuggestionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=2000, title="Описание запроса")


@app.post(
    "/api/suggestions",
    response_model=llm.DraftFields,
    tags=["ИИ-помощник"],
    summary="Предложить заполнение формы",
    description="Локальная модель извлекает поля из текста. Заявка не создаётся. Проверьте предложенные данные перед отправкой.",
    responses={
        502: {"description": "Некорректный ответ модели"},
        503: {"description": "Ollama или модель недоступна"},
        504: {"description": "Время ожидания истекло"},
    },
)
def suggest_fields(data: SuggestionInput) -> llm.DraftFields:
    try:
        return llm.suggest_fields(data.text)
    except llm.LLMError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(Path(__file__).with_name("index.html"))


@app.get(
    "/health",
    tags=["Проверка сервиса"],
    summary="Проверить работу сервиса",
    description="Возвращает status: ok, если приложение отвечает на запросы.",
    response_description="Сервис работает",
)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/requests",
    response_model=SavedRequest,
    status_code=201,
    tags=["Заявки"],
    summary="Создать учебную заявку",
    description=(
        "Принимает название инструмента и причину запроса. "
        "Удаляет пробелы по краям и проверяет обязательные поля. "
        "Сохраняет заявку в SQLite и возвращает её номер и статус created."
    ),
    response_description="Заявка создана и сохранена",
    responses={422: {"description": "Ошибка проверки данных запроса"}},
)
def create_request(data: RequestData) -> dict:
    return storage.create_request(tool=data.tool, reason=data.reason)


@app.get(
    "/api/requests/{id}",
    response_model=SavedRequest,
    tags=["Заявки"],
    summary="Получить заявку по номеру",
    description="Возвращает ранее сохранённую учебную заявку из SQLite.",
    response_description="Сохранённая заявка",
    responses={404: {"description": "Заявка не найдена"}},
)
def get_request(id: int) -> dict:
    result = storage.get_request(id)
    if result is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return result

# Однопользовательская демонстрация: авторизация наставника и HR не имитируется как реальная.
import onboarding
from datetime import date

class StartDate(BaseModel):
    start_date: date

class TaskUpdate(BaseModel):
    status: Literal['todo', 'in_progress', 'waiting', 'done']

class ToolUpdate(BaseModel):
    familiar: bool
    installed: bool
    not_required: bool = False

@app.get('/api/onboarding')
def onboarding_state():
    return onboarding.snapshot()

@app.post('/api/onboarding/start')
def onboarding_start(data: StartDate):
    raise HTTPException(403, 'Дата начала стажировки берётся из профиля сотрудника')

@app.post('/api/onboarding/tasks/{task_id}')
def onboarding_task(task_id: str, data: TaskUpdate):
    if task_id not in onboarding.VALID_TASKS:
        raise HTTPException(404, 'Задача не найдена')
    if task_id == '1-1' and data.status in ('in_progress', 'done') and not any(d['scope'] == 'team' for d in materials.listing('1-1')):
        raise HTTPException(409, 'Наставник пока не приложил документы команды')
    if task_id == '0-3':
        raise HTTPException(403, 'Статус встречи обновляется по ответу наставника')
    if task_id == '1-0':
        raise HTTPException(403, 'Статус этой задачи обновляется по результату заявки')
    if task_id == '0-1' and data.status == 'done':
        raise HTTPException(422, 'Создание заявки не подтверждает выдачу доступа')
    if task_id == '0-2' and data.status == 'done':
        state = onboarding.read_state()
        if not state['tools_approved'] or not all(
            state['tools'].get(t['id'], {}).get('familiar') and (
                state['tools'].get(t['id'], {}).get('installed') or
                state['tools'].get(t['id'], {}).get('not_required')
            ) for t in onboarding.TOOLS
        ):
            raise HTTPException(422, 'Подтверди знакомство и доступность каждого согласованного инструмента')
    return onboarding.update_state(lambda s: s['tasks'].update({task_id: data.status}))

@app.post('/api/onboarding/tools/approve-demo')
def approve_demo_tools():
    return onboarding.update_state(lambda s: s.update(tools_approved=True))

@app.post('/api/onboarding/tools/{tool_id}')
def update_tool(tool_id: str, data: ToolUpdate):
    if tool_id not in {t['id'] for t in onboarding.TOOLS}:
        raise HTTPException(404, 'Инструмент не найден')
    if not onboarding.read_state()['tools_approved']:
        raise HTTPException(409, 'Список ещё не согласован в демонстрации')
    return onboarding.update_state(lambda s: s['tools'].update({tool_id: data.model_dump()}))

@app.post('/api/buddy/answer')
def buddy_answer(data: SuggestionInput):
    return onboarding.answer(data.text)


import materials
from fastapi import Request, Response

@app.get('/api/materials')
def list_materials(task_id: str | None = None):
    if task_id is not None and task_id not in onboarding.VALID_TASKS:
        raise HTTPException(404, 'Задача не найдена')
    return materials.listing(task_id)

@app.get('/api/materials/{material_id}')
def read_material(material_id: int):
    item=materials.get(material_id)
    if item is None:
        raise HTTPException(404, 'Материал не найден')
    return Response(content=item['content'],media_type=item['mime'],headers={'X-Content-Type-Options':'nosniff','Content-Security-Policy':"sandbox; default-src 'none'",'Cache-Control':'no-store'})

@app.post('/api/materials')
async def attach_material(request: Request):
    session_user(request)
    raise HTTPException(403, 'Прикрепление документов доступно после подключения аккаунта руководителя')

# Вход в buddy и вызовы отдельного корпоративного сервиса.
import secrets
import time
from threading import Lock
import corporate_gateway

_sessions = {}
_session_lock = Lock()
SESSION_SECONDS = 12 * 60 * 60

def session_user(request: Request):
    token = request.cookies.get('buddy_session', '')
    with _session_lock:
        session = _sessions.get(token)
        if session is None or session['expires'] < time.time():
            _sessions.pop(token, None)
            raise HTTPException(401, 'Войди в аккаунт')
        return session['employee_id']

@app.middleware('http')
async def protect_account(request: Request, call_next):
    if request.url.path.startswith('/api/') and request.url.path not in ('/api/login', '/api/session', '/api/logout'):
        try:
            session_user(request)
        except HTTPException as error:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': error.detail},status_code=error.status_code)
    return await call_next(request)

class LoginData(BaseModel):
    role: Literal['student', 'manager', 'curator']
    login: str = Field(min_length=1,max_length=100)
    password: str = Field(min_length=1,max_length=200)

def apply_profile(profile):
    def update(s):
        s['start_date'] = profile['start_date']
        s['end_date'] = profile['end_date']
        s['employee_profile'] = profile
        if not s.get('access_jobs'):
            s['tasks'].pop('0-1', None)
    return onboarding.update_state(update)

@app.post('/api/login')
def login_account(data: LoginData, response: Response):
    if data.role != 'student':
        raise HTTPException(403, 'Вход для руководителя и куратора пока не подключён. Выберите стажёра.')
    profile = corporate_gateway.call('/auth', {'login':data.login,'password':data.password})
    token = secrets.token_urlsafe(32)
    with _session_lock:
        _sessions[token] = {'employee_id':profile['id'],'expires':time.time()+SESSION_SECONDS}
    apply_profile(profile)
    response.set_cookie('buddy_session',token,httponly=True,samesite='strict',max_age=SESSION_SECONDS,path='/')
    return profile

@app.get('/api/session')
def current_session(request: Request):
    employee_id = session_user(request)
    profile = corporate_gateway.call('/employees/'+str(employee_id))
    apply_profile(profile)
    return profile

@app.post('/api/logout')
def logout_account(request: Request, response: Response):
    with _session_lock:
        _sessions.pop(request.cookies.get('buddy_session',''),None)
    response.delete_cookie('buddy_session',path='/')
    return {'ok':True}

def sync_access(job):
    if job is None:
        return None
    def update(s):
        s.setdefault('access_jobs',{})[str(job['id'])] = job
        # Задача доступов теперь закрывается самоподтверждением группы информации.
        if job['status']=='done':
            notices=s.setdefault('notifications',[])
            notice_id='access-'+str(job['id'])
            if not any(n['id']==notice_id for n in notices):
                notices.append({'id':notice_id,'text':'Рабочие доступы готовы. Код доступен в задаче.','task_id':'0-1','read':False,'created':time.time()})
    onboarding.update_state(update)
    return job

@app.post('/api/work-access')
def request_work_access(request: Request):
    employee_id = session_user(request)
    return sync_access(corporate_gateway.call(f'/employees/{employee_id}/access',{}))

@app.get('/api/work-access')
def current_work_access(request: Request):
    employee_id = session_user(request)
    return sync_access(corporate_gateway.call(f'/employees/{employee_id}/access'))

@app.get('/api/work-access/{job_id}')
def get_work_access(job_id: int, request: Request):
    employee_id = session_user(request)
    return sync_access(corporate_gateway.call(f'/employees/{employee_id}/access/{job_id}'))

class TaskFeedback(BaseModel):
    satisfied: bool
    comment: str = Field(default='',max_length=2000)

@app.post('/api/work-access/{job_id}/feedback')
def access_feedback(job_id:int,data:TaskFeedback,request:Request):
    employee_id = session_user(request)
    return corporate_gateway.call(f'/employees/{employee_id}/access/{job_id}/feedback',data.model_dump())

@app.get('/api/notifications')
def notifications():
    return onboarding.read_state().get('notifications',[])

@app.post('/api/notifications/read')
def mark_notifications_read():
    def update(s):
        for notice in s.get('notifications',[]):
            notice['read'] = True
    onboarding.update_state(update)
    return {'ok':True}




# Задача 1-0 управляется корпоративным сервисом, а не ручными статусами стажёра.
def sync_goals(job):
    if job is None:
        return None
    def update(s):
        s['tasks']['1-0']='done' if job['status']=='done' else 'waiting'
        if job['status']=='done':
            notices=s.setdefault('notifications',[])
            notice_id='goals-'+str(job['id'])
            if not any(n['id']==notice_id for n in notices):
                notices.append({'id':notice_id,'text':'Цели и ожидания готовы. Открой результат в задаче.','task_id':'1-0','read':False,'created':time.time()})
    onboarding.update_state(update)
    return job

@app.post('/api/goals-request')
def submit_goals(request:Request):
    employee_id=session_user(request)
    return sync_goals(corporate_gateway.call(f'/employees/{employee_id}/goals',{}))

@app.get('/api/goals-request')
def get_goals(request:Request):
    employee_id=session_user(request)
    return sync_goals(corporate_gateway.call(f'/employees/{employee_id}/goals'))

@app.post('/api/goals-request/feedback')
def submit_goals_feedback(data:TaskFeedback,request:Request):
    employee_id=session_user(request)
    return corporate_gateway.call(f'/employees/{employee_id}/goals/feedback',data.model_dump())


INFORMATION_TASKS={'0-6','0-1','0-0','0-4'}

@app.get('/api/group-info/documents/{document_id}')
def group_document(document_id:str):
    return corporate_gateway.call('/checklist/documents/'+document_id)

@app.get('/api/group-info/{task_id}')
def group_information(task_id:str):
    if task_id not in INFORMATION_TASKS:
        raise HTTPException(404,'Задача не относится к этой группе')
    return corporate_gateway.call('/checklist/information/'+task_id)

class InformationTaskStatus(BaseModel):
    status: Literal['done','in_progress'] = 'done'

@app.post('/api/group-info/{task_id}/confirm')
def confirm_information(task_id:str,request:Request,data:InformationTaskStatus):
    if task_id not in INFORMATION_TASKS:
        raise HTTPException(404,'Задача не относится к этой группе')
    employee_id=session_user(request)
    def update(s):
        s['tasks'][task_id]=data.status
        s.setdefault('confirmations',{})[task_id]={'employee_id':employee_id,'confirmed':data.status=='done','created':time.time()}
    return onboarding.update_state(update)



@app.get('/api/work-tools-content')
def read_work_tools_content():
    return corporate_gateway.call('/checklist/work-tools')

# «Готово» для этой задачи означает, что встреча назначена, а не проведена.
def sync_mentor_meeting(job):
    if job is None:
        return None
    def update(s):
        s['mentor_meeting']=job
        s['tasks']['0-3']='done' if job['status']=='done' else 'waiting'
        if job['status']=='done':
            notices=s.setdefault('notifications',[])
            nid='mentor-meeting-'+str(job['id'])
            if not any(n['id']==nid for n in notices):
                notices.append({'id':nid,'text':'Встреча с наставником назначена. Дата и ссылка — в задаче.','task_id':'0-3','read':False,'created':time.time()})
    onboarding.update_state(update)
    return job

@app.post('/api/mentor-meeting')
def submit_mentor_meeting(request:Request):
    uid=session_user(request)
    return sync_mentor_meeting(corporate_gateway.call(f'/employees/{uid}/mentor-meeting',{}))

@app.get('/api/mentor-meeting')
def current_mentor_meeting(request:Request):
    uid=session_user(request)
    return sync_mentor_meeting(corporate_gateway.call(f'/employees/{uid}/mentor-meeting'))



import ai_features

@app.post('/api/ai/assist')
def ai_assist(data:ai_features.AssistInput):
    try:
        return ai_features.assist(data,onboarding.snapshot())
    except llm.LLMError as error:
        raise HTTPException(error.status_code,str(error)) from error
