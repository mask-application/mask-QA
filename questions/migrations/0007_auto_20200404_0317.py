# Generated by Django 3.0.4 on 2020-04-04 03:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0006_authtoken_expired'),
    ]

    operations = [
        migrations.AlterField(
            model_name='faq',
            name='post_id',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
