# Generated migration for adding preferred_language field to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0031_helpsupport_reply'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='preferred_language',
            field=models.CharField(
                choices=[('en', 'English'), ('ar', 'Arabic')],
                default='en',
                help_text="User's preferred language for emails and notifications",
                max_length=5,
                verbose_name='Preferred Language'
            ),
        ),
    ]
