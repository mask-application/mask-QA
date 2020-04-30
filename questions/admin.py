from django.contrib import admin
from django import forms
from questions.models import *


class FAQModelForm(forms.ModelForm):
    answer = forms.CharField(widget=forms.Textarea)
    question = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = FAQ
        exclude = ()



# Register your models here.
class QuestionAdmin(admin.ModelAdmin):
    ordering = ['-created_at']
    list_display = ('title', 'text', 'related_faq', 'faq_checked')

    search_fields = (
        'title',
        'text',
        'answer_text'
    )


class FAQAdmin(admin.ModelAdmin):
    list_display = ('fid', 'question', 'post_id', 'answer')
    form = FAQModelForm


admin.site.register(Question, QuestionAdmin)
admin.site.register(FAQ, FAQAdmin)
