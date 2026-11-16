"""Однопользовательский прототип адаптации. Кадровые данные — демонстрационные."""
import calendar
import json
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from zoneinfo import ZoneInfo
from datetime import datetime
import storage

TOOLS = [
    {"id": "camunda", "name": "Camunda", "description": "Моделирование бизнес-процессов BPMN.", "url": "https://docs.camunda.io/downloads/"},
    {"id": "postgresql", "name": "PostgreSQL", "description": "Работа с данными и SQL. Нужен ли локальный сервер — уточни у наставника.", "url": "https://www.postgresql.org/download/windows/"},
    {"id": "powerpoint", "name": "PowerPoint", "description": "Презентации результатов и требований.", "url": "https://www.microsoft.com/en-us/microsoft-365/powerpoint"},
    {"id": "excel", "name": "Excel", "description": "Таблицы, анализ и описание данных.", "url": "https://www.microsoft.com/en-us/microsoft-365/excel"},
]
COUNTS = [7, 3, 2, 2, 2, 3]
VALID_TASKS = {f"{i}-{j}" for i, count in enumerate(COUNTS) for j in range(count)}


def today():
    # Фиксированная продуктовая зона, не часовой пояс машины проверяющего.
    try:
        return datetime.now(ZoneInfo("Europe/Moscow")).date()
    except Exception:
        from datetime import timezone
        return datetime.now(timezone(timedelta(hours=3))).date()


def months(start, n):
    m = start.month - 1 + n
    y, m = start.year + m // 12, m % 12 + 1
    return date(y, m, min(start.day, calendar.monthrange(y, m)[1]))


def read_state():
    with closing(sqlite3.connect(storage.database_path())) as c:
        c.execute("CREATE TABLE IF NOT EXISTS buddy_state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)")
        c.execute("INSERT OR IGNORE INTO buddy_state VALUES (1, ?)", (json.dumps({"start_date": None, "tasks": {}, "tools": {}, "tools_approved": False}),))
        c.commit()
        return json.loads(c.execute("SELECT payload FROM buddy_state WHERE id=1").fetchone()[0])


def update_state(change):
    read_state()
    with closing(sqlite3.connect(storage.database_path())) as c:
        c.execute("BEGIN IMMEDIATE")
        state = json.loads(c.execute("SELECT payload FROM buddy_state WHERE id=1").fetchone()[0])
        change(state)
        c.execute("UPDATE buddy_state SET payload=? WHERE id=1", (json.dumps(state, ensure_ascii=False),))
        c.commit()
    return snapshot(state)


def snapshot(state=None, current=None):
    state = read_state() if state is None else state
    current = current or today()
    result = dict(state, today=current.isoformat(), catalog=TOOLS, profile=state.get("employee_profile", {}).get("position", "Стажёр — бизнес-аналитик"), demo=True)
    if not state["start_date"]:
        return dict(result, current_stage=0, progress=0, day=None, deadlines=[], elapsed=False)
    start = date.fromisoformat(state["start_date"])
    boundaries = [start, start + timedelta(days=7), start + timedelta(days=14), months(start, 1), months(start, 2), months(start, 3), months(start, 6)]
    end = date.fromisoformat(state['end_date']) if state.get('end_date') else None
    enabled = [i for i in range(6) if end is None or i == 0 or boundaries[i] < end]
    if end:
        last = enabled[-1]
        boundaries[last+1] = end + timedelta(days=1)
    else:
        last = 5
    stage = max(0, min(last, sum(current >= d for d in boundaries[1:last+1])))
    result['enabled_stages'] = enabled
    # Каждый отрезок шкалы соответствует своему реальному периоду.
    ratio = max(0, min(1, (current - boundaries[stage]).days / max(1, (boundaries[stage+1]-boundaries[stage]).days)))
    return dict(result, current_stage=stage, progress=min(1, (stage + ratio)/5), day=max(0, (current-start).days+1), elapsed=current>=start, deadlines=[(d-timedelta(days=1)).isoformat() for d in boundaries[1:]])


def answer(text):
    q = text.casefold()
    state = read_state()
    if any(w in q for w in ("зарплат", "ндс", "ндфл", "выплат", "оклад")):
        return {"text": "У меня нет подключения к расчётным листкам и графику выплат Авито. Суммы и даты не буду придумывать: уточни их в кадровом сервисе или у HR. НДС и удержания из зарплаты — разные понятия; расчёт в этом прототипе не выполняется.", "source": "Ограничение прототипа: кадровый сервис не подключён"}
    if "отпуск" in q:
        available = months(date.fromisoformat(state["start_date"]), 3).isoformat() if state["start_date"] else "после указания даты старта"
        return {"text": f"Демонстрационное правило: обращение по оплачиваемому или неоплачиваемому отпуску доступно после 3 месяцев, с {available}. Это условие нашего сценария, а не подтверждённая политика Авито. Реальные условия и остаток уточни у HR. Заявка здесь не отправляется.", "source": "Демо-политика по условию сценария"}
    if "отгул" in q:
        return {"text": "Демонстрационный кадровый сервис: доступно 2 дня отгула (вымышленные данные). Реальный остаток неизвестен. Укажи желаемые даты и обратись к наставнику или HR; этот прототип не отправляет кадровые заявки.", "source": "Имитация кадрового сервиса, не данные сотрудника Авито"}
    if "больнич" in q:
        return {"text": "Уточни у HR порядок уведомления и оформления больничного. Кадровый сервис не подключён, поэтому я не вижу его статус. Медицинские документы и диагноз в чат присылать не нужно.", "source": "Ограничение прототипа"}
    for tool in TOOLS:
        if tool["id"] in q or (tool["id"] == "postgresql" and any(w in q for w in ("postgres", "постгре", "sql"))):
            return {"text": tool["name"] + ": " + tool["description"] + " Используй согласованную наставником версию. Ссылка открывает официальный сайт, а не устанавливает программу автоматически.", "source": tool["url"], "url": tool["url"]}
    if any(w in q for w in ("инструмент", "программ", "установ")):
        return {"text": "Для сценария бизнес-аналитика предложены Camunda, PostgreSQL, PowerPoint и Excel. Открой «Рабочие инструменты»: там есть описание, ссылки и шаги знакомства. До подтверждения наставником это предложенный список.", "source": "Демонстрационный список инструментов"}
    if any(w in q for w in ("команд", "наставник", "стажиров", "авито", "адаптац")):
        return {"text": "Помогу с планом адаптации, инструментами и заявками на доступ. Знакомство с командой можно подтвердить самостоятельно в задаче слева. Если нужен внутренний регламент Авито, укажи тему: без подключённого источника я не буду выдумывать ответ.", "source": "План прототипа и границы базы знаний"}
    return {"text": "Я помогаю с Авито и стажировкой в Авито. Личную жизнь и другие компании не обсуждаю. Можешь спросить про адаптацию, рабочие инструменты, доступ или кадровый процесс.", "source": "Область работы AI-buddy"}


