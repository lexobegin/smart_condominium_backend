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

        self.crear_roles_y_permisos()
        self.crear_condominios()
        self.crear_usuarios()

        """self.crear_conceptos_cobro()
        self.crear_facturas_y_pagos()
        self.crear_comunicados()
        self.crear_notificaciones()"""

        self.stdout.write(self.style.SUCCESS("¡Base de datos poblada exitosamente!"))

    def crear_roles_y_permisos(self):
        roles = ['Administrador', 'Residente', 'Seguridad', 'Mantenimiento', 'Propietario']
        permisos = [
            ('ver_dashboard', 'Ver panel principal', 'General'),
            ('gestionar_unidades', 'Gestionar unidades habitacionales', 'Administración'),
            ('ver_finanzas', 'Ver finanzas', 'Finanzas'),
            ('registrar_visitas', 'Registrar visitas', 'Seguridad'),
            ('reportar_mantenimiento', 'Reportar mantenimientos', 'Mantenimiento'),
        ]

        self.rol_objs = {}

        for rol in roles:
            obj, _ = Rol.objects.get_or_create(nombre=rol)
            self.rol_objs[rol] = obj

        for nombre, descripcion, modulo in permisos:
            permiso, _ = Permiso.objects.get_or_create(nombre=nombre, defaults={
                'descripcion': descripcion,
                'modulo': modulo
            })
            # Asignar todos los permisos al administrador
            RolPermiso.objects.get_or_create(rol=self.rol_objs['Administrador'], permiso=permiso)

        self.stdout.write(f"Roles creados: {len(roles)}")
        self.stdout.write(f"Permisos creados: {len(permisos)}")

    def crear_condominios(self):
        self.condominios = []
        nombres = ['Condominio Las Palmas', 'Condominio Vista Mar', 'Condominio Jardines del Sur']

        for nombre in nombres:
            condominio = Condominio.objects.create(
                nombre=nombre,
                direccion=fake.address(),
                telefono=fake.phone_number(),
                email=fake.email()
            )
            self.condominios.append(condominio)

        self.stdout.write(f"Condominios creados: {len(self.condominios)}")

    def crear_usuarios(self):
        generos = ['M', 'F']
        tipos_usuario = ['residente', 'propietario', 'administrador', 'seguridad', 'mantenimiento']
        unidades_total = 0

        for condominio in self.condominios:
            for i in range(1, 11):  # 10 unidades por condominio
                unidad = UnidadHabitacional.objects.create(
                    condominio=condominio,
                    codigo=f"{condominio.nombre[:3].upper()}-{i:03d}",
                    tipo=random.choice(['departamento', 'casa']),
                    metros_cuadrados=random.uniform(60.0, 150.0),
                    estado=random.choice(['ocupada', 'desocupada']),
                )

                # Crear propietario
                propietario = self.crear_usuario_random(tipo='propietario', unidad=unidad)
                unidad.propietario_actual = propietario

                # Crear residente si está ocupada
                if unidad.estado == 'ocupada':
                    residente = self.crear_usuario_random(tipo='residente', unidad=unidad)
                    unidad.residente_actual = residente

                unidad.save()
                unidades_total += 1

            # Crear un administrador por condominio
            self.crear_usuario_random(tipo='administrador', unidad=None)

            # Crear personal de seguridad y mantenimiento
            for _ in range(2):
                self.crear_usuario_random(tipo='seguridad')
                self.crear_usuario_random(tipo='mantenimiento')

        self.stdout.write(f"Usuarios creados: {Usuario.objects.count()}")
        self.stdout.write(f"Unidades habitacionales creadas: {unidades_total}")

    def crear_usuario_random(self, tipo, unidad=None):
        nombre = fake.first_name()
        apellidos = fake.last_name()
        genero = random.choice(['M', 'F'])
        ci = fake.unique.random_number(digits=8)
        email = f"{nombre.lower()}.{apellidos.lower()}.{random.randint(1000,9999)}@mail.com"

        usuario = Usuario.objects.create(
            email=email,
            nombre=nombre,
            apellidos=apellidos,
            ci=str(ci),
            fecha_nacimiento=fake.date_of_birth(minimum_age=18, maximum_age=80),
            genero=genero,
            telefono=fake.phone_number(),
            tipo=tipo,
            unidad_habitacional=unidad if tipo in ['residente', 'propietario'] else None,
            estado='activo',
            is_active=True,
            is_staff=True if tipo == 'administrador' else False,
        )
        usuario.set_password('12345678')
        usuario.save()

        # Asignar Rol
        rol = self.rol_objs.get(tipo.capitalize())
        if rol:
            UsuarioRol.objects.get_or_create(usuario=usuario, rol=rol)

        return usuario
"""
    def crear_conceptos_cobro(self):
        tipos = ['mensual', 'extraordinario', 'servicio']
        conceptos = ['Cuota de mantenimiento', 'Fondo de reserva', 'Reparación de ascensor', 'Limpieza general', 'Reemplazo de bombillos']

        self.conceptos = []

        for nombre in conceptos:
            concepto = ConceptoCobro.objects.create(
                nombre=nombre,
                descripcion=fake.sentence(),
                tipo=random.choice(tipos),
                monto=random.uniform(20.0, 200.0),
                aplica_desde=timezone.now().date(),
                aplica_hasta=timezone.now().date().replace(year=timezone.now().year + 1)
            )
            self.conceptos.append(concepto)

        self.stdout.write(f"Conceptos de cobro creados: {len(self.conceptos)}")

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
                    concepto=concepto,
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

        for i in range(10):
            comunicado = Comunicado.objects.create(
                titulo=fake.sentence(nb_words=6),
                contenido=fake.paragraph(nb_sentences=3),
                fecha_publicacion=fake.date_this_year(),
                prioridad=random.choice(prioridades),
            )
            self.comunicados.append(comunicado)

            # Asociar a 5 unidades aleatorias
            unidades = random.sample(list(UnidadHabitacional.objects.all()), k=5)
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

        self.stdout.write(f"Notificaciones creadas: {Notificacion.objects.count()}")"""