from celery.task import PeriodicTask, Task
from django.conf import settings
from questions.models import Question, FAQ, AuthToken
import requests
from django.db import IntegrityError
import datetime
from questions.predictor import QuestionPredictor
import logging

logger = logging.getLogger(__name__)


class RequestHandler():
    __instance = None

    @staticmethod
    def getInstance():
        if RequestHandler.__instance is None:
            RequestHandler()
        return RequestHandler.__instance

    def __init__(self):
        if RequestHandler.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            RequestHandler.__instance = self
            self.expiration_time = None
            self.secret_key = None
            self.username = settings.MASK_ADMIN_USER
            self.password = settings.MASK_ADMIN_PASS
            logger.info(self.username)
            logger.info(self.password)
            self.auth_url = settings.MASK_ADMIN_URL + "admin/authenticate"

    def authenticate(self):
        logger.info("start authentication")
        data = {
            "username": self.username,
            "password": self.password
        }
        headers = self.get_anonymous_headers()
        res = requests.post(self.auth_url, json=data, headers=headers)
        logger.info("authenticate status code is: " + str(res.status_code))
        res = res.json()
        logger.info(res)
        return res['secret_key'], datetime.datetime.now() + datetime.timedelta(seconds=res['ttl'])

    def get_anonymous_headers(self):
        header = {
            "Content-Type": 'application/json'
        }
        return header

    def get_secret_key(self):
        if AuthToken.objects.all().count() == 0:
            token = AuthToken.objects.create()
        else:
            token = AuthToken.objects.first()
        if token.expired or token.secret_key is None or \
           datetime.datetime.now() + datetime.timedelta(minutes=2) > token.expiration_time:
            token.secret_key, token.expiration_time = self.authenticate()
            token.expired = False
            token.save()
        return token.secret_key

    def get_authorized_headers(self):
        header = self.get_anonymous_headers()
        header["Secret-Key"] = self.get_secret_key()
        return header


class FetchNewQuestionsTask(PeriodicTask):
    name = "fetch_new_questions_task"
    run_every = datetime.timedelta(minutes=5)
    ignore_result = True

    def run(self, **kwargs):
        logger.info("start adding questions")
        params = {
            'page': 0,
            'per_page': 50
        }
        question_list_url = settings.MASK_ADMIN_URL + "question"  # /?" + urllib.parse.urlencode(params)
        new_question_exists = True
        num_question_added = 0
        added_question_ids = []
        while new_question_exists:
            params['page'] += 1
            logger.info("fetch page: " + str(params["page"]))
            new_question_exists = False
            headers = RequestHandler.getInstance().get_authorized_headers()
            res = requests.get(question_list_url, params=params, headers=headers)
            logger.info(res.status_code)
            if res.status_code == 401:
                token = AuthToken.objects.first()
                token.expired = True
                token.save()
                params["page"] -= 1
                new_question_exists = True
                continue
            questions = res.json()["list"]
            for i, q in enumerate(questions):
                try:
                    Question.objects.create(
                        qid=q["id"],
                        title=q["title"],
                        text=q["text"],
                        created_at=q["create_time"],
                    )
                    num_question_added += 1
                    new_question_exists = True
                    added_question_ids.append(q["id"])
                except IntegrityError:
                    pass
        logger.info(str(num_question_added) + " questions added.")
        AnswerQuestionsTask().delay(added_question_ids)
        logger.info("end adding questions.")


class AnswerQuestionsTask(Task):
    name = "answer_questions_task"
    ignore_result = True

    def run(self, question_ids):
        questions = Question.objects.filter(qid__in=question_ids)
        faq_ids = QuestionPredictor().predict_related_faq_ids(list(questions))
        FAQs = {}
        for i, q in enumerate(questions):
            if faq_ids[i] in FAQs:
                faq = FAQs[faq_ids[i]]
            else:
                faq = FAQ.objects.get(fid=faq_ids[i])
                FAQs[faq_ids[i]] = faq
            q.related_faq = faq
            q.answer_text = faq.answer
            q.answer_related_post_id = faq.post_id
            q.save()
            PostAnswerTask().delay(q.qid)


class PostAnswerTask(Task):
    nam = "post_answer_task"
    ignore_result = True

    def run(self, question_id):
        question = Question.objects.get(qid=question_id)
        answer_url = settings.MASK_ADMIN_URL + "question/" + question_id + "/answer"
        params = {
            "answer": question.answer_text
        }
        if question.answer_related_post_id is not None:
            params["post"] = question.answer_related_post_id

        try:
            headers = RequestHandler.getInstance().get_authorized_headers()
        except Exception:
            PostAnswerTask().delay(question_id)
            return

        res = requests.post(answer_url, json=params, headers=headers)
        logger.info("result_status_code is: " + str(res.status_code))
        if res.status_code == 200:
            question.answer_time = datetime.datetime.now()
            question.save()
            SetSeenTask().delay(question_id)
            logger.info("Question with id " + question_id + " answered successfully.")
        elif res.status_code == 401:
            token = AuthToken.objects.first()
            token.expired = True
            token.save()
            PostAnswerTask().delay(question_id)
        else:
            logger.info("Answering question with id " + question_id + " faild with status_code=." + str(res.status_code))


class SetSeenTask(Task):
    nam = "set_seen_task"
    ignore_result = True

    def run(self, question_id):
        seen_url = settings.MASK_ADMIN_URL + "question/" + question_id + "/seen"
        try:
            headers = RequestHandler.getInstance().get_authorized_headers()
        except Exception:
            SetSeenTask().delay(question_id)
            return

        res = requests.post(seen_url, headers=headers)
        logger.info("result_status_code is: " + str(res.status_code))
        if res.status_code == 200:
            logger.info("Question with id " + question_id + " set seen successfully.")
        elif res.status_code == 401:
            token = AuthToken.objects.first()
            token.expired = True
            token.save()
            SetSeenTask().delay(question_id)
        else:
            logger.info("Set seen for question with id " + question_id + " faild with status_code=." + str(res.status_code))
