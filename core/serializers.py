from rest_framework import serializers
from .models import *


class CondominioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condominio
        fields = '__all__'

class UnidadHabitacionalSerializer(serializers.ModelSerializer):
    condominio = CondominioSerializer(read_only=True)

    class Meta:
        model = UnidadHabitacional
        fields = '__all__'

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

class CondominioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condominio
        fields = '__all__'


class UnidadHabitacionalSerializer(serializers.ModelSerializer):
    condominio = CondominioSerializer(read_only=True)
    condominio_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominio.objects.all(),
        source='condominio',
        write_only=True
    )

    class Meta:
        model = UnidadHabitacional
        fields = '__all__'