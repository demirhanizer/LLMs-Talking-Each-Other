# Generated by Django 5.1.1 on 2024-10-03 18:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="response",
            field=models.TextField(blank=True, null=True),
        ),
    ]