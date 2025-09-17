import random
from django.core.management.base import BaseCommand
from faker import Faker
from core.models import *
from django.utils import timezone

fake = Faker('es_ES')


class Command(BaseCommand):
    help = 'Pobla la base de datos con condominios, unidades, usuarios, roles y permisos'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando población de base de datos...")

        self.crear_conceptos_cobro()
        self.crear_facturas_y_pagos()
        self.crear_comunicados()
        self.crear_notificaciones()

        self.stdout.write(self.style.SUCCESS("¡Base de datos poblada exitosamente!"))

    def crear_conceptos_cobro(self):

        self.conceptos = []

        conceptos = [
            'Cuota de mantenimiento',
            'Fondo de reserva',
            'Reparación de ascensor',
            'Limpieza general',
            'Reemplazo de bombillos'
        ]

        tipos_validos = ['cuota_mensual', 'multa', 'reserva', 'servicio', 'otros']
        periodicidades = ['mensual', 'trimestral', 'anual', 'unico', 'eventual']

        condominios = Condominio.objects.all()

        if not condominios.exists():
            self.stdout.write(self.style.ERROR("No hay condominios en la base de datos."))
            return

        for condominio in condominios:
            for nombre in conceptos:
                concepto = ConceptoCobro.objects.create(
                    nombre=nombre,
                    descripcion=fake.sentence(),
                    tipo=random.choice(tipos_validos),
                    monto=round(random.uniform(20.0, 200.0), 2),
                    periodicidad=random.choice(periodicidades),
                    aplica_desde=timezone.now().date(),
                    aplica_hasta=timezone.now().date().replace(year=timezone.now().year + 1),
                    condominio=condominio
                )
                self.conceptos.append(concepto)

        self.stdout.write(self.style.SUCCESS(f"Conceptos de cobro creados: {len(self.conceptos)}"))

    def crear_facturas_y_pagos(self):
        unidades = UnidadHabitacional.objects.all()
        estados_factura = ['pendiente', 'pagada', 'vencida']
        estados_pago = ['aprobado', 'rechazado', 'pendiente']
        metodos_pago = ['efectivo', 'transferencia', 'tarjeta']

        self.facturas = []

        for unidad in unidades:
            for i in range(2):  # 2 facturas por unidad
                concepto = random.choice(self.conceptos)
                monto = concepto.monto
                fecha_emision = fake.date_this_year()
                fecha_vencimiento = fake.date_between(start_date=fecha_emision, end_date='+30d')

                factura = Factura.objects.create(
                    unidad_habitacional=unidad,
                    concepto_cobro=concepto,
                    monto=monto,
                    descripcion=f"Factura por {concepto.nombre.lower()}",
                    fecha_emision=fecha_emision,
                    fecha_vencimiento=fecha_vencimiento,
                    estado=random.choice(estados_factura)
                )
                self.facturas.append(factura)

                # Crear pago si la factura está pagada
                if factura.estado == 'pagada':
                    Pago.objects.create(
                        factura=factura,
                        monto=monto,
                        fecha_pago=fake.date_between(start_date=fecha_emision, end_date=fecha_vencimiento),
                        metodo_pago=random.choice(metodos_pago),
                        referencia_pago=fake.uuid4(),
                        estado=random.choice(estados_pago)
                    )

        self.stdout.write(f"Facturas creadas: {len(self.facturas)}")
        self.stdout.write(f"Pagos creados: {Pago.objects.count()}")

    def crear_comunicados(self):
        prioridades = ['alta', 'media', 'baja']
        self.comunicados = []

        # Buscar administradores
        admins = Usuario.objects.filter(tipo='administrador')
        if not admins.exists():
            self.stdout.write(self.style.ERROR("No hay usuarios administradores para asignar como autores"))
            return

        for i in range(10):
            autor = random.choice(admins)

            comunicado = Comunicado.objects.create(
                titulo=fake.sentence(nb_words=6),
                contenido=fake.paragraph(nb_sentences=3),
                fecha_publicacion=fake.date_this_year(),
                prioridad=random.choice(prioridades),
                autor=autor  # Campo obligatorio
            )
            self.comunicados.append(comunicado)

            # Asociar a 5 unidades aleatorias (si hay suficientes)
            unidades_disponibles = list(UnidadHabitacional.objects.all())
            if len(unidades_disponibles) >= 5:
                unidades = random.sample(unidades_disponibles, k=5)
                for unidad in unidades:
                    ComunicadoUnidad.objects.create(
                        comunicado=comunicado,
                        unidad_habitacional=unidad,
                        leido=random.choice([True, False])
                    )

        self.stdout.write(f"Comunicados creados: {len(self.comunicados)}")
        self.stdout.write(f"Comunicados-Unidad creados: {ComunicadoUnidad.objects.count()}")
    
    def crear_notificaciones(self):
        tipos = ['informativa', 'advertencia', 'urgente']
        prioridades = ['alta', 'media', 'baja']
        usuarios = Usuario.objects.all()

        for usuario in random.sample(list(usuarios), k=20):  # 20 notificaciones aleatorias
            Notificacion.objects.create(
                usuario=usuario,
                titulo=fake.sentence(),
                mensaje=fake.text(max_nb_chars=120),
                tipo=random.choice(tipos),
                prioridad=random.choice(prioridades),
                enviada=random.choice([True, False]),
                leida=random.choice([True, False]),
                fecha_envio=fake.date_time_this_year()
            )

        self.stdout.write(f"Notificaciones creadas: {Notificacion.objects.count()}")