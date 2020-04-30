from django.db import models

# Create your models here.


class Question(models.Model):

    qid = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=1000, blank=True)
    text = models.CharField(max_length=3000, blank=True)
    created_at = models.DateTimeField()

    fetched_at = models.DateTimeField(auto_now_add=True)

    related_faq = models.ForeignKey('FAQ', null=True, on_delete=models.SET_NULL, related_name='questions')
    faq_checked = models.BooleanField(default=False)

    answer_text = models.CharField(max_length=3000, null=True)
    answer_related_post_id = models.CharField(max_length=100, null=True)
    answer_time = models.DateTimeField(null=True)
    was_helpfull = models.IntegerField(choices=(
        (0, 'Not Answered'),
        (1, 'Helpfull'),
        (2, 'Not Helpfull')
    ), default=0)


class FAQ(models.Model):

    fid = models.IntegerField(unique=True)

    post_id = models.CharField(max_length=100, null=True)

    question = models.CharField(max_length=3000)
    answer = models.CharField(max_length=3000)

    def __str__(self):
        return self.question


class AuthToken(models.Model):

    secret_key = models.CharField(max_length=100, null=True)
    expiration_time = models.DateTimeField(null=True)
    expired = models.BooleanField(default=False)
