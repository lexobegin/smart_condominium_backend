import random
from django.core.management.base import BaseCommand
from faker import Faker
from core.models import *
from django.utils import timezone
from datetime import timedelta, datetime

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
        self.stdout.write("Creando áreas comunes...")
        
        self.areas_comunes = []
        tipos_areas = [
            {'nombre': 'Piscina', 'capacidad': (20, 50), 'precio': (30, 80)},
            {'nombre': 'Salón de Eventos', 'capacidad': (30, 100), 'precio': (50, 150)},
            {'nombre': 'Gimnasio', 'capacidad': (10, 25), 'precio': (20, 50)},
            {'nombre': 'Cancha de Tenis', 'capacidad': (4, 8), 'precio': (40, 80)},
            {'nombre': 'Área de BBQ', 'capacidad': (15, 30), 'precio': (25, 60)},
            {'nombre': 'Jardín Principal', 'capacidad': (25, 60), 'precio': (15, 40)},
            {'nombre': 'Terraza Mirador', 'capacidad': (10, 20), 'precio': (20, 45)},
            {'nombre': 'Sala de Juegos', 'capacidad': (8, 15), 'precio': (15, 35)},
            {'nombre': 'Estacionamiento Visitantes', 'capacidad': (5, 20), 'precio': (10, 25)},
            {'nombre': 'Área Infantil', 'capacidad': (10, 25), 'precio': (0, 0)},  # Gratuita
            {'nombre': 'Salón de Reuniones', 'capacidad': (12, 30), 'precio': (30, 70)},
            {'nombre': 'Sala de Cine', 'capacidad': (15, 35), 'precio': (25, 55)}
        ]
        
        condominios = Condominio.objects.all()
        
        for condominio in condominios:
            for tipo_area in tipos_areas:
                capacidad_min, capacidad_max = tipo_area['capacidad']
                precio_min, precio_max = tipo_area['precio']
                
                area = AreaComun.objects.create(
                    nombre=f"{tipo_area['nombre']} - {condominio.nombre.split()[-1]}",  # Usar última palabra del nombre
                    descripcion=fake.paragraph(nb_sentences=2),
                    capacidad=random.randint(capacidad_min, capacidad_max),
                    horario_apertura=timezone.datetime.strptime('07:00', '%H:%M').time(),
                    horario_cierre=timezone.datetime.strptime('22:00', '%H:%M').time(),
                    precio_por_hora=round(random.uniform(precio_min, precio_max), 2),
                    reglas_uso=fake.paragraph(nb_sentences=3),
                    requiere_aprobacion=random.choice([True, False]),
                    condominio=condominio
                )
                self.areas_comunes.append(area)
        
        self.stdout.write(f"Áreas comunes creadas: {len(self.areas_comunes)}")

    def crear_categorias_mantenimiento(self):
        self.stdout.write("Creando categorías de mantenimiento...")
        
        self.categorias_mantenimiento = []
        categorias = [
            'Plomería y Tuberías',
            'Sistema Eléctrico',
            'Pintura y Acabados',
            'Jardinería y Paisajismo',
            'Limpieza General',
            'Carpintería y Muebles',
            'Herrería y Estructuras',
            'Albañilería y Construcción',
            'Aire Acondicionado y Ventilación',
            'Sistema de Seguridad',
            'Ascensores y Elevadores',
            'Piscina y Áreas Húmedas'
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
        self.stdout.write("Creando reservas de áreas comunes...")
        
        estados = ['pendiente', 'confirmada', 'cancelada', 'completada']
        # Obtener residentes activos (con relación activa a unidades)
        residentes_activos = Usuario.objects.filter(
            usuariounidad__tipo_relacion='residente',
            usuariounidad__fecha_fin__isnull=True
        ).distinct()
        
        reservas_creadas = 0
        hoy = datetime.now().date()
        
        for area in self.areas_comunes:
            # Crear 5-8 reservas por área (pasadas y futuras)
            for _ in range(random.randint(5, 8)):
                if not residentes_activos.exists():
                    continue
                    
                usuario = random.choice(residentes_activos)
                
                # 60% reservas futuras, 40% pasadas
                if random.random() < 0.6:
                    fecha_reserva = fake.date_between(start_date='+1d', end_date='+60d')
                else:
                    fecha_reserva = fake.date_between(start_date='-60d', end_date='-1d')
                
                # Generar horas dentro del horario del área (8 AM - 10 PM)
                hora_inicio_hour = random.randint(8, 21)
                hora_inicio = timezone.datetime.strptime(f'{hora_inicio_hour:02d}:00', '%H:%M').time()
                
                duracion = random.randint(1, 4)  # 1-4 horas de duración
                hora_fin_hour = (hora_inicio_hour + duracion) % 24
                hora_fin = timezone.datetime.strptime(f'{hora_fin_hour:02d}:00', '%H:%M').time()
                
                # Determinar estado basado en fecha
                if fecha_reserva < hoy:
                    estado = random.choices(
                        ['completada', 'cancelada'], 
                        weights=[0.8, 0.2]
                    )[0]
                else:
                    estado = random.choices(
                        ['confirmada', 'pendiente', 'cancelada'], 
                        weights=[0.6, 0.3, 0.1]
                    )[0]
                
                # Calcular monto total (áreas gratuitas tienen precio 0)
                monto_total = area.precio_por_hora * duracion
                
                reserva = Reserva.objects.create(
                    area_comun=area,
                    usuario=usuario,
                    fecha_reserva=fecha_reserva,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    estado=estado,
                    monto_total=round(monto_total, 2),
                    motivo=fake.sentence(),
                    numero_invitados=random.randint(1, min(area.capacidad, 20))
                )
                reservas_creadas += 1
        
        self.stdout.write(f"Reservas creadas: {reservas_creadas}")

    def crear_solicitudes_mantenimiento(self):
        self.stdout.write("Creando solicitudes de mantenimiento...")
        
        prioridades = ['baja', 'media', 'alta', 'urgente']
        estados = ['pendiente', 'asignado', 'en_proceso', 'completado', 'cancelado']
        creador_tipos = ['residente', 'administracion', 'sistema']
        
        # Obtener usuarios que pueden reportar (residentes, propietarios, administradores)
        usuarios_reporta = Usuario.objects.filter(
            tipo__in=['residente', 'propietario', 'administrador']
        )
        
        # Obtener unidades ocupadas
        unidades_ocupadas = UnidadHabitacional.objects.filter(estado='ocupada')
        
        solicitudes_creadas = 0
        
        # Crear 30 solicitudes variadas
        for _ in range(30):
            categoria = random.choice(self.categorias_mantenimiento)
            usuario = random.choice(usuarios_reporta)
            
            # 60% para unidades, 30% para áreas comunes, 10% sin ubicación específica
            rand_val = random.random()
            if rand_val < 0.6 and unidades_ocupadas.exists():
                unidad_habitacional = random.choice(unidades_ocupadas)
                area_comun = None
            elif rand_val < 0.9 and self.areas_comunes:
                unidad_habitacional = None
                area_comun = random.choice(self.areas_comunes)
            else:
                unidad_habitacional = None
                area_comun = None
            
            # Determinar prioridad realista basada en el tipo de problema
            if categoria.nombre in ['Plomería', 'Sistema Eléctrico', 'Ascensores']:
                prioridad = random.choices(['alta', 'urgente', 'media'], weights=[0.4, 0.4, 0.2])[0]
            elif categoria.nombre in ['Seguridad', 'Aire Acondicionado']:
                prioridad = random.choices(['alta', 'media', 'baja'], weights=[0.3, 0.5, 0.2])[0]
            else:
                prioridad = random.choices(['media', 'baja', 'alta'], weights=[0.5, 0.3, 0.2])[0]
            
            solicitud = SolicitudMantenimiento.objects.create(
                unidad_habitacional=unidad_habitacional,
                area_comun=area_comun,
                categoria_mantenimiento=categoria,
                usuario_reporta=usuario,
                titulo=fake.sentence(nb_words=4),
                descripcion=fake.paragraph(nb_sentences=3),
                prioridad=prioridad,
                estado=random.choice(estados),
                fecha_limite=fake.date_between(start_date='+1d', end_date='+30d'),
                creador_tipo=random.choice(creador_tipos)
            )
            
            # Si está completada, asignar fecha de completado realista
            if solicitud.estado == 'completado':
                fecha_completado = fake.date_between(
                    start_date=solicitud.fecha_reporte.date(), 
                    end_date=min(solicitud.fecha_limite, datetime.now().date())
                )
                solicitud.fecha_completado = timezone.make_aware(
                    datetime.combine(fecha_completado, datetime.now().time())
                )
                solicitud.save()
            
            solicitudes_creadas += 1
        
        self.stdout.write(f"Solicitudes de mantenimiento creadas: {solicitudes_creadas}")

    def crear_tareas_mantenimiento(self):
        self.stdout.write("Creando tareas de mantenimiento...")
        
        estados = ['pendiente', 'en_proceso', 'completado', 'cancelado']
        solicitudes = SolicitudMantenimiento.objects.all()
        tecnicos = Usuario.objects.filter(tipo='mantenimiento')
        
        tareas_creadas = 0
        
        for solicitud in solicitudes:
            # Crear 1-3 tareas por solicitud (solo para asignadas, en proceso o completadas)
            if solicitud.estado in ['asignado', 'en_proceso', 'completado']:
                num_tareas = random.randint(1, 3)
                
                for i in range(num_tareas):
                    tecnico = random.choice(tecnicos) if tecnicos.exists() else None
                    
                    tarea = TareaMantenimiento.objects.create(
                        solicitud_mantenimiento=solicitud,
                        usuario_asignado=tecnico,
                        descripcion=fake.paragraph(nb_sentences=2),
                        estado=random.choice(estados),
                        fecha_limite=fake.date_between(start_date='+1d', end_date='+15d'),
                        costo_estimado=round(random.uniform(50.0, 500.0), 2)
                    )
                    
                    # Si la tarea está completada, asignar datos reales
                    if tarea.estado == 'completado':
                        fecha_completado = fake.date_between(
                            start_date=tarea.fecha_asignacion.date(), 
                            end_date=min(tarea.fecha_limite, datetime.now().date())
                        )
                        tarea.fecha_completado = timezone.make_aware(
                            datetime.combine(fecha_completado, datetime.now().time())
                        )
                        # Costo real puede variar ±25% del estimado
                        variacion = random.uniform(0.75, 1.25)
                        tarea.costo_real = round(tarea.costo_estimado * variacion, 2)
                        tarea.save()
                    
                    tareas_creadas += 1
        
        self.stdout.write(f"Tareas de mantenimiento creadas: {tareas_creadas}")

    def crear_mantenimiento_preventivo(self):
        self.stdout.write("Creando mantenimientos preventivos...")
        
        tecnicos = Usuario.objects.filter(tipo='mantenimiento')
        
        mantenimientos_creados = 0
        periodicidades = [7, 15, 30, 90, 180, 365]  # días
        
        for categoria in self.categorias_mantenimiento:
            # Crear mantenimiento preventivo para el 50% de las categorías
            if random.choice([True, False]):
                # Decidir si es para área común o general
                if random.choice([True, False]) and self.areas_comunes:
                    area_comun = random.choice(self.areas_comunes)
                else:
                    area_comun = None
                    
                tecnico = random.choice(tecnicos) if tecnicos.exists() else None
                
                periodicidad = random.choice(periodicidades)
                ultima_ejecucion = fake.date_between(start_date='-90d', end_date='-7d')
                
                mantenimiento = MantenimientoPreventivo.objects.create(
                    categoria_mantenimiento=categoria,
                    area_comun=area_comun,
                    descripcion=f"Mantenimiento preventivo de {categoria.nombre.lower()}",
                    periodicidad_dias=periodicidad,
                    ultima_ejecucion=ultima_ejecucion,
                    proxima_ejecucion=ultima_ejecucion + timedelta(days=periodicidad),
                    responsable=tecnico
                )
                
                mantenimientos_creados += 1
        
        self.stdout.write(f"Mantenimientos preventivos creados: {mantenimientos_creados}")