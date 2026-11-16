import os
import tempfile
import unittest
from unittest.mock import patch
import materials

class MaterialTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env=patch.dict(os.environ,LEARNING_REQUESTS_DB=os.path.join(tmp.name,'test.db'))
        env.start()
        self.addCleanup(env.stop)

    def test_guides_and_team_example_seed_once(self):
        first=materials.listing()
        guides = [d for d in first if d['seeded']]
        self.assertEqual(len(guides), len(materials.GUIDES))
        self.assertEqual(first, materials.listing())
        self.assertTrue(any(d['task_id']=='1-1' and d['scope']=='team' for d in first))
        self.assertNotIn('0-0',{d['task_id'] for d in first})
        # Offline introduction and chats use corporate information, not local guides.
        self.assertEqual({d['task_id'] for d in guides},materials.onboarding.VALID_TASKS-{'0-0','0-6'})

    def test_team_upload_persists_and_stays_in_its_task(self):
        content='Документ команды <script>test</script>'.encode()
        mid=materials.upload('1-0','team','Цели команды','text/plain',content)
        self.assertEqual(materials.get(mid)['content'],content)
        self.assertTrue(any(d['id']==mid for d in materials.listing('1-0')))
        self.assertFalse(any(d['id']==mid for d in materials.listing('1-1')))
        self.assertIsNone(materials.get(99999))
