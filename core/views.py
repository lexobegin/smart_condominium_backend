from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet

from rest_framework.permissions import IsAuthenticated

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken  # si usas JWT

from rest_framework import viewsets, filters

from .serializers import *
from .models import *

class UsuarioViewSet(ModelViewSet):
    queryset = Usuario.objects.all().order_by('-id')
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'apellidos']  # campos que quieres que se busquen

    def get_serializer_class(self):
        if self.action in ['create']:
            return UsuarioRegistroSerializer
        return UsuarioSerializer

class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Email y contraseña son requeridos'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, email=email, password=password)
        if not user:
            return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'error': 'Cuenta inactiva'}, status=status.HTTP_403_FORBIDDEN)

        # Si usas JWT
        refresh = RefreshToken.for_user(user)
        """return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'usuario': {
                'id': user.id,
                'nombre': user.nombre,
                'apellidos': user.apellidos,
                'email': user.email,
                'tipo': user.tipo,
                'roles': list(user.roles.values('id', 'nombre'))
            }
        })"""
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'usuario': UsuarioLoginSerializer(user).data
        })

class CondominioViewSet(ModelViewSet):
    queryset = Condominio.objects.all()
    serializer_class = CondominioSerializer
    permission_classes = [IsAuthenticated]

class UnidadHabitacionalViewSet(ModelViewSet):
    queryset = UnidadHabitacional.objects.all()
    serializer_class = UnidadHabitacionalSerializer
    permission_classes = [IsAuthenticated]

# ===================================
# FINANZAS
# ===================================

class ConceptoCobroViewSet(ModelViewSet):
    queryset = ConceptoCobro.objects.all()
    serializer_class = ConceptoCobroSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'tipo']
    ordering_fields = ['monto', 'aplica_desde', 'aplica_hasta']


class FacturaViewSet(ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['descripcion', 'estado']
    ordering_fields = ['fecha_emision', 'fecha_vencimiento', 'monto']


class PagoViewSet(ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['referencia_pago', 'estado', 'metodo_pago']
    ordering_fields = ['fecha_pago', 'monto']

# ===================================
# COMUNICACIÓN
# ===================================

class ComunicadoViewSet(ModelViewSet):
    queryset = Comunicado.objects.all()
    serializer_class = ComunicadoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['titulo', 'contenido', 'prioridad']
    ordering_fields = ['fecha_publicacion', 'prioridad']


class ComunicadoUnidadViewSet(ModelViewSet):
    queryset = ComunicadoUnidad.objects.all()
    serializer_class = ComunicadoUnidadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['comunicado', 'unidad_habitacional']

class ComunicadoLeidoViewSet(viewsets.ModelViewSet):
    queryset = ComunicadoLeido.objects.all()
    serializer_class = ComunicadoLeidoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        comunicado = serializer.validated_data['comunicado']
        usuario = self.request.user
        if ComunicadoLeido.objects.filter(comunicado=comunicado, usuario=usuario).exists():
            raise serializers.ValidationError("Este comunicado ya fue marcado como leído.")
        serializer.save(usuario=usuario)

# ===================================
# NOTIFICACIONES
# ===================================

class NotificacionViewSet(ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['titulo', 'mensaje', 'tipo', 'prioridad']
    ordering_fields = ['fecha_envio', 'prioridad', 'enviada', 'leida']


class AreaComunViewSet(viewsets.ModelViewSet):
    queryset = AreaComun.objects.all()
    serializer_class = AreaComunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrar por condominio si se proporciona
        condominio_id = self.request.query_params.get('condominio_id')
        if condominio_id:
            queryset = queryset.filter(condominio_id=condominio_id)
        return queryset

class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrar por usuario si es residente
        if not self.request.user.is_staff:
            queryset = queryset.filter(usuario=self.request.user)
        
        # Filtros adicionales
        area_comun_id = self.request.query_params.get('area_comun_id')
        estado = self.request.query_params.get('estado')
        fecha = self.request.query_params.get('fecha')
        
        if area_comun_id:
            queryset = queryset.filter(area_comun_id=area_comun_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        if fecha:
            queryset = queryset.filter(fecha_reserva=fecha)
            
        return queryset

class CategoriaMantenimientoViewSet(viewsets.ModelViewSet):
    queryset = CategoriaMantenimiento.objects.all()
    serializer_class = CategoriaMantenimientoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrar por condominio
        condominio_id = self.request.query_params.get('condominio_id')
        if condominio_id:
            queryset = queryset.filter(condominio_id=condominio_id)
        return queryset

class SolicitudMantenimientoViewSet(viewsets.ModelViewSet):
    queryset = SolicitudMantenimiento.objects.all()
    serializer_class = SolicitudMantenimientoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Para residentes, solo ver sus propias solicitudes
        if not self.request.user.is_staff:
            queryset = queryset.filter(usuario_reporta=self.request.user)
        
        # Filtros adicionales
        estado = self.request.query_params.get('estado')
        prioridad = self.request.query_params.get('prioridad')
        categoria_id = self.request.query_params.get('categoria_id')
        
        if estado:
            queryset = queryset.filter(estado=estado)
        if prioridad:
            queryset = queryset.filter(prioridad=prioridad)
        if categoria_id:
            queryset = queryset.filter(categoria_mantenimiento_id=categoria_id)
            
        return queryset

class TareaMantenimientoViewSet(viewsets.ModelViewSet):
    queryset = TareaMantenimiento.objects.all()
    serializer_class = TareaMantenimientoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Para técnicos, solo ver sus tareas asignadas
        if not self.request.user.is_staff:
            queryset = queryset.filter(usuario_asignado=self.request.user)
        
        # Filtros adicionales
        estado = self.request.query_params.get('estado')
        solicitud_id = self.request.query_params.get('solicitud_id')
        
        if estado:
            queryset = queryset.filter(estado=estado)
        if solicitud_id:
            queryset = queryset.filter(solicitud_mantenimiento_id=solicitud_id)
            
        return queryset

class MantenimientoPreventivoViewSet(viewsets.ModelViewSet):
    queryset = MantenimientoPreventivo.objects.all()
    serializer_class = MantenimientoPreventivoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        area_comun_id = self.request.query_params.get('area_comun_id')
        categoria_id = self.request.query_params.get('categoria_id')
        
        if area_comun_id:
            queryset = queryset.filter(area_comun_id=area_comun_id)
        if categoria_id:
            queryset = queryset.filter(categoria_mantenimiento_id=categoria_id)
            
        return queryset