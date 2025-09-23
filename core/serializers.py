from rest_framework import serializers
from .models import *

# ===============================
# CONDOMINIO / UNIDAD HABITACIONAL
# ===============================

class CondominioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condominio
        fields = '__all__'


class UnidadHabitacionalSerializer(serializers.ModelSerializer):
    """
    - Escritura: acepta 'condominio' como PrimaryKeyRelatedField (ID).
    - Lectura: devuelve 'condominio' como objeto anidado (CondominioSerializer),
      para no romper el front que usa u.condominio?.nombre.
    """
    # Para escritura: ID
    condominio = serializers.PrimaryKeyRelatedField(
        queryset=Condominio.objects.all()
    )

    class Meta:
        model = UnidadHabitacional
        fields = '__all__'

    # Para lectura: objeto anidado
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['condominio'] = CondominioSerializer(instance.condominio).data
        return rep


# ===============================
# USUARIOS / ROLES / PERMISOS
# ===============================

class UsuarioSerializer(serializers.ModelSerializer):
    unidad_habitacional = UnidadHabitacionalSerializer(read_only=True)
    genero_display = serializers.CharField(source='get_genero_display', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    roles = serializers.StringRelatedField(many=True, read_only=True)
    permisos = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Usuario
        exclude = ['password']
        read_only_fields = ['email', 'fecha_registro', 'is_active', 'is_staff']


class UsuarioRegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=6)

    class Meta:
        model = Usuario
        fields = [
            'email', 'password', 'nombre', 'apellidos', 'ci',
            'fecha_nacimiento', 'genero', 'telefono',
            'unidad_habitacional', 'tipo'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permiso
        fields = '__all__'


class RolSerializer(serializers.ModelSerializer):
    permisos = PermisoSerializer(many=True, source='permisos', read_only=True)

    class Meta:
        model = Rol
        fields = '__all__'


class UsuarioRolSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsuarioRol
        fields = ['usuario', 'rol']


class RolPermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolPermiso
        fields = ['rol', 'permiso']


class RolSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id', 'nombre']


class UsuarioLoginSerializer(serializers.ModelSerializer):
    roles = RolSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'apellidos', 'email', 'tipo', 'roles']


# ===============================
# FINANZAS
# ===============================

class ConceptoCobroSerializer(serializers.ModelSerializer):
    condominio = CondominioSerializer(read_only=True)
    condominio_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominio.objects.all(),
        source='condominio',
        write_only=True
    )

    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    periodicidad_display = serializers.CharField(source='get_periodicidad_display', read_only=True)

    class Meta:
        model = ConceptoCobro
        fields = '__all__'


class FacturaSerializer(serializers.ModelSerializer):
    unidad_habitacional = UnidadHabitacionalSerializer(read_only=True)
    unidad_habitacional_id = serializers.PrimaryKeyRelatedField(
        queryset=UnidadHabitacional.objects.all(),
        source='unidad_habitacional',
        write_only=True
    )

    concepto_cobro = ConceptoCobroSerializer(read_only=True)
    concepto_cobro_id = serializers.PrimaryKeyRelatedField(
        queryset=ConceptoCobro.objects.all(),
        source='concepto_cobro',
        write_only=True
    )

    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Factura
        fields = '__all__'


class PagoSerializer(serializers.ModelSerializer):
    factura = FacturaSerializer(read_only=True)
    factura_id = serializers.PrimaryKeyRelatedField(
        queryset=Factura.objects.all(),
        source='factura',
        write_only=True
    )

    metodo_pago_display = serializers.CharField(source='get_metodo_pago_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Pago
        fields = '__all__'


# ===============================
# COMUNICACIÓN
# ===============================

class ComunicadoSerializer(serializers.ModelSerializer):
    autor = UsuarioSerializer(read_only=True)
    autor_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        source='autor',
        write_only=True
    )

    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    destinatarios_display = serializers.CharField(source='get_destinatarios_display', read_only=True)

    class Meta:
        model = Comunicado
        fields = '__all__'


class ComunicadoUnidadSerializer(serializers.ModelSerializer):
    comunicado = ComunicadoSerializer(read_only=True)
    comunicado_id = serializers.PrimaryKeyRelatedField(
        queryset=Comunicado.objects.all(),
        source='comunicado',
        write_only=True
    )

    unidad_habitacional = UnidadHabitacionalSerializer(read_only=True)
    unidad_habitacional_id = serializers.PrimaryKeyRelatedField(
        queryset=UnidadHabitacional.objects.all(),
        source='unidad_habitacional',
        write_only=True
    )

    class Meta:
        model = ComunicadoUnidad
        fields = '__all__'


class ComunicadoLeidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComunicadoLeido
        fields = ['id', 'comunicado', 'usuario', 'fecha_leido']
        read_only_fields = ['fecha_leido']


# ===============================
# NOTIFICACIONES
# ===============================

class NotificacionSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        source='usuario',
        write_only=True,
        required=False,
        allow_null=True
    )

    unidad_habitacional = UnidadHabitacionalSerializer(read_only=True)
    unidad_habitacional_id = serializers.PrimaryKeyRelatedField(
        queryset=UnidadHabitacional.objects.all(),
        source='unidad_habitacional',
        write_only=True,
        required=False,
        allow_null=True
    )

    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)

    class Meta:
        model = Notificacion
        fields = '__all__'


# ===============================
# RESERVAS / MANTENIMIENTO
# ===============================

class AreaComunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaComun
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ReservaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserva
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, data):
        if data['hora_fin'] <= data['hora_inicio']:
            raise serializers.ValidationError("La hora de fin debe ser mayor que la hora de inicio.")
        return data


class CategoriaMantenimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaMantenimiento
        fields = '__all__'
        read_only_fields = ('created_at',)


class SolicitudMantenimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitudMantenimiento
        fields = '__all__'
        read_only_fields = ('fecha_reporte', 'created_at', 'updated_at')


class TareaMantenimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TareaMantenimiento
        fields = '__all__'
        read_only_fields = ('fecha_asignacion', 'created_at', 'updated_at')


class MantenimientoPreventivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MantenimientoPreventivo
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
