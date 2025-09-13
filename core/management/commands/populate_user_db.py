import random
from django.core.management.base import BaseCommand
from faker import Faker
from core.models import (
    Condominio, UnidadHabitacional, Usuario,
    Rol, Permiso, RolPermiso, UsuarioRol
)
from django.utils import timezone

fake = Faker('es_ES')


class Command(BaseCommand):
    help = 'Pobla la base de datos con condominios, unidades, usuarios, roles y permisos'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando población de base de datos...")

        self.crear_roles_y_permisos()
        self.crear_condominios()
        self.crear_usuarios()

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