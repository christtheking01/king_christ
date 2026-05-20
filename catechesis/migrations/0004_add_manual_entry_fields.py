# Generated manually to add manual entry fields to CatechesisInstructor

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catechesis', '0003_add_user_to_instructor'),
    ]

    operations = [
        migrations.AddField(
            model_name='catechesisinstructor',
            name='entry_type',
            field=models.CharField(choices=[('user', 'System User'), ('manual', 'Manual Entry')], default='user', max_length=10),
        ),
        migrations.AddField(
            model_name='catechesisinstructor',
            name='first_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='catechesisinstructor',
            name='last_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='catechesisinstructor',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='catechesisinstructor',
            name='phone',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
