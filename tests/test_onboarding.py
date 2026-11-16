"""Проверки календаря и сохраняемого состояния адаптации."""
import os
import tempfile
import unittest
from datetime import date
from unittest.mock import patch
from fastapi import HTTPException
from types import SimpleNamespace
import app
import onboarding

class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.dict(os.environ, LEARNING_REQUESTS_DB=os.path.join(self.tmp.name, 'test.db'))
        p.start()
        self.addCleanup(p.stop)
        self.client = self

    def get(self, path):
        return SimpleNamespace(json=lambda:app.onboarding_state())

    def post(self, path, json=None):
        from pydantic import ValidationError
        try:
            if path.endswith('/start'):
                result=app.onboarding_start(app.StartDate(**json))
            elif '/tasks/' in path:
                result=app.onboarding_task(path.rsplit('/',1)[1],app.TaskUpdate(**json))
            elif path.endswith('/approve-demo'):
                result=app.approve_demo_tools()
            elif '/tools/' in path:
                result=app.update_tool(path.rsplit('/',1)[1],app.ToolUpdate(**json))
            else:
                result=app.buddy_answer(app.SuggestionInput(**json))
            return SimpleNamespace(status_code=200,json=lambda:result)
        except HTTPException as e:
            return SimpleNamespace(status_code=e.status_code)
        except ValidationError:
            return SimpleNamespace(status_code=422)

    def test_calendar_boundaries_and_month_end(self):
        state = dict(start_date='2026-01-31', tasks={}, tools={}, tools_approved=False)
        for day, stage in [('2026-01-30',0),('2026-02-06',0),('2026-02-07',1),('2026-02-14',2),('2026-02-28',3),('2026-03-31',4),('2026-04-30',5)]:
            s = onboarding.snapshot(state, date.fromisoformat(day))
            self.assertEqual(s['current_stage'], stage)
            self.assertTrue(0 <= s['progress'] <= 1)
        self.assertEqual(onboarding.snapshot(state,date(2026,2,7))['deadlines'][0], '2026-02-06')

    def test_state_survives_and_access_not_done(self):
        self.assertIsNone(self.client.get('/api/onboarding').json()['start_date'])
        self.assertEqual(self.client.post('/api/onboarding/start',json={'start_date':'invalid'}).status_code,422)
        self.client.post('/api/onboarding/start',json={'start_date':'2026-11-01'})
        self.client.post('/api/onboarding/tasks/0-0',json={'status':'done'})
        self.assertEqual(self.client.get('/api/onboarding').json()['tasks']['0-0'],'done')
        self.assertEqual(self.client.post('/api/onboarding/tasks/0-1',json={'status':'done'}).status_code,422)
        self.assertEqual(self.client.post('/api/onboarding/tasks/9-9',json={'status':'done'}).status_code,404)

    def test_tools_require_demo_approval(self):
        body={'familiar':True,'installed':False,'not_required':True}
        self.assertEqual(self.client.post('/api/onboarding/tools/excel',json=body).status_code,409)
        self.assertEqual(self.client.post('/api/onboarding/tasks/0-2',json={'status':'done'}).status_code,422)
        self.client.post('/api/onboarding/tools/approve-demo')
        self.assertEqual(self.client.post('/api/onboarding/tools/excel',json=body).status_code,200)
        self.assertTrue(self.client.get('/api/onboarding').json()['tools']['excel']['familiar'])

    def test_answers_have_sources_and_no_fake_payroll(self):
        for text in ['Когда отпуск?', 'Сколько отгулов?', 'Какая зарплата?', 'Что такое Camunda?', 'Расскажи про личную жизнь']:
            result=self.client.post('/api/buddy/answer',json={'text':text})
            self.assertEqual(result.status_code,200)
            self.assertTrue(result.json()['source'])
        self.assertIn('нет подключения',onboarding.answer('зарплата')['text'])
        self.assertIn('Демонстрационный',onboarding.answer('отгулы')['text'])


