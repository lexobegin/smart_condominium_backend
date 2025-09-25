from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError

class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('tipo', 'administrador')  # O el tipo que uses por defecto

        return self.create_user(email, password, **extra_fields)

class Condominio(models.Model):
    nombre = models.CharField(max_length=255)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre


class UnidadHabitacional(models.Model):
    TIPO_CHOICES = [
        ('departamento', 'Departamento'),
        ('casa', 'Casa'),
        ('local', 'Local'),
        ('oficina', 'Oficina'),
    ]

    ESTADO_CHOICES = [
        ('ocupada', 'Ocupada'),
        ('desocupada', 'Desocupada'),
        ('en_construccion', 'En construcción'),
    ]

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    metros_cuadrados = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='desocupada')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.codigo} - {self.condominio.nombre}"
    
    # Métodos útiles para obtener relaciones actuales
    @property
    def propietario_actual(self):
        """Retorna el propietario principal actual"""
        relacion = self.usuariounidad_set.filter(
            tipo_relacion='propietario',
            fecha_fin__isnull=True
        ).first()
        return relacion.usuario if relacion else None

    @property
    def residentes_actuales(self):
        """Retorna todos los residentes actuales"""
        return Usuario.objects.filter(
            usuariounidad__unidad=self,
            usuariounidad__tipo_relacion='residente',
            usuariounidad__fecha_fin__isnull=True
        )

# PRIMERO: Crear el modelo intermedio ANTES de modificar Usuario
class UsuarioUnidad(models.Model):
    TIPO_RELACION_CHOICES = [
        ('propietario', 'Propietario'),
        ('residente', 'Residente'),
        ('inquilino', 'Inquilino'),
        ('familiar', 'Familiar'),
        ('trabajador', 'Trabajador'),
    ]

    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    unidad = models.ForeignKey('UnidadHabitacional', on_delete=models.CASCADE)
    tipo_relacion = models.CharField(max_length=20, choices=TIPO_RELACION_CHOICES)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    es_principal = models.BooleanField(default=False)  # Para identificar relación principal
    
    class Meta:
        unique_together = ('usuario', 'unidad', 'tipo_relacion')
        db_table = 'usuario_unidad'

    def __str__(self):
        return f"{self.usuario} - {self.unidad} ({self.get_tipo_relacion_display()})"

class Usuario(AbstractBaseUser, PermissionsMixin):
    TIPO_CHOICES = [
        ('residente', 'Residente'),
        ('administrador', 'Administrador'),
        ('seguridad', 'Seguridad'),
        ('mantenimiento', 'Mantenimiento'),
        ('propietario', 'Propietario'),
    ]

    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('pendiente', 'Pendiente'),
    ]

    GENERO_CHOICES = [('M', 'Masculino'), ('F', 'Femenino')]

    # Relación muchos-a-muchos:
    unidades_habitacionales = models.ManyToManyField(
        'UnidadHabitacional', 
        through='UsuarioUnidad',
        through_fields=('usuario', 'unidad'),
        related_name='usuarios'
    )

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    nombre = models.CharField(max_length=255)
    apellidos = models.CharField(max_length=255)
    ci = models.CharField(max_length=50, unique=True)  # Número de carnet de identidad
    fecha_nacimiento = models.DateField(blank=True, null=True)
    genero = models.CharField(max_length=1, choices=GENERO_CHOICES, blank=True, null=True)

    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    password = models.CharField(max_length=128)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    token_notificacion = models.CharField(max_length=255, blank=True, null=True)
    foto_perfil = models.TextField(blank=True, null=True)
    datos_faciales = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellidos', 'ci', 'tipo']

    objects = UsuarioManager()

    def __str__(self):
        return f"{self.nombre} {self.apellidos} ({self.get_tipo_display()})"

    @property
    def roles(self):
        return [usuario_rol.rol for usuario_rol in self.usuario_roles.all()]

    @property
    def permisos(self):
        permisos = set()
        for rol in self.roles.all():
            for permiso in rol.permisos.all():
                permisos.add(permiso.nombre)
        return list(permisos)

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Permiso(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    modulo = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} - {self.modulo}"

