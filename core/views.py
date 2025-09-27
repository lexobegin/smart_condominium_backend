from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet

from rest_framework.permissions import IsAuthenticated

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken  # si usas JWT

from rest_framework import viewsets, filters

from rest_framework.decorators import api_view, permission_classes, action
from django.db.models import Prefetch
from datetime import date, datetime, timedelta 

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

    @action(detail=False, methods=['get'], url_path='todos')
    def listar_todos(self, request):
        condominios = self.get_queryset()
        serializer = self.get_serializer(condominios, many=True)
        return Response(serializer.data)

class UnidadHabitacionalViewSet(ModelViewSet):
    queryset = UnidadHabitacional.objects.all()
    serializer_class = UnidadHabitacionalSerializer
    permission_classes = [IsAuthenticated]

class UsuarioUnidadViewSet(viewsets.ModelViewSet):
    queryset = UsuarioUnidad.objects.select_related('usuario', 'unidad', 'unidad__condominio')
    serializer_class = UsuarioUnidadSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [filters.SearchFilter]
    search_fields = [
        'usuario__nombre', 'usuario__email', 
        'unidad__codigo', 'unidad__condominio__nombre'
    ]

# Endpoint útil para gestión de relaciones
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def gestionar_unidades_usuario(request, usuario_id=None):
    """
    Gestiona las unidades de un usuario específico
    """
    if request.method == 'GET':
        relaciones = UsuarioUnidad.objects.filter(usuario_id=usuario_id)
        serializer = UsuarioUnidadSerializer(relaciones, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['usuario'] = usuario_id
        serializer = UsuarioUnidadSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    queryset = AreaComun.objects.all().order_by('-id')
    serializer_class = AreaComunSerializer
    permission_classes = [IsAuthenticated]

    # Habilitar filtro de búsqueda
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'capacidad']

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
    queryset = CategoriaMantenimiento.objects.all().order_by('-id')
    serializer_class = CategoriaMantenimientoSerializer
    permission_classes = [IsAuthenticated]
    
    # Habilitar filtro de búsqueda
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'descripcion']

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
    
    # Habilitar filtro de búsqueda
    filter_backends = [filters.SearchFilter]
    search_fields = ['titulo', 'descripcion', 'prioridad','estado']

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
    
    # Habilitar filtro de búsqueda
    filter_backends = [filters.SearchFilter]
    search_fields = ['fecha_asignacion', 'fecha_completado', 'estado', 'solicitud_mantenimiento__titulo', 'usuario_asignado__nombre']

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
    
    # Habilitar filtro de búsqueda
    filter_backends = [filters.SearchFilter]
    search_fields = ['descripcion', 'periodicidad_dias', 'ultima_ejecucion', 'proxima_ejecucion', 'categoria_mantenimiento__nombre', 'responsable__nombre', 'area_comun__nombre']

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

# ===================================
# APIs PARA MOVIL
# ===================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consultar_cuotas_servicios(request):
    """
    Consulta las facturas (cuotas y servicios) del usuario autenticado
    """
    try:
        usuario = request.user
        
        if not hasattr(usuario, 'unidad_habitacional') or not usuario.unidad_habitacional:
            return Response(
                {"error": "No tiene unidad habitacional asignada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        unidad = usuario.unidad_habitacional
        
        # Consultar facturas de los últimos 6 meses con pre-fetch de pagos
        hoy = date.today()
        # Manejar correctamente el cambio de año al restar meses
        if hoy.month > 6:
            seis_meses_atras = hoy.replace(month=hoy.month - 6)
        else:
            seis_meses_atras = hoy.replace(month=12 + (hoy.month - 6), year=hoy.year - 1)
        
        # Pre-cargar pagos para optimizar
        facturas = Factura.objects.filter(
            unidad_habitacional=unidad,
            fecha_emision__gte=seis_meses_atras
        ).select_related(
            'concepto_cobro', 'unidad_habitacional'
        ).prefetch_related(
            Prefetch('pago_set', queryset=Pago.objects.filter(estado='completado'))
        ).order_by('-fecha_emision', '-estado')
        
        # Agrupar por estado para facilitar el display en móvil
        facturas_pendientes = facturas.filter(estado__in=['pendiente', 'vencida'])
        facturas_pagadas = facturas.filter(estado='pagada')
        
        # Serializar
        serializer = FacturaSerializer(facturas, many=True)
        
        return Response({
            "pendientes": FacturaSerializer(facturas_pendientes, many=True).data,
            "pagadas": FacturaSerializer(facturas_pagadas, many=True).data,
            "total_pendiente": float(sum(f.monto for f in facturas_pendientes)),
            "total_pagado": float(sum(f.monto for f in facturas_pagadas))
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al consultar facturas: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===================================
# IA Y SEGURIDAD - VIEWS
# ===================================

class VehiculoViewSet(viewsets.ModelViewSet):
    queryset = Vehiculo.objects.select_related('usuario')
    serializer_class = VehiculoSerializer
    permission_classes = [IsAuthenticated]

class RegistroAccesoViewSet(viewsets.ModelViewSet):
    queryset = RegistroAcceso.objects.select_related('usuario', 'vehiculo').order_by('-fecha_hora')
    serializer_class = RegistroAccesoSerializer
    permission_classes = [IsAuthenticated]

class VisitanteViewSet(viewsets.ModelViewSet):
    queryset = Visitante.objects.select_related('anfitrion').order_by('-fecha_entrada')
    serializer_class = VisitanteSerializer
    permission_classes = [IsAuthenticated]

class IncidenteSeguridadViewSet(viewsets.ModelViewSet):
    queryset = IncidenteSeguridad.objects.select_related('usuario_reporta', 'usuario_asignado').order_by('-fecha_hora')
    serializer_class = IncidenteSeguridadSerializer
    permission_classes = [IsAuthenticated]

class BitacoraViewSet(viewsets.ModelViewSet):
    queryset = Bitacora.objects.select_related('usuario').order_by('-created_at')
    serializer_class = BitacoraSerializer
    permission_classes = [IsAuthenticated]

class CamaraSeguridadViewSet(viewsets.ModelViewSet):
    queryset = CamaraSeguridad.objects.select_related('condominio')
    serializer_class = CamaraSeguridadSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'ubicacion', 'tipo_camara']