"""Единственная точка HTTP-обращений buddy к корпоративному сервису."""
import json
import os
from urllib.request import Request, ProxyHandler, build_opener
from urllib.error import HTTPError, URLError
from fastapi import HTTPException

def call(path,data=None):
    base=os.environ.get('CORPORATE_SERVICE_URL','http://127.0.0.1:8001')
    request=Request(base.rstrip('/')+path,data=json.dumps(data,ensure_ascii=False).encode() if data is not None else None,headers={'Content-Type':'application/json','X-Service-Key':os.environ.get('CORPORATE_SERVICE_KEY','buddy-local-development')},method='POST' if data is not None else 'GET')
    try:
        with build_opener(ProxyHandler({})).open(request,timeout=8) as response:
            return json.load(response)
    except HTTPError as e:
        try:
            detail=json.load(e).get('detail','Ошибка корпоративного сервиса')
        except Exception:
            detail='Ошибка корпоративного сервиса'
        raise HTTPException(e.code,detail) from e
    except (URLError,TimeoutError,OSError) as e:
        raise HTTPException(503,'Корпоративный сервис недоступен. Запусти оба приложения через run_services.py.') from e
