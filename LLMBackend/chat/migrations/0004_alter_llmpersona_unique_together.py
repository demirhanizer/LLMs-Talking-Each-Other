# Generated by Django 5.1.1 on 2024-12-14 21:50

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_alter_message_sender"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="llmpersona",
            unique_together={("user", "name")},
        ),
    ]