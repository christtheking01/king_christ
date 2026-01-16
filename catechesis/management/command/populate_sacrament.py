from django.core.management.base import BaseCommand
from catechesis.models import Sacrament

class Command(BaseCommand):
    help = 'Populate the database with the seven sacraments'

    def handle(self, *args, **kwargs):
        sacraments_data = [
            ('baptism', False, 'The first sacrament of initiation', None),
            ('confirmation', True, 'Sacrament of Christian maturity', 12),
            ('eucharist', True, 'First Holy Communion', 7),
            ('reconciliation', True, 'Sacrament of Penance', 7),
            ('marriage', True, 'Holy Matrimony', 18),
            ('holy_orders', True, 'Ordination to ministry', 25),
            ('anointing_sick', True, 'Sacrament of healing', None),
        ]
        
        for name, requires_cert, desc, min_age in sacraments_data:
            Sacrament.objects.get_or_create(
                name=name,
                defaults={
                    'requires_birth_certificate': requires_cert,
                    'description': desc,
                    'min_age': min_age
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully populated sacraments'))