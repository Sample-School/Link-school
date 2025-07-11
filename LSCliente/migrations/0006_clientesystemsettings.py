# Generated by Django 5.1.2 on 2025-05-29 12:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('LSCliente', '0005_merge_20250529_0924'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClienteSystemSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagem_home_1', models.ImageField(blank=True, null=True, upload_to='logos_clientes/')),
                ('system_primary_color', models.CharField(default='#3E3D3F', max_length=7)),
                ('system_second_color', models.CharField(default='#575758', max_length=7)),
                ('tempo_maximo_inatividade', models.IntegerField(default=30, help_text='Tempo máximo de inatividade em minutos')),
            ],
        ),
    ]
