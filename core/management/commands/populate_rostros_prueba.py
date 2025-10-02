import json
from django.core.management.base import BaseCommand
from core.models import Usuario
from django.utils import timezone

class Command(BaseCommand):
    help = 'Poblar datos faciales de prueba para usuarios'

    def handle(self, *args, **kwargs):
        self.stdout.write("Poblando datos faciales de prueba...")
        
        # Obtener primeros 5 usuarios activos
        usuarios = Usuario.objects.filter(estado='activo')[:20]
        
        rostros_poblados = 0
        
        for usuario in usuarios:
            # Crear embedding simulado para DeepFace
            embedding_simulado = [float(i * 0.1) for i in range(128)]  # Embedding de 128 dimensiones
            
            usuario.datos_faciales = json.dumps({
                'embedding': embedding_simulado,
                'backend': 'deepface',
                'fecha_registro': timezone.now().isoformat(),
                'simulado': True,
                'embedding_length': len(embedding_simulado)
            })
            usuario.save()
            
            rostros_poblados += 1
            self.stdout.write(f"  - {usuario.nombre}: Embedding facial simulado ({len(embedding_simulado)} dimensiones)")
        
        self.stdout.write(f"Rostros poblados: {rostros_poblados}")
        self.stdout.write(self.style.SUCCESS("¡Datos faciales de prueba creados exitosamente!"))