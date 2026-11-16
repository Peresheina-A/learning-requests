"""Материалы к задачам. Встроенные памятки — учебные, не регламенты Авито."""
import sqlite3
from contextlib import closing
import storage
import onboarding

GUIDES = [
    ('0-1','Рабочие доступы','Составь список нужных систем. Укажи рабочую цель для каждого доступа. Сверь его с наставником, отправь заявку и сохрани номер. Статус «создана» не означает, что доступ выдан. Проверь вход после подтверждения сервиса.'),
    ('0-2','Знакомство с рабочими инструментами','Изучи назначение Camunda, PostgreSQL, PowerPoint и Excel. Согласуй список и версии с наставником. Для каждого отметь знакомство, установку или отсутствие необходимости установки. Выполни небольшой пример: схема процесса, SQL-запрос, слайд, таблица.'),
    ('0-3','Первая встреча с наставником','Подготовь вопросы: что считается результатом первой задачи; как задавать вопросы; когда проходят встречи; где фиксировать решения. После встречи запиши договорённости.'),
    ('0-4','Процессы команды','Попроси наставника приложить описание процессов команды. Найди участников процесса, вход, результат, ограничения и точки согласования. Кратко перескажи своё понимание наставнику.'),
    ('0-5','Первая задача аналитика','Уточни проблему, заказчика, ожидаемый результат и срок. Запиши критерии готовности и открытые вопросы. Не подменяй требования предположениями. Покажи план наставнику до выполнения.'),
    ('1-0','Цели и ожидания','Запиши 2–3 ожидаемых результата на ближайший период. Для каждого согласуй с наставником признак выполнения и срок. Пример: описать процесс и получить комментарии команды.'),
    ('1-1','Документы команды','Прочитай приложенные документы команды. Составь словарь терминов, список участников и вопросов. Если документа нет, запроси его у наставника — не считай пустую подборку изученной.'),
    ('1-2','Практика работы с требованиями','Учебный мини-курс: 1. Сформулируй проблему. 2. Опиши текущий процесс. 3. Собери ограничения. 4. Согласуй критерии приёмки. Практика: составь одностраничное описание первой задачи.'),
    ('2-0','Работа с данными','Учебная памятка: используй только разрешённые источники; не пересылай секреты и персональные данные в чат; запрашивай минимальный доступ. Актуальную политику компании должен приложить ответственный сотрудник.'),
    ('2-1','Итерационная работа и границы систем','Учебный мини-курс: разбей задачу на проверяемые части; уточни границы систем и их обмен данными; покажи промежуточный результат; учти обратную связь. Реальные правила команды смотри в её документах.'),
    ('3-0','Учебная практика','Уточни, нужна ли учебная практика, какие документы запрашивает вуз, кто их подписывает и в какие сроки. Приложенные компанией формы имеют приоритет над этой памяткой.'),
    ('3-1','Аналитические артефакты','Учебная практика: подготовь схему BPMN в Camunda, пример SQL-запроса в тестовой базе и краткое описание требований. Проверь результат вместе с наставником. Не используй реальные данные без разрешения.'),
    ('4-0','Паттерны анализа','Учебный мини-курс: сравни варианты решения, ограничения и риски; для выбранного варианта составь критерии проверки. Практика: объясни, почему выбранный вариант решает исходную проблему.'),
    ('4-1','Профессиональное сообщество','Попроси наставника приложить описание профессиональных сообществ и правила участия. Выбери подходящую встречу, подготовь вопрос и запиши полезный вывод.'),
    ('5-0','Подготовка к экватору','Собери результаты: исходная проблема, твой вклад, артефакты, обратная связь и дальнейшие шаги. Согласуй презентацию с наставником и проведи репетицию.'),
    ('5-1','Промежуточная обратная связь','Подготовь примеры того, что получилось и где нужна помощь. На встрече договорись о следующих шагах, сроках и поддержке. Зафиксируй договорённости.'),
    ('5-2','Завершение периода','Собери итоговые материалы, передай незавершённые вопросы и уточни порядок опроса или заключительной встречи. Используй даты и инструкции, приложенные координатором.')
]


def connect():
    c = sqlite3.connect(storage.database_path())
    c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS buddy_materials (id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, scope TEXT NOT NULL, title TEXT NOT NULL, mime TEXT NOT NULL, content BLOB NOT NULL, seeded INTEGER NOT NULL DEFAULT 0)')
    return c


def seed():
    with closing(connect()) as c:
        for task, title, text in GUIDES:
            if not c.execute('SELECT 1 FROM buddy_materials WHERE task_id=? AND seeded=1',(task,)).fetchone():
                content = f'{title}\n\n{text}\n\nДополнительно прочитай актуальные документы компании и команды, приложенные наставником.'
                c.execute('INSERT INTO buddy_materials(task_id,scope,title,mime,content,seeded) VALUES (?,?,?,?,?,1)',(task,'company',title,'text/plain; charset=utf-8',content.encode('utf-8')))
        c.execute('CREATE TABLE IF NOT EXISTS buddy_material_seeds (name TEXT PRIMARY KEY)')
        if not c.execute('SELECT 1 FROM buddy_material_seeds WHERE name=?',('team-documents-example-v1',)).fetchone():
            if not c.execute("SELECT 1 FROM buddy_materials WHERE task_id='1-1' AND scope='team'").fetchone():
                from pathlib import Path
                sample=Path(__file__).with_name('team-documents-example.txt').read_text(encoding='utf-8-sig')
                c.execute('INSERT INTO buddy_materials(task_id,scope,title,mime,content,seeded) VALUES (?,?,?,?,?,0)',('1-1','team','Как работает команда аналитики','text/plain; charset=utf-8',sample.encode('utf-8')))
            c.execute('INSERT INTO buddy_material_seeds(name) VALUES (?)',('team-documents-example-v1',))
        c.commit()


def listing(task_id=None):
    seed()
    with closing(connect()) as c:
        query='SELECT id,task_id,scope,title,mime,seeded FROM buddy_materials'
        rows=c.execute(query+(' WHERE task_id=?' if task_id else '')+' ORDER BY id',(task_id,) if task_id else ()).fetchall()
        return [dict(row) for row in rows]


def upload(task_id,scope,title,mime,content):
    with closing(connect()) as c:
        cur=c.execute('INSERT INTO buddy_materials(task_id,scope,title,mime,content) VALUES (?,?,?,?,?)',(task_id,scope,title,mime,content))
        c.commit()
        return cur.lastrowid


def get(material_id):
    seed()
    with closing(connect()) as c:
        row=c.execute('SELECT * FROM buddy_materials WHERE id=?',(material_id,)).fetchone()
        if not row:
            return None
        item=dict(row)
        if item['mime'].startswith('text/'):
            item['content']=item['content'].decode('utf-8-sig').replace('Учебная памятка прототипа. Не официальный регламент Авито.','').lstrip().encode('utf-8')
        return item


