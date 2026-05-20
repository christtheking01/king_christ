import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('member', '0004_alter_member_ministry_alter_member_shepherd'),
        ('users', '0002_user_pos_pin'),
    ]
    operations = [
        # 1. First remove old field
        migrations.RemoveField(
            model_name='familymembership',
            name='user',
        ),
        # 2. Add new field
        migrations.AddField(
            model_name='familymembership',
            name='member',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='family_memberships', to='member.member'),
        ),
        # 3. Now safe to set unique_together
        migrations.AlterUniqueTogether(
            name='familymembership',
            unique_together={('member', 'family')},
        ),
    ]