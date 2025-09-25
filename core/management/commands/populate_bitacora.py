import random
from django.core.management.base import BaseCommand
from faker import Faker
from core.models import *
from django.utils import timezone
from datetime import datetime, timedelta

fake = Faker('es_ES')

class Command(BaseCommand):
    help = 'Pobla la base de datos con 10 registros de bitácora del sistema'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando población de bitácora del sistema...")

        self.crear_registros_bitacora()

        self.stdout.write(self.style.SUCCESS("¡Registros de bitácora creados exitosamente!"))

    def crear_registros_bitacora(self):
        self.stdout.write("Creando registros de bitácora...")
        
        # Obtener algunos usuarios de diferentes tipos para los registros
        administradores = Usuario.objects.filter(tipo='administrador', estado='activo')
        residentes = Usuario.objects.filter(tipo='residente', estado='activo')
        seguridad = Usuario.objects.filter(tipo='seguridad', estado='activo')
        
        # Combinar todos los usuarios (algunos registros pueden ser del sistema sin usuario)
        todos_usuarios = list(administradores) + list(residentes) + list(seguridad)
        
        # Definir acciones y módulos realistas del sistema
        acciones_modulos = [
            # Acciones de administración
            {'accion': 'login_exitoso', 'modulo': 'Autenticación', 'descripcion': 'Inicio de sesión exitoso'},
            {'accion': 'logout', 'modulo': 'Autenticación', 'descripcion': 'Cierre de sesión'},
            {'accion': 'cambio_password', 'modulo': 'Seguridad', 'descripcion': 'Contraseña actualizada'},
            {'accion': 'crear_usuario', 'modulo': 'Administración', 'descripcion': 'Nuevo usuario registrado'},
            {'accion': 'editar_usuario', 'modulo': 'Administración', 'descripcion': 'Usuario modificado'},
            {'accion': 'crear_factura', 'modulo': 'Finanzas', 'descripcion': 'Factura generada'},
            {'accion': 'pago_registrado', 'modulo': 'Finanzas', 'descripcion': 'Pago procesado'},
            {'accion': 'crear_comunicado', 'modulo': 'Comunicación', 'descripcion': 'Comunicado publicado'},
            {'accion': 'reserva_creada', 'modulo': 'Reservas', 'descripcion': 'Reserva de área común'},
            {'accion': 'solicitud_mantenimiento', 'modulo': 'Mantenimiento', 'descripcion': 'Solicitud creada'},
            
            # Acciones de seguridad
            {'accion': 'acceso_denegado', 'modulo': 'Seguridad', 'descripcion': 'Intento de acceso no autorizado'},
            {'accion': 'reconocimiento_facial', 'modulo': 'IA Seguridad', 'descripcion': 'Reconocimiento facial procesado'},
            {'accion': 'alerta_seguridad', 'modulo': 'IA Seguridad', 'descripcion': 'Alerta generada por sistema'},
            {'accion': 'registro_visitante', 'modulo': 'Seguridad', 'descripcion': 'Visitante registrado'},
            
            # Acciones del sistema
            {'accion': 'backup_sistema', 'modulo': 'Sistema', 'descripcion': 'Copia de seguridad realizada'},
            {'accion': 'actualizacion_sistema', 'modulo': 'Sistema', 'descripcion': 'Sistema actualizado'},
            {'accion': 'error_sistema', 'modulo': 'Sistema', 'descripcion': 'Error detectado en módulo'},
        ]
        
        # Crear 10 registros de bitácora con fechas distribuidas en los últimos 7 días
        registros_creados = 0
        hoy = timezone.now()
        
        for i in range(10):
            # Distribuir los registros en los últimos 7 días
            dias_atras = random.randint(0, 7)
            minutos_atras = random.randint(0, 1439)  # 0-1439 minutos en un día
            
            fecha_registro = hoy - timedelta(days=dias_atras, minutes=minutos_atras)
            
            # 80% de registros con usuario, 20% del sistema (sin usuario)
            if random.random() < 0.8 and todos_usuarios:
                usuario = random.choice(todos_usuarios)
            else:
                usuario = None
            
            accion_modulo = random.choice(acciones_modulos)
            
            # Generar detalles específicos según la acción
            detalles = self.generar_detalles_bitacora(accion_modulo['accion'], usuario)
            
            bitacora = Bitacora.objects.create(
                usuario=usuario,
                accion=accion_modulo['accion'],
                modulo=accion_modulo['modulo'],
                detalles=detalles,
                ip_address=fake.ipv4(),
                user_agent=random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                    'Dart/3.0 (dart:io)',
                    'Python-urllib/3.9'
                ]),
                created_at=fecha_registro
            )
            
            registros_creados += 1
            self.stdout.write(f"  Registro {i+1}: {accion_modulo['accion']} - {accion_modulo['modulo']}")
        
        self.stdout.write(f"Registros de bitácora creados: {registros_creados}")

    def generar_detalles_bitacora(self, accion, usuario):
        """Genera detalles específicos para cada tipo de acción"""
        
        if accion == 'login_exitoso' and usuario:
            return f"Usuario {usuario.email} inició sesión desde la aplicación móvil"
        
        elif accion == 'logout' and usuario:
            return f"Usuario {usuario.nombre} cerró sesión después de {random.randint(5, 120)} minutos de actividad"
        
        elif accion == 'cambio_password' and usuario:
            return f"Usuario {usuario.email} actualizó su contraseña de forma segura"
        
        elif accion == 'crear_usuario':
            nuevo_usuario = Usuario.objects.order_by('-id').first()
            if nuevo_usuario:
                return f"Nuevo usuario creado: {nuevo_usuario.email} ({nuevo_usuario.get_tipo_display()})"
            return "Nuevo usuario registrado en el sistema"
        
        elif accion == 'editar_usuario' and usuario:
            campos = random.choice(['perfil', 'datos de contacto', 'configuración de notificaciones'])
            return f"Usuario {usuario.email} actualizó sus {campos}"
        
        elif accion == 'crear_factura':
            factura = Factura.objects.order_by('-id').first()
            if factura:
                return f"Factura #{factura.id} creada para {factura.unidad_habitacional.codigo} - ${factura.monto}"
            return "Nueva factura generada en el sistema"
        
        elif accion == 'pago_registrado':
            pago = Pago.objects.order_by('-id').first()
            if pago:
                return f"Pago #{pago.id} registrado por ${pago.monto} via {pago.get_metodo_pago_display()}"
            return "Transacción de pago procesada exitosamente"
        
        elif accion == 'crear_comunicado':
            comunicado = Comunicado.objects.order_by('-id').first()
            if comunicado:
                return f"Comunicado '{comunicado.titulo[:30]}...' publicado por {comunicado.autor.nombre}"
            return "Nuevo comunicado publicado en el sistema"
        
        elif accion == 'reserva_creada' and usuario:
            area = AreaComun.objects.order_by('?').first()
            if area:
                return f"Reserva creada por {usuario.nombre} para {area.nombre}"
            return f"Usuario {usuario.nombre} realizó una reserva de área común"
        
        elif accion == 'solicitud_mantenimiento' and usuario:
            categorias = ['Plomería', 'Electricidad', 'Pintura', 'Jardinería']
            return f"Solicitud de mantenimiento para {random.choice(categorias)} reportada por {usuario.nombre}"
        
        elif accion == 'acceso_denegado':
            return "Intento de acceso no autorizado detectado en puerta principal - credenciales inválidas"
        
        elif accion == 'reconocimiento_facial':
            confianza = round(random.uniform(0.85, 0.99), 2)
            return f"Reconocimiento facial procesado - confidence score: {confianza}"
        
        elif accion == 'alerta_seguridad':
            tipos = ['persona no autorizada', 'vehiculo sospechoso', 'comportamiento inusual']
            return f"Alerta de seguridad generada: {random.choice(tipos)} detectado en área común"
        
        elif accion == 'registro_visitante':
            return f"Visitante registrado en sistema - ingreso autorizado por residente"
        
        elif accion == 'backup_sistema':
            return "Copia de seguridad automática de la base de datos completada exitosamente"
        
        elif accion == 'actualizacion_sistema':
            return "Sistema actualizado a la versión más reciente - proceso automático"
        
        elif accion == 'error_sistema':
            modulos = ['módulo de pagos', 'sistema de notificaciones', 'base de datos', 'API de IA']
            return f"Error menor detectado en {random.choice(modulos)} - resuelto automáticamente"
        
        else:
            return f"Acción del sistema registrada: {accion}"
