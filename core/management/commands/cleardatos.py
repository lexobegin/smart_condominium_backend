from django.core.management.base import BaseCommand
from core.models import *

class Command(BaseCommand):
    help = 'Borra datos de algunos modelos específicos'

    def handle(self, *args, **kwargs):
        ConceptoCobro.objects.all().delete()
        Factura.objects.all().delete()
        Pago.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Datos borrados de Modelo1 y Modelo2.'))
