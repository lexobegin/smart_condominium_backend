import random
from django.core.management.base import BaseCommand
from faker import Faker
from core.models import *
from django.utils import timezone
from datetime import datetime, timedelta

fake = Faker('es_ES')

class Command(BaseCommand):
    help = 'Pobla la base de datos con datos de seguridad: vehículos, registros de acceso, visitantes, incidentes y cámaras'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando población de datos de seguridad con IA...")

        self.crear_camaras_seguridad()
        self.crear_vehiculos()
        self.crear_registros_acceso()
        self.crear_visitantes()
        self.crear_incidentes_seguridad()

        self.stdout.write(self.style.SUCCESS("¡Datos de seguridad con IA poblados exitosamente!"))

    def crear_camaras_seguridad(self):
        self.stdout.write("Creando cámaras de seguridad...")
        
        self.camaras = []
        tipos_camara = [
            {'tipo': 'entrada_principal', 'nombre': 'Entrada Principal', 'cantidad': (2, 3)},
            {'tipo': 'estacionamiento', 'nombre': 'Estacionamiento', 'cantidad': (3, 5)},
            {'tipo': 'area_comun', 'nombre': 'Área Común', 'cantidad': (4, 6)},
            {'tipo': 'perimetral', 'nombre': 'Perimetral', 'cantidad': (2, 4)}
        ]
        
        condominios = Condominio.objects.all()
        
        for condominio in condominios:
            for tipo_cam in tipos_camara:
                cantidad_min, cantidad_max = tipo_cam['cantidad']
                cantidad = random.randint(cantidad_min, cantidad_max)
                
                for i in range(1, cantidad + 1):
                    camara = CamaraSeguridad.objects.create(
                        condominio=condominio,
                        nombre=f"{tipo_cam['nombre']} {i} - {condominio.nombre.split()[-1]}",
                        ubicacion=self.generar_ubicacion_camara(tipo_cam['tipo']),
                        tipo_camara=tipo_cam['tipo'],
                        url_stream=f"rtsp://{condominio.nombre.lower().replace(' ', '_')}_{tipo_cam['tipo']}_{i}.stream",
                        esta_activa=random.choices([True, False], weights=[0.85, 0.15])[0]
                    )
                    self.camaras.append(camara)
        
        self.stdout.write(f"Cámaras de seguridad creadas: {len(self.camaras)}")

    def generar_ubicacion_camara(self, tipo_camara):
        ubicaciones = {
            'entrada_principal': [
                'Puerta Principal Norte', 'Puerta Principal Sur', 'Garita de Seguridad',
                'Recepción Principal', 'Control de Acceso Vehicular'
            ],
            'estacionamiento': [
                'Nivel 1 - Entrada', 'Nivel 1 - Salida', 'Nivel 2 - Zona Central',
                'Área de Visitantes', 'Esquina Noroeste', 'Área Cubierta'
            ],
            'area_comun': [
                'Piscina - Zona Norte', 'Piscina - Zona Sur', 'Salón de Eventos',
                'Gimnasio - Entrada', 'Área de BBQ', 'Jardín Principal',
                'Parque Infantil', 'Terraza Mirador'
            ],
            'perimetral': [
                'Muro Perimetral Este', 'Muro Perimetral Oeste', 'Torre de Vigilancia Norte',
                'Torre de Vigilancia Sur', 'Esquina Noreste', 'Esquina Suroeste'
            ]
        }
        return random.choice(ubicaciones.get(tipo_camara, ['Ubicación General']))

    def crear_vehiculos(self):
        self.stdout.write("Creando vehículos de residentes...")
        
        # Obtener residentes activos con unidades
        residentes_con_unidad = Usuario.objects.filter(
            usuariounidad__tipo_relacion='residente',
            usuariounidad__fecha_fin__isnull=True
        ).distinct()
        
        marcas_modelos = {
            'Toyota': ['Corolla', 'Camry', 'RAV4', 'Hilux', 'Yaris'],
            'Honda': ['Civic', 'Accord', 'CR-V', 'HR-V', 'Pilot'],
            'Ford': ['Fiesta', 'Focus', 'Escape', 'Explorer', 'Ranger'],
            'Chevrolet': ['Spark', 'Aveo', 'Cruze', 'Trailblazer', 'Silverado'],
            'Nissan': ['Versa', 'Sentra', 'Kicks', 'X-Trail', 'Frontier'],
            'Hyundai': ['Accent', 'Elantra', 'Tucson', 'Santa Fe', 'Creta'],
            'Kia': ['Rio', 'Forte', 'Seltos', 'Sportage', 'Sorento']
        }
        
        colores = ['Rojo', 'Azul', 'Negro', 'Blanco', 'Gris', 'Plateado', 'Verde', 'Azul Marino']
        
        vehiculos_creados = 0
        residentes_seleccionados = random.sample(
            list(residentes_con_unidad), 
            min(50, residentes_con_unidad.count())  # Máximo 50 vehículos
        )
        
        for residente in residentes_seleccionados:
            marca = random.choice(list(marcas_modelos.keys()))
            modelo = random.choice(marcas_modelos[marca])
            año = random.randint(2010, 2023)
            
            # Generar placa realista (formato boliviano: XXX-###)
            letras = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
            numeros = ''.join(random.choices('0123456789', k=3))
            placa = f"{letras}-{numeros}"
            
            # Verificar que la placa sea única
            while Vehiculo.objects.filter(placa=placa).exists():
                letras = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
                numeros = ''.join(random.choices('0123456789', k=3))
                placa = f"{letras}-{numeros}"
            
            vehiculo = Vehiculo.objects.create(
                usuario=residente,
                placa=placa,
                marca=marca,
                modelo=f"{modelo} {año}",
                color=random.choice(colores),
                autorizado=random.choices([True, False], weights=[0.95, 0.05])[0],
                datos_ocr=f"Placa: {placa}, Marca: {marca}, Color: {random.choice(colores)}"
            )
            vehiculos_creados += 1
        
        self.stdout.write(f"Vehículos creados: {vehiculos_creados}")

    def crear_registros_acceso(self):
        self.stdout.write("Creando registros de acceso...")
        
        # Obtener vehículos autorizados
        vehiculos_autorizados = Vehiculo.objects.filter(autorizado=True)
        
        # Obtener residentes activos
        residentes_activos = Usuario.objects.filter(
            usuariounidad__tipo_relacion='residente',
            usuariounidad__fecha_fin__isnull=True,
            estado='activo'
        ).distinct()
        
        registros_creados = 0
        hoy = timezone.now()
        
        # Crear registros de los últimos 30 días
        for dias_atras in range(30, 0, -1):
            fecha_base = hoy - timedelta(days=dias_atras)
            
            # Generar entre 20-50 registros por día
            registros_dia = random.randint(20, 50)
            
            for _ in range(registros_dia):
                # 70% peatonal, 30% vehicular
                tipo_acceso = random.choices(['peatonal', 'vehicular'], weights=[0.7, 0.3])[0]
                
                if tipo_acceso == 'peatonal' and residentes_activos.exists():
                    usuario = random.choice(residentes_activos)
                    vehiculo = None
                    metodo = random.choices(['facial', 'tarjeta', 'manual'], weights=[0.6, 0.3, 0.1])[0]
                elif tipo_acceso == 'vehicular' and vehiculos_autorizados.exists():
                    vehiculo = random.choice(vehiculos_autorizados)
                    usuario = vehiculo.usuario
                    metodo = 'placa'
                else:
                    continue
                
                # 85% de reconocimiento exitoso para métodos automáticos
                reconocimiento_exitoso = metodo in ['facial', 'placa'] and random.choices([True, False], weights=[0.85, 0.15])[0]
                
                # Confidence score realista
                if reconocimiento_exitoso:
                    confidence = round(random.uniform(0.85, 0.99), 4)
                else:
                    confidence = round(random.uniform(0.10, 0.70), 4) if random.choice([True, False]) else None
                
                # Generar hora aleatoria del día
                hora_acceso = fecha_base.replace(
                    hour=random.randint(6, 22),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                # Determinar dirección (entrada/salida) - más entradas en la mañana, salidas en la tarde
                if hora_acceso.hour < 12:
                    direccion = random.choices(['entrada', 'salida'], weights=[0.7, 0.3])[0]
                else:
                    direccion = random.choices(['entrada', 'salida'], weights=[0.3, 0.7])[0]
                
                registro = RegistroAcceso.objects.create(
                    usuario=usuario,
                    vehiculo=vehiculo,
                    tipo=tipo_acceso,
                    direccion=direccion,
                    metodo=metodo,
                    fecha_hora=hora_acceso,
                    reconocimiento_exitoso=reconocimiento_exitoso,
                    confidence_score=confidence
                )
                registros_creados += 1
        
        self.stdout.write(f"Registros de acceso creados: {registros_creados}")

    def crear_visitantes(self):
        self.stdout.write("Creando registros de visitantes...")
        
        # Obtener residentes activos que pueden recibir visitas
        residentes_anfitriones = Usuario.objects.filter(
            usuariounidad__tipo_relacion='residente',
            usuariounidad__fecha_fin__isnull=True,
            estado='activo'
        ).distinct()
        
        visitantes_creados = 0
        hoy = timezone.now()
        
        # Crear visitas de los últimos 60 días
        for dias_atras in range(60, 0, -1):
            fecha_base = hoy - timedelta(days=dias_atras)
            
            # Generar entre 5-15 visitas por día
            visitas_dia = random.randint(5, 15)
            
            for _ in range(visitas_dia):
                anfitrion = random.choice(residentes_anfitriones)
                
                # 30% de visitas con vehículo
                tiene_vehiculo = random.random() < 0.3
                placa_vehiculo = fake.license_plate() if tiene_vehiculo else None
                
                # Generar fecha de entrada
                fecha_entrada = fecha_base.replace(
                    hour=random.randint(8, 20),
                    minute=random.randint(0, 59)
                )
                
                # 80% de visitas ya tienen fecha de salida
                tiene_salida = random.random() < 0.8
                if tiene_salida:
                    # Salida entre 1-8 horas después
                    horas_visita = random.randint(1, 8)
                    fecha_salida = fecha_entrada + timedelta(hours=horas_visita)
                else:
                    fecha_salida = None
                
                visitante = Visitante.objects.create(
                    nombre=f"{fake.first_name()} {fake.last_name()}",
                    documento_identidad=fake.random_number(digits=8),
                    telefono=fake.phone_number(),
                    motivo_visita=random.choice([
                        "Visita familiar", "Entrega de paquete", "Reunión social",
                        "Mantenimiento", "Entrega de comida", "Visita médica"
                    ]),
                    anfitrion=anfitrion,
                    fecha_entrada=fecha_entrada,
                    fecha_salida=fecha_salida,
                    placa_vehiculo=placa_vehiculo
                )
                visitantes_creados += 1
        
        self.stdout.write(f"Visitantes creados: {visitantes_creados}")

    def crear_incidentes_seguridad(self):
        self.stdout.write("Creando incidentes de seguridad...")
        
        tipos_incidente = [
            'persona_no_autorizada', 'vehiculo_no_autorizado', 'comportamiento_sospechoso',
            'acceso_no_autorizado', 'mascota_suelta', 'vehiculo_mal_estacionado'
        ]
        
        gravedades = ['baja', 'media', 'alta']
        estados = ['pendiente', 'investigando', 'resuelto', 'falso_positivo']
        
        # Obtener personal de seguridad para asignar incidentes
        personal_seguridad = Usuario.objects.filter(tipo='seguridad', estado='activo')
        
        incidentes_creados = 0
        hoy = timezone.now()
        
        # Crear incidentes de los últimos 90 días
        for dias_atras in range(90, 0, -1):
            fecha_base = hoy - timedelta(days=dias_atras)
            
            # Generar entre 0-3 incidentes por día (no todos los días tienen incidentes)
            if random.random() < 0.6:  # 60% de probabilidad de tener incidentes ese día
                incidentes_dia = random.randint(1, 3)
                
                for _ in range(incidentes_dia):
                    tipo = random.choice(tipos_incidente)
                    
                    # Asignar gravedad según el tipo de incidente
                    if tipo in ['acceso_no_autorizado', 'persona_no_autorizada']:
                        gravedad = random.choices(['alta', 'media', 'baja'], weights=[0.6, 0.3, 0.1])[0]
                    elif tipo in ['vehiculo_no_autorizado', 'comportamiento_sospechoso']:
                        gravedad = random.choices(['media', 'alta', 'baja'], weights=[0.5, 0.3, 0.2])[0]
                    else:
                        gravedad = random.choices(['baja', 'media', 'alta'], weights=[0.6, 0.3, 0.1])[0]
                    
                    # Asignar estado según la fecha (incidentes antiguos más probables de estar resueltos)
                    if dias_atras > 30:
                        estado = random.choices(['resuelto', 'falso_positivo', 'investigando'], weights=[0.7, 0.2, 0.1])[0]
                    elif dias_atras > 7:
                        estado = random.choices(['investigando', 'resuelto', 'pendiente'], weights=[0.4, 0.4, 0.2])[0]
                    else:
                        estado = random.choices(['pendiente', 'investigando', 'resuelto'], weights=[0.5, 0.3, 0.2])[0]
                    
                    # Asignar personal si está en investigación o resuelto
                    usuario_asignado = None
                    if estado in ['investigando', 'resuelto'] and personal_seguridad.exists():
                        usuario_asignado = random.choice(personal_seguridad)
                    
                    # Confidence score para incidentes detectados por IA
                    confidence = round(random.uniform(0.70, 0.98), 4) if random.random() < 0.8 else None
                    
                    incidente = IncidenteSeguridad.objects.create(
                        tipo=tipo,
                        descripcion=self.generar_descripcion_incidente(tipo),
                        ubicacion=random.choice([
                            'Entrada Principal', 'Estacionamiento Nivel 1', 'Área de Piscina',
                            'Jardín Principal', 'Pasillo Este', 'Área de BBQ', 'Salón de Eventos'
                        ]),
                        fecha_hora=fecha_base.replace(
                            hour=random.randint(0, 23),
                            minute=random.randint(0, 59)
                        ),
                        gravedad=gravedad,
                        estado=estado,
                        confidence_score=confidence,
                        usuario_asignado=usuario_asignado
                    )
                    incidentes_creados += 1
        
        self.stdout.write(f"Incidentes de seguridad creados: {incidentes_creados}")

    def generar_descripcion_incidente(self, tipo_incidente):
        descripciones = {
            'persona_no_autorizada': [
                "Persona no identificida intentando acceder sin autorización",
                "Individuo merodeando en zona restringida sin credenciales",
                "Acceso denegado por falta de registro en sistema facial"
            ],
            'vehiculo_no_autorizado': [
                "Vehículo con placa no registrada intentando ingresar",
                "Automóvil no autorizado estacionado en área residentes",
                "Intento de acceso vehicular con credenciales inválidas"
            ],
            'comportamiento_sospechoso': [
                "Persona actuando de manera sospechosa en áreas comunes",
                "Vehículo circulando repetidamente sin motivo aparente",
                "Individuo tomando fotografías de instalaciones"
            ],
            'acceso_no_autorizado': [
                "Intento de acceso por zona perimetral no autorizada",
                "Puerta de emergencia forzada durante la noche",
                "Acceso a área técnica sin autorización"
            ],
            'mascota_suelta': [
                "Canino sin correa en área de piscina",
                "Mascota sin supervisión en jardín principal",
                "Animal doméstico en zona infantil sin dueño"
            ],
            'vehiculo_mal_estacionado': [
                "Vehículo obstruyendo salida de emergencia",
                "Automóvil estacionado en lugar de discapacitados sin credencial",
                "Estacionamiento en doble fila bloqueando circulación"
            ]
        }
        return random.choice(descripciones.get(tipo_incidente, ["Incidente reportado por sistema de seguridad"]))

# Para agregar este comando, crear el archivo en core/management/commands/populate_seguridad_ia_db.py