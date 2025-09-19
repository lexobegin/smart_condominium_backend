import random
from django.core.management.base import BaseCommand
from faker import Faker
from core.models import *
from django.utils import timezone
from datetime import timedelta

fake = Faker('es_ES')

class Command(BaseCommand):
    help = 'Pobla la base de datos con áreas comunes, reservas, categorías de mantenimiento, solicitudes y tareas'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando población de áreas comunes y mantenimiento...")

        self.crear_areas_comunes()
        self.crear_categorias_mantenimiento()
        self.crear_reservas()
        self.crear_solicitudes_mantenimiento()
        self.crear_tareas_mantenimiento()
        self.crear_mantenimiento_preventivo()

        self.stdout.write(self.style.SUCCESS("¡Datos de áreas comunes y mantenimiento poblados exitosamente!"))

    def crear_areas_comunes(self):
        self.areas_comunes = []
        
        tipos_areas = [
            'Piscina', 'Salón de Eventos', 'Gimnasio', 'Cancha de Tenis',
            'Área de BBQ', 'Jardín', 'Terraza', 'Sala de Juegos',
            'Estacionamiento Visitantes', 'Área Infantil'
        ]
        
        condominios = Condominio.objects.all()
        
        for condominio in condominios:
            for nombre in tipos_areas:
                area = AreaComun.objects.create(
                    nombre=f"{nombre} - {condominio.nombre}",
                    descripcion=fake.paragraph(nb_sentences=2),
                    capacidad=random.randint(5, 50),
                    horario_apertura=timezone.datetime.strptime('08:00', '%H:%M').time(),
                    horario_cierre=timezone.datetime.strptime('22:00', '%H:%M').time(),
                    precio_por_hora=round(random.uniform(10.0, 100.0), 2),
                    reglas_uso=fake.paragraph(nb_sentences=3),
                    requiere_aprobacion=random.choice([True, False]),
                    condominio=condominio
                )
                self.areas_comunes.append(area)
        
        self.stdout.write(f"Áreas comunes creadas: {len(self.areas_comunes)}")

    def crear_categorias_mantenimiento(self):
        self.categorias_mantenimiento = []
        
        categorias = [
            'Plomería', 'Electricidad', 'Pintura', 'Jardinería',
            'Limpieza', 'Carpintería', 'Herrería', 'Albañilería',
            'Aire Acondicionado', 'Seguridad'
        ]
        
        condominios = Condominio.objects.all()
        
        for condominio in condominios:
            for nombre in categorias:
                categoria = CategoriaMantenimiento.objects.create(
                    nombre=nombre,
                    descripcion=fake.sentence(),
                    condominio=condominio
                )
                self.categorias_mantenimiento.append(categoria)
        
        self.stdout.write(f"Categorías de mantenimiento creadas: {len(self.categorias_mantenimiento)}")

    def crear_reservas(self):
        estados = ['pendiente', 'confirmada', 'cancelada', 'completada']
        usuarios = Usuario.objects.filter(tipo__in=['residente', 'propietario'])
        
        reservas_creadas = 0
        
        for area in self.areas_comunes:
            # Crear 3-5 reservas por área
            for _ in range(random.randint(3, 5)):
                usuario = random.choice(usuarios)
                fecha_reserva = fake.date_between(start_date='-30d', end_date='+30d')
                                
                # Generar horas dentro del horario del área
                hora_inicio = timezone.datetime.strptime('09:00', '%H:%M').time()
                # Añadir horas aleatorias
                hora_inicio_hours = (hora_inicio.hour + random.randint(0, 10)) % 24
                hora_inicio = timezone.datetime.strptime(f'{hora_inicio_hours:02d}:00', '%H:%M').time()

                duracion = random.randint(1, 4)  # 1-4 horas de duración
                hora_fin_hours = (hora_inicio.hour + duracion) % 24
                hora_fin = timezone.datetime.strptime(f'{hora_fin_hours:02d}:00', '%H:%M').time()
                
                # Calcular monto total
                monto_total = area.precio_por_hora * duracion
                
                reserva = Reserva.objects.create(
                    area_comun=area,
                    usuario=usuario,
                    fecha_reserva=fecha_reserva,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    estado=random.choice(estados),
                    monto_total=round(monto_total, 2),
                    motivo=fake.sentence(),
                    numero_invitados=random.randint(1, area.capacidad)
                )
                reservas_creadas += 1
        
        self.stdout.write(f"Reservas creadas: {reservas_creadas}")

    def crear_solicitudes_mantenimiento(self):
        prioridades = ['baja', 'media', 'alta', 'urgente']
        estados = ['pendiente', 'asignado', 'en_proceso', 'completado', 'cancelado']
        creador_tipos = ['residente', 'administracion', 'sistema']
        
        usuarios = Usuario.objects.all()
        unidades = UnidadHabitacional.objects.all()
        
        solicitudes_creadas = 0
        
        for _ in range(20):  # Crear 20 solicitudes
            categoria = random.choice(self.categorias_mantenimiento)
            usuario = random.choice(usuarios)
            
            # Decidir si es para unidad habitacional o área común
            if random.choice([True, False]):
                unidad_habitacional = random.choice(unidades)
                area_comun = None
            else:
                unidad_habitacional = None
                area_comun = random.choice(self.areas_comunes)
            
            solicitud = SolicitudMantenimiento.objects.create(
                unidad_habitacional=unidad_habitacional,
                area_comun=area_comun,
                categoria_mantenimiento=categoria,
                usuario_reporta=usuario,
                titulo=fake.sentence(nb_words=4),
                descripcion=fake.paragraph(nb_sentences=3),
                prioridad=random.choice(prioridades),
                estado=random.choice(estados),
                fecha_limite=fake.date_between(start_date='+1d', end_date='+30d'),
                creador_tipo=random.choice(creador_tipos)
            )
            
            # Si está completada, asignar fecha de completado
            if solicitud.estado == 'completado':
                
                solicitud.fecha_completado = timezone.make_aware(
                    fake.date_time_between(
                        start_date=solicitud.fecha_reporte, 
                        end_date=solicitud.fecha_limite
                    )
                )
                solicitud.save()
            
            solicitudes_creadas += 1
        
        self.stdout.write(f"Solicitudes de mantenimiento creadas: {solicitudes_creadas}")

    def crear_tareas_mantenimiento(self):
        estados = ['pendiente', 'en_proceso', 'completado', 'cancelado']
        solicitudes = SolicitudMantenimiento.objects.filter(estado__in=['asignado', 'en_proceso', 'completado'])
        tecnicos = Usuario.objects.filter(tipo='mantenimiento')
        
        tareas_creadas = 0
        
        for solicitud in solicitudes:
            # Crear 1-3 tareas por solicitud
            for _ in range(random.randint(1, 3)):
                tecnico = random.choice(tecnicos) if tecnicos.exists() else None
                
                tarea = TareaMantenimiento.objects.create(
                    solicitud_mantenimiento=solicitud,
                    usuario_asignado=tecnico,
                    descripcion=fake.paragraph(nb_sentences=2),
                    estado=random.choice(estados),
                    fecha_limite=fake.date_between(start_date='+1d', end_date='+15d'),
                    costo_estimado=round(random.uniform(50.0, 500.0), 2)
                )
                
                # Si está completada, asignar fecha de completado y costo real
                if tarea.estado == 'completado':
                    
                    tarea.fecha_completado = timezone.make_aware(
                        fake.date_time_between(
                            start_date=tarea.fecha_asignacion, 
                            end_date=tarea.fecha_limite
                        )
                    )
                    # Costo real puede variar ±20% del estimado
                    variacion = random.uniform(0.8, 1.2)
                    tarea.costo_real = round(tarea.costo_estimado * variacion, 2)
                    tarea.save()
                
                tareas_creadas += 1
        
        self.stdout.write(f"Tareas de mantenimiento creadas: {tareas_creadas}")

    def crear_mantenimiento_preventivo(self):
        tecnicos = Usuario.objects.filter(tipo='mantenimiento')
        
        mantenimientos_creados = 0
        
        for categoria in self.categorias_mantenimiento:
            # Crear mantenimiento preventivo para algunas categorías
            if random.choice([True, False, False]):  # 33% de probabilidad
                area_comun = random.choice(self.areas_comunes) if random.choice([True, False]) else None
                tecnico = random.choice(tecnicos) if tecnicos.exists() else None
                
                periodicidad = random.choice([7, 15, 30, 90, 180, 365])  # días
                
                mantenimiento = MantenimientoPreventivo.objects.create(
                    categoria_mantenimiento=categoria,
                    area_comun=area_comun,
                    descripcion=fake.paragraph(nb_sentences=2),
                    periodicidad_dias=periodicidad,
                    ultima_ejecucion=fake.date_between(start_date='-60d', end_date='-1d'),
                    responsable=tecnico
                )
                
                # Calcular próxima ejecución
                if mantenimiento.ultima_ejecucion:
                    mantenimiento.proxima_ejecucion = (
                        mantenimiento.ultima_ejecucion + 
                        timedelta(days=mantenimiento.periodicidad_dias)
                    )
                    mantenimiento.save()
                
                mantenimientos_creados += 1
        
        self.stdout.write(f"Mantenimientos preventivos creados: {mantenimientos_creados}")
