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
