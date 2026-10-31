from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.test import TestCase

from . import catalog

User = get_user_model()
PW = 'Sup3r-secret-pw'


def signed_in(name):
    client = APIClient(enforce_csrf_checks=False)
    res = client.post('/api/v1/auth/register/', {'email': f'{name}@example.com', 'username': name, 'password': PW}, format='json')
    assert res.status_code == 201, res.content
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + res.json()['token'])
    return client


def two_questions():
    key = catalog.answer_key()
    ids = [q for q in key if q.startswith('polity-001-')][:3]
    return ids, [key[i][0] for i in ids]


def wrong_letter(answer):
    return 'a' if answer != 'a' else 'b'


class MarkingTests(TestCase):
    def test_marks_come_from_the_server_answer_key(self):
        c = signed_in('marker')
        ids, ans = two_questions()
        body = {'name': 't', 'duration': 5, 'config': {'marking': {'correct': 1, 'negative': 0.33}}, 'answers': [
            {'qid': ids[0], 'chosen': ans[0]}, {'qid': ids[1], 'chosen': wrong_letter(ans[1])}, {'qid': ids[2], 'chosen': None},
            {'qid': 'nope-1', 'chosen': 'a'}, {'qid': ids[0], 'chosen': wrong_letter(ans[0])}]}
        attempt_id = c.post('/api/v1/attempts/', body, format='json').json()['id']
        got = c.get(f'/api/v1/attempts/{attempt_id}/').json()
        self.assertEqual((got['total'], got['correct'], got['wrong'], got['skipped']), (3, 1, 1, 1))  # unknown + repeated ids ignored
        self.assertEqual(got['score'], 0.67)
        self.assertEqual(got['maxscore'], 3.0)

    def test_users_only_see_their_own_attempts(self):
        a, b = signed_in('alice'), signed_in('bob')
        ids, ans = two_questions()
        aid = a.post('/api/v1/attempts/', {'answers': [{'qid': ids[0], 'chosen': ans[0]}]}, format='json').json()['id']
        self.assertEqual(b.get(f'/api/v1/attempts/{aid}/').status_code, 404)
        self.assertEqual(b.delete(f'/api/v1/attempts/{aid}/').status_code, 404)
        self.assertEqual(b.get('/api/v1/attempts/').json(), [])
        self.assertEqual(b.get('/api/v1/qstats/').json(), {})
        self.assertEqual(a.delete(f'/api/v1/attempts/{aid}/').status_code, 204)

    def test_rejects_a_paper_with_no_known_questions(self):
        c = signed_in('empty')
        self.assertEqual(c.post('/api/v1/attempts/', {'answers': [{'qid': 'zzz-1', 'chosen': 'a'}]}, format='json').status_code, 400)

    def test_login_is_required_for_data_and_crops(self):
        anon = APIClient()
        for url in ['/api/v1/data/manifest.json', '/api/v1/attempts/', '/api/v1/crop/?book=polity&segs=[]']:
            self.assertEqual(anon.get(url).status_code, 401, url)
        self.assertEqual(anon.get('/api/v1/stats/').status_code, 200)  # the landing page counts are public

    def test_data_paths_are_whitelisted(self):
        c = signed_in('reader')
        self.assertEqual(c.get('/api/v1/data/manifest.json').status_code, 200)
        self.assertEqual(c.get('/api/v1/data/answers.json').status_code, 404)  # the answer key is never downloadable
        self.assertEqual(c.get('/api/v1/data/q/../manifest.json').status_code, 404)


class AuthTests(TestCase):
    def test_login_by_username_or_email_and_cookie_session(self):
        signed_in('carol')
        anon = APIClient()
        self.assertEqual(anon.post('/api/v1/auth/login/', {'username': 'CAROL@example.com', 'password': PW}, format='json').status_code, 200)
        res = anon.post('/api/v1/auth/login/', {'username': 'carol', 'password': PW, 'transport': 'cookie'}, format='json')
        self.assertNotIn('token', res.json())
        self.assertTrue(res.cookies['ghatnachakra_session']['httponly'])
        self.assertEqual(anon.post('/api/v1/auth/login/', {'username': 'carol', 'password': 'bad'}, format='json').status_code, 401)

    def test_cookie_session_needs_csrf_for_writes(self):
        c = APIClient(enforce_csrf_checks=True)
        c.post('/api/v1/auth/register/', {'email': 'd@example.com', 'username': 'dave', 'password': PW, 'transport': 'cookie'}, format='json')
        res = c.post('/api/v1/attempts/', {'answers': []}, format='json')
        self.assertEqual((res.status_code, res.json()['error']['code']), (403, 'csrf_failed'))

    def test_duplicate_username_and_weak_password(self):
        signed_in('erin')
        c = APIClient()
        self.assertEqual(c.post('/api/v1/auth/register/', {'email': 'x@example.com', 'username': 'erin', 'password': PW}, format='json').status_code, 400)
        self.assertEqual(c.post('/api/v1/auth/register/', {'email': 'y@example.com', 'username': 'frank', 'password': '123'}, format='json').status_code, 400)
