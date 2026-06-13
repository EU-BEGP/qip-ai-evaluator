from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='level',
            field=models.CharField(
                choices=[('INFO', 'Info'), ('ERROR', 'Error')],
                default='INFO',
                max_length=20,
            ),
        ),
    ]
