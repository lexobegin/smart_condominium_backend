import random
from django.core.management.base import BaseCommand
from faker import Faker
from core.models import *
from django.utils import timezone
from datetime import date, timedelta

fake = Faker('es_ES')

class Command(BaseCommand):
    help = 'Pobla la base de datos con conceptos de cobro, facturas, pagos, comunicados y notificaciones'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando población de datos de cobros y comunicaciones...")

        self.crear_conceptos_cobro()
        self.crear_facturas_y_pagos()
        self.crear_comunicados()
        self.crear_notificaciones()

        self.stdout.write(self.style.SUCCESS("¡Datos de cobros y comunicaciones poblados exitosamente!"))

    def crear_conceptos_cobro(self):
        self.stdout.write("Creando conceptos de cobro...")
        
        self.conceptos = []
        conceptos_data = [
            {'nombre': 'Cuota de mantenimiento mensual', 'tipo': 'cuota_mensual', 'monto_base': (50, 200), 'periodicidad': 'mensual'},
            {'nombre': 'Fondo de reserva', 'tipo': 'cuota_mensual', 'monto_base': (20, 50), 'periodicidad': 'mensual'},
            {'nombre': 'Mantenimiento de áreas comunes', 'tipo': 'servicio', 'monto_base': (30, 80), 'periodicidad': 'mensual'},
            {'nombre': 'Servicio de seguridad', 'tipo': 'servicio', 'monto_base': (40, 100), 'periodicidad': 'mensual'},
            {'nombre': 'Multa por ruido', 'tipo': 'multa', 'monto_base': (100, 300), 'periodicidad': 'eventual'},
            {'nombre': 'Multa por mal estacionamiento', 'tipo': 'multa', 'monto_base': (50, 150), 'periodicidad': 'eventual'},
            {'nombre': 'Reserva de sala de eventos', 'tipo': 'reserva', 'monto_base': (80, 200), 'periodicidad': 'eventual'},
            {'nombre': 'Uso de piscina', 'tipo': 'servicio', 'monto_base': (20, 60), 'periodicidad': 'eventual'},
            {'nombre': 'Reparación extraordinaria', 'tipo': 'otros', 'monto_base': (100, 500), 'periodicidad': 'unico'},
        ]

        condominios = Condominio.objects.all()

        if not condominios.exists():
            self.stdout.write(self.style.ERROR("No hay condominios en la base de datos."))
            return

        for condominio in condominios:
            for concepto_data in conceptos_data:
                monto_min, monto_max = concepto_data['monto_base']
                # Variar el monto por condominio para hacerlo más realista
                monto = round(random.uniform(monto_min, monto_max), 2)
                
                concepto = ConceptoCobro.objects.create(
                    nombre=concepto_data['nombre'],
                    descripcion=fake.sentence(),
                    tipo=concepto_data['tipo'],
                    monto=monto,
                    periodicidad=concepto_data['periodicidad'],
                    aplica_desde=timezone.now().date() - timedelta(days=30),
                    aplica_hasta=timezone.now().date().replace(year=timezone.now().year + 1),
                    condominio=condominio
                )
                self.conceptos.append(concepto)

        self.stdout.write(self.style.SUCCESS(f"Conceptos de cobro creados: {len(self.conceptos)}"))

    def crear_facturas_y_pagos(self):
        self.stdout.write("Creando facturas y pagos...")
        
        unidades = UnidadHabitacional.objects.all()
        estados_factura = ['pendiente', 'pagada', 'vencida', 'cancelada']
        metodos_pago = ['tarjeta', 'transferencia', 'efectivo', 'app']
        estados_pago = ['completado', 'pendiente', 'fallido']

        self.facturas = []
        hoy = date.today()

        for unidad in unidades:
            # Obtener conceptos que aplican a este condominio
            conceptos_condominio = [c for c in self.conceptos if c.condominio_id == unidad.condominio_id]
            
            if not conceptos_condominio:
                continue

            # Crear facturas para los últimos 6 meses
            for meses_atras in range(6, 0, -1):
                fecha_base = hoy.replace(day=1) - timedelta(days=30 * meses_atras)
                
                for concepto in conceptos_condominio:
                    # Solo crear facturas para conceptos mensuales o únicos
                    if concepto.periodicidad not in ['mensual', 'unico']:
                        continue
                    
                    # 80% de probabilidad de crear factura para este concepto
                    if random.random() < 0.8:
                        fecha_emision = fecha_base
                        fecha_vencimiento = fecha_base + timedelta(days=15)
                        
                        # Determinar estado basado en fechas
                        if fecha_vencimiento < hoy - timedelta(days=30):
                            estado = random.choices(
                                ['pagada', 'vencida', 'cancelada'], 
                                weights=[0.7, 0.2, 0.1]
                            )[0]
                        elif fecha_vencimiento < hoy:
                            estado = random.choices(
                                ['pagada', 'vencida', 'pendiente'], 
                                weights=[0.6, 0.3, 0.1]
                            )[0]
                        else:
                            estado = random.choices(
                                ['pagada', 'pendiente'], 
                                weights=[0.3, 0.7]
                            )[0]

                        factura = Factura.objects.create(
                            unidad_habitacional=unidad,
                            concepto_cobro=concepto,
                            monto=concepto.monto,
                            descripcion=f"{concepto.nombre} - {fecha_emision.strftime('%B %Y')}",
                            fecha_emision=fecha_emision,
                            fecha_vencimiento=fecha_vencimiento,
                            estado=estado,
                            periodo=fecha_emision.replace(day=1)
                        )
                        self.facturas.append(factura)

                        # Crear pago si la factura está pagada
                        if factura.estado == 'pagada':
                            fecha_pago = fecha_vencimiento - timedelta(days=random.randint(0, 10))
                            if fecha_pago < fecha_emision:
                                fecha_pago = fecha_emision + timedelta(days=1)
                            
                            Pago.objects.create(
                                factura=factura,
                                monto=factura.monto,
                                fecha_pago=fecha_pago,
                                metodo_pago=random.choice(metodos_pago),
                                referencia_pago=f"PAGO-{factura.id}-{random.randint(1000,9999)}",
                                estado='completado',
                                comprobante=f"https://comprobantes.com/{factura.id}.pdf"
                            )

        self.stdout.write(f"Facturas creadas: {len(self.facturas)}")
        self.stdout.write(f"Pagos creados: {Pago.objects.count()}")

    def crear_comunicados(self):
        self.stdout.write("Creando comunicados...")
        
        prioridades = ['alta', 'media', 'baja', 'urgente']
        destinatarios_opciones = ['todos', 'propietarios', 'residentes', 'personal']
        
        # Buscar administradores
        admins = Usuario.objects.filter(tipo='administrador')
        if not admins.exists():
            self.stdout.write(self.style.ERROR("No hay usuarios administradores para asignar como autores"))
            return

        self.comunicados = []
        
        # Crear 15 comunicados variados
        for i in range(15):
            autor = random.choice(admins)
            fecha_publicacion = fake.date_between(start_date='-60d', end_date='today')
            
            comunicado = Comunicado.objects.create(
                titulo=fake.sentence(nb_words=8),
                contenido=fake.paragraph(nb_sentences=5),
                autor=autor,
                prioridad=random.choice(prioridades),
                fecha_publicacion=fecha_publicacion,
                fecha_expiracion=fecha_publicacion + timedelta(days=random.randint(7, 30)),
                destinatarios=random.choice(destinatarios_opciones)
            )
            self.comunicados.append(comunicado)

            # Asignar a unidades según el tipo de destinatario
            if comunicado.destinatarios == 'todos':
                unidades = UnidadHabitacional.objects.all()
            elif comunicado.destinatarios == 'propietarios':
                # Obtener unidades que tienen propietarios activos
                unidades_con_propietarios = UnidadHabitacional.objects.filter(
                    usuariounidad__tipo_relacion='propietario',
                    usuariounidad__fecha_fin__isnull=True
                ).distinct()
                unidades = unidades_con_propietarios
            elif comunicado.destinatarios == 'residentes':
                # Obtener unidades ocupadas (con residentes)
                unidades_ocupadas = UnidadHabitacional.objects.filter(estado='ocupada')
                unidades = unidades_ocupadas
            else:  # personal
                # Para personal, no asignar a unidades específicas
                continue

            # Asignar a un subconjunto de unidades (máximo 10 para no saturar)
            if unidades.exists():
                unidades_seleccionadas = random.sample(
                    list(unidades), 
                    min(10, unidades.count())
                )
                
                for unidad in unidades_seleccionadas:
                    ComunicadoUnidad.objects.create(
                        comunicado=comunicado,
                        unidad_habitacional=unidad
                    )

                    # Crear registros de lectura para algunos usuarios de la unidad
                    usuarios_unidad = Usuario.objects.filter(
                        usuariounidad__unidad=unidad,
                        usuariounidad__fecha_fin__isnull=True
                    ).distinct()
                    
                    for usuario in usuarios_unidad:
                        # 60% de probabilidad de que el usuario haya leído el comunicado
                        if random.random() < 0.6:
                            ComunicadoLeido.objects.get_or_create(
                                comunicado=comunicado,
                                usuario=usuario
                            )

        self.stdout.write(f"Comunicados creados: {len(self.comunicados)}")
        self.stdout.write(f"Comunicados-Unidad creados: {ComunicadoUnidad.objects.count()}")
        self.stdout.write(f"Registros de lectura creados: {ComunicadoLeido.objects.count()}")

    def crear_notificaciones(self):
        self.stdout.write("Creando notificaciones...")
        
        tipos = ['pago', 'seguridad', 'reserva', 'comunicado', 'mantenimiento', 'sistema']
        prioridades = ['alta', 'media', 'baja']
        
        # Obtener usuarios activos
        usuarios_activos = Usuario.objects.filter(estado='activo')
        
        # Crear 50 notificaciones variadas
        notificaciones_creadas = 0
        
        for i in range(50):
            usuario = random.choice(usuarios_activos)
            tipo = random.choice(tipos)
            
            # Determinar contenido según el tipo
            if tipo == 'pago':
                titulo = random.choice([
                    "Recordatorio de pago pendiente",
                    "Pago confirmado exitosamente",
                    "Factura vencida - Acción requerida"
                ])
            elif tipo == 'seguridad':
                titulo = random.choice([
                    "Alerta de seguridad en área común",
                    "Visitante registrado en entrada",
                    "Incidente reportado - Zona de estacionamiento"
                ])
            elif tipo == 'reserva':
                titulo = random.choice([
                    "Reserva de área común confirmada",
                    "Recordatorio: Reserva para mañana",
                    "Solicitud de reserva rechazada"
                ])
            elif tipo == 'comunicado':
                titulo = random.choice([
                    "Nuevo comunicado disponible",
                    "Aviso importante de administración",
                    "Reunión de condominio programada"
                ])
            elif tipo == 'mantenimiento':
                titulo = random.choice([
                    "Solicitud de mantenimiento recibida",
                    "Mantenimiento programado para su unidad",
                    "Reporte de mantenimiento completado"
                ])
            else:  # sistema
                titulo = random.choice([
                    "Actualización del sistema",
                    "Mantenimiento programado de la plataforma",
                    "Nueva funcionalidad disponible"
                ])

            notificacion = Notificacion.objects.create(
                usuario=usuario,
                titulo=titulo,
                mensaje=fake.text(max_nb_chars=120),
                tipo=tipo,
                prioridad=random.choice(prioridades),
                enviada=random.choice([True, False]),
                leida=random.choice([True, False, False]),  # 66% de no leídas
                fecha_envio=fake.date_time_this_month()
            )
            notificaciones_creadas += 1

        self.stdout.write(f"Notificaciones creadas: {notificaciones_creadas}")