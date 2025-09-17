from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

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

    propietario_actual = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL,
        related_name='propiedades',
        blank=True, null=True
    )
    residente_actual = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL,
        related_name='residencias',
        blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.codigo} - {self.condominio.nombre}"

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

    unidad_habitacional = models.ForeignKey(
        UnidadHabitacional, on_delete=models.SET_NULL,
        blank=True, null=True
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
    leido = models.BooleanField(default=False)

    class Meta:
        unique_together = ('comunicado', 'unidad_habitacional')

    def __str__(self):
        return f"Comunicado #{self.comunicado_id} -> {self.unidad_habitacional}"


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