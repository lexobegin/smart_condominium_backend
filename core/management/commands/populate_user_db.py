import random
from django.core.management.base import BaseCommand
from faker import Faker
from core.models import *
from django.utils import timezone
from datetime import date, timedelta

fake = Faker('es_ES')

class Command(BaseCommand):
    help = 'Pobla la base de datos con condominios, unidades, usuarios, roles y permisos'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando población de base de datos...")

        self.crear_roles_y_permisos()
        self.crear_condominios()
        self.crear_unidades_habitacionales()
        self.crear_usuarios_y_relaciones()

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
        nombres = [
            'Condominio Las Palmas', 
            'Condominio Vista Mar', 
            'Condominio Jardines del Sur',
            'Condominio Altos del Norte',
            'Condominio Valle Azul'
        ]

        for nombre in nombres:
            condominio = Condominio.objects.create(
                nombre=nombre,
                direccion=fake.address(),
                telefono=fake.phone_number(),
                email=fake.email()
            )
            self.condominios.append(condominio)

        self.stdout.write(f"Condominios creados: {len(self.condominios)}")

    def crear_unidades_habitacionales(self):
        self.unidades_por_condominio = {}
        
        for condominio in self.condominios:
            unidades_condominio = []
            num_unidades = random.randint(40, 50)  # Entre 40 y 50 unidades por condominio
            
            for i in range(1, num_unidades + 1):
                unidad = UnidadHabitacional.objects.create(
                    condominio=condominio,
                    codigo=f"{condominio.nombre[:3].upper()}-{i:03d}",
                    tipo=random.choice(['departamento', 'casa', 'local', 'oficina']),
                    metros_cuadrados=random.uniform(60.0, 200.0),
                    estado=random.choice(['ocupada', 'desocupada', 'en_construccion']),
                )
                unidades_condominio.append(unidad)
            
            self.unidades_por_condominio[condominio.id] = unidades_condominio
            self.stdout.write(f"Condominio {condominio.nombre}: {len(unidades_condominio)} unidades creadas")

    def crear_usuarios_y_relaciones(self):
        admin_counter = 1
        
        for condominio in self.condominios:
            unidades = self.unidades_por_condominio[condominio.id]
            
            self.stdout.write(f"\nCreando usuarios para {condominio.nombre}...")
            
            # 1. CREAR ADMINISTRADORES (2 por condominio)
            for i in range(2):
                admin = self.crear_usuario_base(
                    tipo='administrador',
                    email=f"admin{admin_counter}@mail.com",
                    condominio=condominio
                )
                admin_counter += 1
                self.stdout.write(f"  Administrador creado: {admin.email}")

            # 2. CREAR PERSONAL DE SEGURIDAD (5 por condominio)
            for i in range(5):
                seguridad = self.crear_usuario_base(
                    tipo='seguridad',
                    condominio=condominio
                )
                self.stdout.write(f"  Seguridad creado: {seguridad.email}")

            # 3. CREAR PERSONAL DE MANTENIMIENTO (10 por condominio)
            for i in range(10):
                mantenimiento = self.crear_usuario_base(
                    tipo='mantenimiento',
                    condominio=condominio
                )
                self.stdout.write(f"  Mantenimiento creado: {mantenimiento.email}")

            # 4. CREAR PROPIETARIOS Y RESIDENTES PARA UNIDADES OCUPADAS
            unidades_ocupadas = [u for u in unidades if u.estado == 'ocupada']
            self.stdout.write(f"  Unidades ocupadas: {len(unidades_ocupadas)}")
            
            for unidad in unidades_ocupadas:
                # Crear propietario para cada unidad ocupada
                propietario = self.crear_usuario_base(
                    tipo='propietario',
                    condominio=condominio
                )
                
                # Crear relación propietario-unidad
                UsuarioUnidad.objects.create(
                    usuario=propietario,
                    unidad=unidad,
                    tipo_relacion='propietario',
                    fecha_inicio=fake.date_between(start_date='-5y', end_date='today'),
                    es_principal=True
                )
                
                # Crear residentes (entre 1 y 5 por unidad)
                num_residentes = random.randint(1, 5)
                for i in range(num_residentes):
                    residente = self.crear_usuario_base(
                        tipo='residente',
                        condominio=condominio
                    )
                    
                    # Crear relación residente-unidad
                    UsuarioUnidad.objects.create(
                        usuario=residente,
                        unidad=unidad,
                        tipo_relacion='residente',
                        fecha_inicio=fake.date_between(start_date='-2y', end_date='today'),
                        es_principal=(i == 0)  # El primer residente es principal
                    )
                
                self.stdout.write(f"  Unidad {unidad.codigo}: {num_residentes} residentes + 1 propietario")

        # Estadísticas finales
        total_usuarios = Usuario.objects.count()
        total_unidades = UnidadHabitacional.objects.count()
        total_relaciones = UsuarioUnidad.objects.count()
        
        self.stdout.write(f"\n--- ESTADÍSTICAS FINALES ---")
        self.stdout.write(f"Total usuarios: {total_usuarios}")
        self.stdout.write(f"Total unidades: {total_unidades}")
        self.stdout.write(f"Total relaciones usuario-unidad: {total_relaciones}")

    def crear_usuario_base(self, tipo, email=None, condominio=None):
        """Crea un usuario base con datos aleatorios"""
        nombre = fake.first_name()
        apellidos = fake.last_name()
        genero = random.choice(['M', 'F'])
        ci = fake.unique.random_number(digits=8)
        
        if not email:
            # Generar email único basado en nombre y apellidos
            base_email = f"{nombre.lower()}.{apellidos.lower()}.{random.randint(1000,9999)}"
            email = f"{base_email}@mail.com"
            
            # Asegurar que el email sea único
            counter = 1
            while Usuario.objects.filter(email=email).exists():
                email = f"{base_email}{counter}@mail.com"
                counter += 1

        usuario = Usuario.objects.create(
            email=email,
            nombre=nombre,
            apellidos=apellidos,
            ci=str(ci),
            fecha_nacimiento=fake.date_of_birth(minimum_age=18, maximum_age=80),
            genero=genero,
            telefono=fake.phone_number(),
            tipo=tipo,
            estado='activo',
            is_active=True,
            is_staff=(tipo == 'administrador'),
        )
        usuario.set_password('12345678')
        usuario.save()

        # Asignar Rol correspondiente
        rol_nombre = tipo.capitalize()
        rol = self.rol_objs.get(rol_nombre)
        if rol:
            UsuarioRol.objects.get_or_create(usuario=usuario, rol=rol)

        return usuario

    def crear_camaras_seguridad(self):
        """OPCIONAL: Crear cámaras de seguridad para cada condominio"""
        for condominio in self.condominios:
            tipos_camara = ['entrada_principal', 'estacionamiento', 'area_comun', 'perimetral']
            
            for i, tipo in enumerate(tipos_camara, 1):
                CamaraSeguridad.objects.create(
                    condominio=condominio,
                    nombre=f"Cámara {tipo.replace('_', ' ').title()} {i}",
                    ubicacion=fake.street_address(),
                    tipo_camara=tipo,
                    url_stream=f"rtsp://camera{condominio.id}_{i}.stream",
                    esta_activa=random.choice([True, True, True, False])  # 75% activas
                )
        
        self.stdout.write(f"Cámaras de seguridad creadas: {CamaraSeguridad.objects.count()}")