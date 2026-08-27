from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Incident',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=300, verbose_name='Titre')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('gravite', models.CharField(choices=[('mineure', 'Mineure'), ('moderee', 'Modérée'), ('majeure', 'Majeure'), ('critique', 'Critique')], default='mineure', max_length=50, verbose_name='Gravité')),
                ('resolu', models.BooleanField(default=False, verbose_name='Résolu')),
                ('date_signalement', models.DateTimeField(auto_now_add=True, verbose_name='Date de signalement')),
                ('date_resolution', models.DateTimeField(blank=True, null=True, verbose_name='Date de résolution')),
                ('intervention', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incidents', to='core.intervention', verbose_name='Intervention')),
                ('signale_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='incidents_signales', to=settings.AUTH_USER_MODEL, verbose_name='Signalé par')),
            ],
            options={
                'verbose_name': 'Incident',
                'verbose_name_plural': 'Incidents',
                'ordering': ['-date_signalement'],
            },
        ),
    ]
