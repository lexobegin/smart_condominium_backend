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
# SERIALIZERS BÁSICOS (Evitar dependencias circulares)
# ===============================

class UsuarioBasicoSerializer(serializers.ModelSerializer):
    """Serializer básico para Usuario (sin relaciones complejas)"""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'apellidos', 'email', 'tipo', 'tipo_display', 'telefono', 'foto_perfil']

class UnidadBasicaSerializer(serializers.ModelSerializer):
    """Serializer básico para UnidadHabitacional"""
    condominio_nombre = serializers.CharField(source='condominio.nombre', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = UnidadHabitacional
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'estado', 'estado_display', 'metros_cuadrados', 'condominio_nombre']

class CondominioBasicoSerializer(serializers.ModelSerializer):
    """Serializer básico para Condominio"""
    class Meta:
        model = Condominio
        fields = ['id', 'nombre', 'direccion', 'telefono', 'email']

# ===============================
# USUARIOS / ROLES / PERMISOS
# ===============================

# ===============================
# RELACIÓN USUARIO-UNIDAD
# ===============================

class UsuarioUnidadSerializer(serializers.ModelSerializer):
    usuario = UsuarioBasicoSerializer(read_only=True)
    unidad = UnidadBasicaSerializer(read_only=True)
    tipo_relacion_display = serializers.CharField(source='get_tipo_relacion_display', read_only=True)
    
    # Campos para escritura (IDs)
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(), 
        source='usuario', 
        write_only=True
    )
    unidad_id = serializers.PrimaryKeyRelatedField(
        queryset=UnidadHabitacional.objects.all(), 
        source='unidad', 
        write_only=True
    )
    
    class Meta:
        model = UsuarioUnidad
        fields = [
            'id', 'usuario', 'unidad', 'tipo_relacion', 'tipo_relacion_display',
            'fecha_inicio', 'fecha_fin', 'es_principal',
            'usuario_id', 'unidad_id'  # Campos de escritura
        ]
        read_only_fields = ['id']


class UsuarioSerializer(serializers.ModelSerializer):
    # Relaciones usando serializers básicos
    relaciones_unidades = UsuarioUnidadSerializer(source='usuariounidad_set', many=True, read_only=True)
    unidades_habitacionales = UnidadBasicaSerializer(many=True, read_only=True)

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
            'fecha_nacimiento', 'genero', 'telefono', 'tipo'
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

    # NUEVOS CAMPOS PARA LA APP MÓVIL
    pagos = serializers.SerializerMethodField()
    comprobante_url = serializers.SerializerMethodField()

    class Meta:
        model = Factura
        fields = '__all__'

    def get_pagos(self, obj):
        """Obtiene todos los pagos relacionados con esta factura"""
        pagos = Pago.objects.filter(factura=obj)
        return PagoSerializer(pagos, many=True).data
    
    def get_comprobante_url(self, obj):
        """Obtiene el comprobante del primer pago completado"""
        pago_completado = Pago.objects.filter(factura=obj, estado='completado').first()
        if pago_completado and pago_completado.comprobante:
            return pago_completado.comprobante
        return None


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
    condominio = CondominioSerializer(read_only=True)
    condominio_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominio.objects.all(), source='condominio', write_only=True
    )

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


# ===================================
# IA Y SEGURIDAD - SERIALIZERS
# ===================================

class VehiculoSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    
    class Meta:
        model = Vehiculo
        fields = '__all__'

class RegistroAccesoSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    vehiculo = VehiculoSerializer(read_only=True)
    
    class Meta:
        model = RegistroAcceso
        fields = '__all__'

class VisitanteSerializer(serializers.ModelSerializer):
    anfitrion = UsuarioSerializer(read_only=True)
    
    class Meta:
        model = Visitante
        fields = '__all__'

class IncidenteSeguridadSerializer(serializers.ModelSerializer):
    usuario_reporta = UsuarioSerializer(read_only=True)
    usuario_asignado = UsuarioSerializer(read_only=True)
    
    class Meta:
        model = IncidenteSeguridad
        fields = '__all__'


class BitacoraSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    
    class Meta:
        model = Bitacora
        fields = '__all__'

class CamaraSeguridadSerializer(serializers.ModelSerializer):
    condominio = CondominioBasicoSerializer(read_only=True)
    condominio_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominio.objects.all(),
        source='condominio',
        write_only=True
    )
    tipo_camara_display = serializers.CharField(source='get_tipo_camara_display', read_only=True)
    
    class Meta:
        model = CamaraSeguridad
        fields = '__all__'

"""
class ModeloIASerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeloIA
        fields = '__all__'

class PrediccionMorosidadSerializer(serializers.ModelSerializer):
    unidad_habitacional = UnidadHabitacionalSerializer(read_only=True)
    modelo_ia = ModeloIASerializer(read_only=True)
    
    class Meta:
        model = PrediccionMorosidad
        fields = '__all__'

class ConfiguracionSistemaSerializer(serializers.ModelSerializer):
    condominio = CondominioSerializer(read_only=True)
    
    class Meta:
        model = ConfiguracionSistema
        fields = '__all__'
"""