class RolPermiso(models.Model):
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name='permisos')
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('rol', 'permiso')

    def __str__(self):
        return f"{self.rol.nombre} -> {self.permiso.nombre}"

class UsuarioRol(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='usuario_roles')
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('usuario', 'rol')

    def __str__(self):
        return f"{self.usuario.nombre} -> {self.rol.nombre}"

# ===================================
# FINANZAS
# ===================================

class ConceptoCobro(models.Model):
    TIPO_CHOICES = [
        ('cuota_mensual', 'Cuota Mensual'),
        ('multa', 'Multa'),
        ('reserva', 'Reserva'),
        ('servicio', 'Servicio'),
        ('otros', 'Otros'),
    ]

    PERIODICIDAD_CHOICES = [
        ('mensual', 'Mensual'),
        ('trimestral', 'Trimestral'),
        ('anual', 'Anual'),
        ('unico', 'Único'),
        ('eventual', 'Eventual'),
    ]

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    periodicidad = models.CharField(max_length=20, choices=PERIODICIDAD_CHOICES, default='mensual')
    aplica_desde = models.DateField(blank=True, null=True)
    aplica_hasta = models.DateField(blank=True, null=True)
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} - {self.get_tipo_display()}"


class Factura(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
    ]

    unidad_habitacional = models.ForeignKey('UnidadHabitacional', on_delete=models.CASCADE)
    concepto_cobro = models.ForeignKey('ConceptoCobro', on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    descripcion = models.TextField(blank=True, null=True)
    periodo = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Factura #{self.id} - {self.unidad_habitacional}"


class Pago(models.Model):
    METODO_PAGO_CHOICES = [
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('efectivo', 'Efectivo'),
        ('app', 'App'),
    ]

    ESTADO_CHOICES = [
        ('completado', 'Completado'),
        ('pendiente', 'Pendiente'),
        ('fallido', 'Fallido'),
    ]

    factura = models.ForeignKey('Factura', on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    referencia_pago = models.CharField(max_length=255, blank=True, null=True)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    comprobante = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pago #{self.id} - {self.metodo_pago} - {self.estado}"

# ===================================
# COMUNICACIÓN
# ===================================

class Comunicado(models.Model):
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    DESTINATARIOS_CHOICES = [
        ('todos', 'Todos'),
        ('propietarios', 'Propietarios'),
        ('residentes', 'Residentes'),
        ('personal', 'Personal'),
        ('unidades_especificas', 'Unidades Específicas'),
    ]

    titulo = models.CharField(max_length=255)
    contenido = models.TextField()
    autor = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='media')
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateField(blank=True, null=True)
    destinatarios = models.CharField(max_length=30, choices=DESTINATARIOS_CHOICES, default='todos')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.titulo} ({self.get_prioridad_display()})"


class ComunicadoUnidad(models.Model):
    comunicado = models.ForeignKey('Comunicado', on_delete=models.CASCADE)
    unidad_habitacional = models.ForeignKey('UnidadHabitacional', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('comunicado', 'unidad_habitacional')

    def __str__(self):
        return f"Comunicado #{self.comunicado_id} -> {self.unidad_habitacional}"


class ComunicadoLeido(models.Model):
    comunicado = models.ForeignKey('Comunicado', on_delete=models.CASCADE)
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    fecha_leido = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('comunicado', 'usuario')

    def __str__(self):
        return f"{self.usuario} leyó {self.comunicado} el {self.fecha_leido}"

# ===================================
# NOTIFICACIONES
# ===================================

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('pago', 'Pago'),
        ('seguridad', 'Seguridad'),
        ('reserva', 'Reserva'),
        ('comunicado', 'Comunicado'),
        ('mantenimiento', 'Mantenimiento'),
        ('sistema', 'Sistema'),
    ]

    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
    ]

    titulo = models.CharField(max_length=255)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    fecha_envio = models.DateTimeField(auto_now_add=True)
    enviada = models.BooleanField(default=False)
    leida = models.BooleanField(default=False)

    usuario = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    unidad_habitacional = models.ForeignKey('UnidadHabitacional', on_delete=models.SET_NULL, null=True, blank=True)

    relacion_con_id = models.IntegerField(blank=True, null=True)
    tipo_relacion = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.tipo}"


class AreaComun(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    capacidad = models.IntegerField(blank=True, null=True)
    horario_apertura = models.TimeField(blank=True, null=True)
    horario_cierre = models.TimeField(blank=True, null=True)
    precio_por_hora = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reglas_uso = models.TextField(blank=True, null=True)
    requiere_aprobacion = models.BooleanField(default=False)
    condominio = models.ForeignKey('Condominio', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

class Reserva(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
    ]

    area_comun = models.ForeignKey('AreaComun', on_delete=models.CASCADE)
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    fecha_reserva = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    motivo = models.TextField(blank=True, null=True)
    numero_invitados = models.IntegerField(blank=True, null=True)
    factura = models.ForeignKey('Factura', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError("La hora de fin debe ser mayor que la hora de inicio.")

class CategoriaMantenimiento(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    condominio = models.ForeignKey('Condominio', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class SolicitudMantenimiento(models.Model):
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('asignado', 'Asignado'),
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    CREADOR_TIPO_CHOICES = [
        ('residente', 'Residente'),
        ('administracion', 'Administración'),
        ('sistema', 'Sistema'),
    ]

    unidad_habitacional = models.ForeignKey('UnidadHabitacional', on_delete=models.SET_NULL, null=True, blank=True)
    area_comun = models.ForeignKey('AreaComun', on_delete=models.SET_NULL, null=True, blank=True)
    categoria_mantenimiento = models.ForeignKey('CategoriaMantenimiento', on_delete=models.CASCADE)
    usuario_reporta = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_limite = models.DateField(blank=True, null=True)
    fecha_completado = models.DateTimeField(blank=True, null=True)
    creador_tipo = models.CharField(max_length=20, choices=CREADOR_TIPO_CHOICES, default='residente')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TareaMantenimiento(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    solicitud_mantenimiento = models.ForeignKey('SolicitudMantenimiento', on_delete=models.CASCADE)
    usuario_asignado = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_limite = models.DateField(blank=True, null=True)
    fecha_completado = models.DateTimeField(blank=True, null=True)
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    costo_real = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MantenimientoPreventivo(models.Model):
    categoria_mantenimiento = models.ForeignKey('CategoriaMantenimiento', on_delete=models.CASCADE)
    area_comun = models.ForeignKey('AreaComun', on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.TextField()
    periodicidad_dias = models.IntegerField()
    ultima_ejecucion = models.DateField(blank=True, null=True)
    proxima_ejecucion = models.DateField(blank=True, null=True)
    responsable = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# ===================================
# SEGURIDAD CON IA - MODELOS FALTANTES
# ===================================

class Vehiculo(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    placa = models.CharField(max_length=20, unique=True)
    marca = models.CharField(max_length=50, blank=True, null=True)
    modelo = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=30, blank=True, null=True)
    autorizado = models.BooleanField(default=True)
    datos_ocr = models.TextField(blank=True, null=True)  # Datos extraídos por OCR
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.placa} - {self.usuario.nombre}"


class RegistroAcceso(models.Model):
    TIPO_CHOICES = [
        ('peatonal', 'Peatonal'),
        ('vehicular', 'Vehicular'),
    ]
    
    DIRECCION_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
    ]
    
    METODO_CHOICES = [
        ('facial', 'Reconocimiento Facial'),
        ('tarjeta', 'Tarjeta'),
        ('manual', 'Manual'),
        ('placa', 'Lectura de Placa'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True)
    direccion = models.CharField(max_length=10, choices=DIRECCION_CHOICES)
    metodo = models.CharField(max_length=20, choices=METODO_CHOICES)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    foto_evidencia = models.TextField(blank=True, null=True)
    reconocimiento_exitoso = models.BooleanField(default=False)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_direccion_display()} - {self.get_metodo_display()} - {self.fecha_hora}"


class Visitante(models.Model):
    nombre = models.CharField(max_length=255)
    documento_identidad = models.CharField(max_length=50, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    motivo_visita = models.TextField(blank=True, null=True)
    anfitrion = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha_entrada = models.DateTimeField(auto_now_add=True)
    fecha_salida = models.DateTimeField(null=True, blank=True)
    foto_entrada = models.TextField(blank=True, null=True)
    foto_salida = models.TextField(blank=True, null=True)
    placa_vehiculo = models.CharField(max_length=20, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} - {self.anfitrion.nombre}"


class IncidenteSeguridad(models.Model):
    TIPO_CHOICES = [
        ('persona_no_autorizada', 'Persona No Autorizada'),
        ('vehiculo_no_autorizado', 'Vehículo No Autorizado'),
        ('comportamiento_sospechoso', 'Comportamiento Sospechoso'),
        ('acceso_no_autorizado', 'Acceso No Autorizado'),
        ('mascota_suelta', 'Mascota Suelta'),
        ('vehiculo_mal_estacionado', 'Vehículo Mal Estacionado'),
        ('zona_restringida', 'Zona Restringida'),
    ]
    
    GRAVEDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('investigando', 'Investigando'),
        ('resuelto', 'Resuelto'),
        ('falso_positivo', 'Falso Positivo'),
    ]

    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    descripcion = models.TextField()
    ubicacion = models.CharField(max_length=255, blank=True, null=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    gravedad = models.CharField(max_length=10, choices=GRAVEDAD_CHOICES, default='media')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    evidencia_foto = models.TextField(blank=True, null=True)
    evidencia_video = models.TextField(blank=True, null=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    usuario_reporta = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidentes_reportados')
    usuario_asignado = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidentes_asignados')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.fecha_hora}"

"""
class ModeloIA(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('entrenando', 'Entrenando'),
        ('error', 'Error'),
    ]

    nombre = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    precision = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    fecha_entrenamiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='inactivo')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} v{self.version}"

class PrediccionMorosidad(models.Model):
    unidad_habitacional = models.ForeignKey(UnidadHabitacional, on_delete=models.CASCADE)
    modelo_ia = models.ForeignKey(ModeloIA, on_delete=models.CASCADE)
    score_morosidad = models.DecimalField(max_digits=5, decimal_places=4)
    fecha_prediccion = models.DateField()
    periodo_predicho = models.DateField()  # Mes/Año predicho (usar día 01)
    variables_utilizadas = models.TextField(blank=True, null=True)  # JSON como TEXT
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Predicción {self.unidad_habitacional} - {self.score_morosidad}"

class ConfiguracionSistema(models.Model):
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.clave} - {self.condominio.nombre}"
"""

class Bitacora(models.Model):  # Nombre simplificado como solicitaste
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=100)
    modulo = models.CharField(max_length=50)
    detalles = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        usuario_nombre = self.usuario.nombre if self.usuario else "Sistema"
        return f"{usuario_nombre} - {self.accion} - {self.created_at}"

class CamaraSeguridad(models.Model):
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255)
    url_stream = models.URLField(blank=True, null=True)
    tipo_camara = models.CharField(max_length=50, choices=[
        ('entrada_principal', 'Entrada Principal'),
        ('estacionamiento', 'Estacionamiento'),
        ('area_comun', 'Área Común'),
        ('perimetral', 'Perimetral')
    ], default='area_comun')
    esta_activa = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} - {self.condominio.nombre}"