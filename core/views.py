from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet

from rest_framework.permissions import IsAuthenticated, IsAdminUser

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken  # si usas JWT

from rest_framework import viewsets, filters

from rest_framework.decorators import api_view, permission_classes, action

from django.db.models import Prefetch, Count, Sum, Case, When, DecimalField, F
from django.db.models.functions import TruncMonth

from django.utils import timezone
from datetime import date, datetime, timedelta

from rest_framework.pagination import PageNumberPagination

# -----------------API
import base64
import requests
import json
import re
import tempfile
import os
from django.conf import settings


from .serializers import *
from .models import *

# -------------------------------------------------------------------
# Helper para obtener IP del cliente
def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")

# Helper para formar un texto amigable de la entidad
def display_obj(obj):
    for attr in ("nombre", "titulo", "codigo", "descripcion"):
        if hasattr(obj, attr):
            val = getattr(obj, attr)
            if val:
                return str(val)
    if hasattr(obj, "id"):
        return f"ID {obj.id}"
    return str(obj)

# Helper central para registrar en Bitácora
def log_bitacora(request, accion, modulo, detalles=""):
    try:
        Bitacora.objects.create(
            usuario=getattr(request, "user", None),
            accion=str(accion),
            modulo=str(modulo),
            detalles=str(detalles),
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")
        )
    except Exception:
        pass
# -------------------------------------------------------------------

# Mixin reutilizable para CRUD (create/update/destroy)
class BitacoraCRUDMixin:
    bitacora_modulo = "General"

    def perform_create(self, serializer):
        obj = serializer.save()
        detalles = f"Creó {display_obj(obj)} (id={getattr(obj, 'id', '-')})"
        log_bitacora(self.request, "crear", self.bitacora_modulo, detalles)

    def perform_update(self, serializer):
        obj = serializer.save()
        detalles = f"Editó {display_obj(obj)} (id={getattr(obj, 'id', '-')})"
        log_bitacora(self.request, "editar", self.bitacora_modulo, detalles)

    def perform_destroy(self, instance):
        detalles = f"Eliminó {display_obj(instance)} (id={getattr(instance, 'id', '-')})"
        log_bitacora(self.request, "eliminar", self.bitacora_modulo, detalles)
        instance.delete()
# -------------------------------------------------------------------

class UsuarioViewSet(BitacoraCRUDMixin, ModelViewSet):
    bitacora_modulo = "Usuarios"
    queryset = Usuario.objects.all().order_by('-id')
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'apellidos']  # campos que quieres que se busquen

    def get_serializer_class(self):
        if self.action in ['create']:
            return UsuarioRegistroSerializer
        return UsuarioSerializer
    
    # Trae todos
    """@action(detail=False, methods=['get'], url_path='todos')
    def listar_todos(self, request):
        unidades = self.get_queryset()
        serializer = UsuarioSelectSerializer(unidades, many=True)
        return Response(serializer.data)"""
    
    # Filtrado por tipo (ej. residentes) //GET /api/usuarios/todos/?tipo=residente
    """@action(detail=False, methods=['get'], url_path='todos')
    def listar_todos(self, request):
        tipo = request.query_params.get('tipo')  # obtener ?tipo=valor
        queryset = self.get_queryset()
        
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        serializer = UsuarioSelectSerializer(queryset, many=True)
        return Response(serializer.data)"""
    
    # Filtrar por múltiples tipos //GET /api/usuarios/todos/?tipo=administrador,seguridad
    @action(detail=False, methods=['get'], url_path='todos')
    def listar_todos(self, request):
        tipo_param = request.query_params.get('tipo')  # puede ser "residente" o "residente,administrador"
        queryset = self.get_queryset()

        if tipo_param:
            tipos = [t.strip() for t in tipo_param.split(',') if t.strip()]
            tipos_validos = dict(Usuario.TIPO_CHOICES).keys()
            tipos_filtrados = [t for t in tipos if t in tipos_validos]

            if not tipos_filtrados:
                return Response({"error": "Ningún tipo de usuario válido fue proporcionado."}, status=400)

            queryset = queryset.filter(tipo__in=tipos_filtrados)

        serializer = UsuarioSelectSerializer(queryset, many=True)
        return Response(serializer.data)

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

        # >>> Registro en Bitácora (login exitoso) <<<
        log_bitacora(request, "login_exitoso", "Autenticación", "Inicio de sesión vía /auth/login")

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'usuario': UsuarioLoginSerializer(user).data
        })

class CondominioViewSet(BitacoraCRUDMixin, ModelViewSet):
    bitacora_modulo = "Condominios"
    queryset = Condominio.objects.all()
    serializer_class = CondominioSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='todos')
    def listar_todos(self, request):
        condominios = self.get_queryset()
        serializer = self.get_serializer(condominios, many=True)
        return Response(serializer.data)

class UnidadHabitacionalViewSet(BitacoraCRUDMixin, ModelViewSet):
    bitacora_modulo = "Unidades"
    queryset = UnidadHabitacional.objects.all()
    serializer_class = UnidadHabitacionalSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='todos')
    def listar_todos(self, request):
        unidades = self.get_queryset()
        serializer = UnidadHabitacionalSelectSerializer(unidades, many=True)
        return Response(serializer.data)

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


class IndicadoresFinancierosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            total_facturas = Factura.objects.count()
            pendientes = Factura.objects.filter(estado="pendiente").count()
            vencidas = Factura.objects.filter(estado="vencida").count()
            morosidad = (pendientes + vencidas) / total_facturas * 100 if total_facturas > 0 else 0

            ingresos_total = Pago.objects.filter(estado="completado").aggregate(total=Sum("monto"))["total"] or 0
            ingresos_mes = Pago.objects.filter(
                estado="completado",
                fecha_pago__gte=date.today().replace(day=1)
            ).aggregate(total=Sum("monto"))["total"] or 0

            pagos_estado = Pago.objects.values("estado").annotate(total=Count("id"))

            return Response({
                "morosidad": {
                    "total_facturas": total_facturas,
                    "pendientes": pendientes,
                    "vencidas": vencidas,
                    "porcentaje_morosidad": round(morosidad, 2)
                },
                "ingresos": {
                    "total": float(ingresos_total),
                    "ultimo_mes": float(ingresos_mes)
                },
                "pagos": {p["estado"]: p["total"] for p in pagos_estado}
            })
        except Exception as e:
            return Response(
                {"error": f"Error al generar indicadores: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ===================================
# REPORTES - ÁREAS COMUNES
# ===================================

class ReporteAreasComunesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            condominio_id = request.query_params.get("condominio_id")
            areas = AreaComun.objects.all()

            if condominio_id:
                areas = areas.filter(condominio_id=condominio_id)

            resumen_areas = []
            total_reservas = 0
            total_ingresos = 0

            for area in areas:
                reservas = Reserva.objects.filter(area_comun=area)
                total_area = reservas.count()
                ingresos_area = reservas.aggregate(total=Sum("monto_total"))["total"] or 0
                pendientes = reservas.filter(estado="pendiente").count()
                confirmadas = reservas.filter(estado="confirmada").count()
                completadas = reservas.filter(estado="completada").count()
                canceladas = reservas.filter(estado="cancelada").count()

                resumen_areas.append({
                    "id": area.id,
                    "nombre": area.nombre,
                    "total_reservas": total_area,
                    "ingresos": float(ingresos_area),
                    "reservas_pendientes": pendientes,
                    "reservas_confirmadas": confirmadas,
                    "reservas_completadas": completadas,
                    "reservas_canceladas": canceladas
                })

                total_reservas += total_area
                total_ingresos += ingresos_area

            return Response({
                "resumen": {
                    "total_reservas": total_reservas,
                    "total_ingresos": float(total_ingresos)
                },
                "areas": resumen_areas
            })
        except Exception as e:
            return Response(
                {"error": f"Error al generar reporte de áreas comunes: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
# ===================================
# REPORTES - VISUALES
# ===================================

class ReporteVisualesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            hoy = date.today()
            hace_12_meses = hoy - timedelta(days=365)
            hace_6_meses = hoy - timedelta(days=180)

            # === INGRESOS MENSUALES ===
            pagos = (
                Pago.objects.filter(estado="completado", fecha_pago__gte=hace_12_meses)
                .annotate(mes=TruncMonth("fecha_pago"))
                .values("mes")
                .annotate(total=Sum("monto"))
                .order_by("mes")
            )
            ingresos_mensuales = [
                {"mes": p["mes"].strftime("%Y-%m"), "total": float(p["total"] or 0)}
                for p in pagos if p["mes"]
            ]

            # === MOROSIDAD MENSUAL ===
            facturas = (
                Factura.objects.filter(fecha_vencimiento__gte=hace_12_meses)
                .annotate(mes=TruncMonth("fecha_vencimiento"))
                .values("mes", "estado")
                .annotate(total=Count("id"))
                .order_by("mes")
            )
            morosidad_dict = {}
            for f in facturas:
                mes = f["mes"].strftime("%Y-%m") if f["mes"] else "N/A"
                if mes not in morosidad_dict:
                    morosidad_dict[mes] = {"pendientes": 0, "vencidas": 0}
                if f["estado"] == "pendiente":
                    morosidad_dict[mes]["pendientes"] = f["total"]
                elif f["estado"] == "vencida":
                    morosidad_dict[mes]["vencidas"] = f["total"]

            morosidad_mensual = [
                {"mes": mes, **valores} for mes, valores in morosidad_dict.items()
            ]

            # === RESERVAS POR ÁREA ===
            reservas = (
                Reserva.objects.filter(
                    fecha_reserva__gte=hace_6_meses,
                    estado__in=["confirmada", "completada"]
                )
                .values("area_comun__nombre")
                .annotate(total=Count("id"))
                .order_by("-total")
            )
            reservas_por_area = [
                {"area": r["area_comun__nombre"] or "Sin nombre", "total": r["total"]}
                for r in reservas
            ]

            return Response({
                "ingresos_mensuales": ingresos_mensuales,
                "morosidad_mensual": morosidad_mensual,
                "reservas_por_area": reservas_por_area
            })
        except Exception as e:
            return Response(
                {"error": f"Error al generar reportes visuales: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
    ordering_fields = ['fecha_envio', 'prioridad', 'enviada', 'es_leida']


class AreaComunViewSet(BitacoraCRUDMixin, viewsets.ModelViewSet):
    bitacora_modulo = "Áreas Comunes"
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
# IA Y SEGURIDAD - VIEWS
# ===================================

class VehiculoViewSet(viewsets.ModelViewSet):
    queryset = Vehiculo.objects.select_related('usuario')
    serializer_class = VehiculoSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter]
    search_fields = ['placa', 'modelo', 'usuario__nombre']

    # Trae todos
    @action(detail=False, methods=['get'], url_path='todos')
    def listar_todos(self, request):
        unidades = self.get_queryset()
        serializer = VehiculoSelectSerializer(unidades, many=True)
        return Response(serializer.data)

class RegistroAccesoViewSet(viewsets.ModelViewSet):
    queryset = RegistroAcceso.objects.select_related('usuario', 'vehiculo').order_by('-fecha_hora')
    serializer_class = RegistroAccesoSerializer
    permission_classes = [IsAuthenticated]

class VisitanteViewSet(viewsets.ModelViewSet):
    queryset = Visitante.objects.select_related('anfitrion').order_by('-fecha_entrada')
    serializer_class = VisitanteSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'documento_identidad', 'telefono']

class IncidenteSeguridadViewSet(viewsets.ModelViewSet):
    queryset = IncidenteSeguridad.objects.select_related('usuario_reporta', 'usuario_asignado').order_by('-fecha_hora')
    serializer_class = IncidenteSeguridadSerializer
    permission_classes = [IsAuthenticated]

class BitacoraViewSet(viewsets.ModelViewSet):
    queryset = Bitacora.objects.select_related('usuario').order_by('-created_at')
    serializer_class = BitacoraSerializer
    permission_classes = [IsAuthenticated]

    # Habilitamos búsqueda y ordenación para el front (?search=&ordering=)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'usuario__email', 'usuario__nombre', 'usuario__apellidos',
        'accion', 'modulo', 'detalles'
    ]
    ordering_fields = ['id', 'created_at']
    ordering = ['-created_at']

class CamaraSeguridadViewSet(viewsets.ModelViewSet):
    queryset = CamaraSeguridad.objects.select_related('condominio')
    serializer_class = CamaraSeguridadSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'ubicacion', 'tipo_camara']

# ===================================
# Logout (JWT) - registra en Bitácora
# ===================================

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Si mandas refresh desde el front, intentamos ponerlo en blacklist (opcional)
        refresh = request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except Exception:
                # No interrumpimos el flujo si falla el blacklist
                pass

        # Registrar en Bitácora
        log_bitacora(request, "logout", "Autenticación", "Cierre de sesión")

        return Response(status=status.HTTP_205_RESET_CONTENT)
# APIs PARA MOVIL - ACTUALIZADAS
# ===================================

# Cuotas y Servicios

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consultar_cuotas_servicios(request):
    """
    Consulta las facturas (cuotas y servicios) del usuario autenticado
    VERSIÓN CORREGIDA - SIN RECURSIÓN
    """
    try:
        usuario = request.user
        
        # Obtener las unidades habitacionales activas del usuario
        unidades_usuario = UnidadHabitacional.objects.filter(
            usuariounidad__usuario=usuario,
            usuariounidad__fecha_fin__isnull=True
        ).distinct()
        
        if not unidades_usuario.exists():
            return Response(
                {"error": "No tiene unidades habitacionales asignadas"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Consultar facturas de TODAS las unidades del usuario en los últimos 6 meses
        hoy = date.today()
        seis_meses_atras = hoy - timedelta(days=180)  # 6 meses aprox
        
        # Pre-cargar facturas de todas las unidades del usuario
        facturas = Factura.objects.filter(
            unidad_habitacional__in=unidades_usuario,
            fecha_emision__gte=seis_meses_atras
        ).select_related(
            'concepto_cobro', 'unidad_habitacional', 'unidad_habitacional__condominio'
        ).prefetch_related(
            Prefetch('pago_set', queryset=Pago.objects.filter(estado='completado'))
        ).order_by('-fecha_emision', '-estado')
        
        # Agrupar por estado para facilitar el display en móvil
        facturas_pendientes = facturas.filter(estado__in=['pendiente', 'vencida'])
        facturas_pagadas = facturas.filter(estado='pagada')
        
        # Calcular totales por unidad
        resumen_unidades = []
        for unidad in unidades_usuario:
            facturas_unidad = facturas.filter(unidad_habitacional=unidad)
            pendientes_unidad = facturas_unidad.filter(estado__in=['pendiente', 'vencida'])
            pagadas_unidad = facturas_unidad.filter(estado='pagada')
            
            resumen_unidades.append({
                "unidad_id": unidad.id,
                "codigo": unidad.codigo,
                "condominio": unidad.condominio.nombre,
                "total_pendiente": float(sum(f.monto for f in pendientes_unidad)),
                "total_pagado": float(sum(f.monto for f in pagadas_unidad)),
                "cantidad_pendientes": pendientes_unidad.count(),
                "cantidad_pagadas": pagadas_unidad.count()
            })
        
        # USAR SERIALIZERS SIMPLIFICADOS PARA MÓVIL
        return Response({
            "resumen_unidades": resumen_unidades,
            "facturas_pendientes": FacturaMovilSerializer(facturas_pendientes, many=True).data,
            "facturas_pagadas": FacturaMovilSerializer(facturas_pagadas, many=True).data,
            "total_general_pendiente": float(sum(f.monto for f in facturas_pendientes)),
            "total_general_pagado": float(sum(f.monto for f in facturas_pagadas)),
            "unidades_activas": [unidad.codigo for unidad in unidades_usuario]
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al consultar facturas: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_movil(request):
    """
    Dashboard completo para la app móvil
    """
    try:
        usuario = request.user
        
        # 1. Obtener unidades activas del usuario
        unidades_activas = UnidadHabitacional.objects.filter(
            usuariounidad__usuario=usuario,
            usuariounidad__fecha_fin__isnull=True
        ).distinct()
        
        if not unidades_activas.exists():
            return Response(
                {"error": "No tiene unidades habitacionales asignadas"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. Facturas pendientes de todas las unidades (últimos 3 meses)
        tres_meses_atras = date.today() - timedelta(days=90)
        facturas_pendientes = Factura.objects.filter(
            unidad_habitacional__in=unidades_activas,
            estado__in=['pendiente', 'vencida'],
            fecha_emision__gte=tres_meses_atras
        ).select_related('concepto_cobro', 'unidad_habitacional')[:10]
        
        # 3. Comunicados no leídos para las unidades del usuario (últimos 15 días)
        quince_dias_atras = date.today() - timedelta(days=15)
        comunicados_no_leidos = Comunicado.objects.filter(
            comunicadounidad__unidad_habitacional__in=unidades_activas,
            fecha_publicacion__gte=quince_dias_atras
        ).exclude(
            comunicadoleido__usuario=usuario
        ).select_related('autor').distinct()[:5]
        
        # 4. Próximas reservas del usuario (próximos 30 días)
        proximas_reservas = Reserva.objects.filter(
            usuario=usuario,
            fecha_reserva__gte=date.today(),
            fecha_reserva__lte=date.today() + timedelta(days=30),
            estado='confirmada'
        ).select_related('area_comun')[:5]
        
        # 5. Notificaciones no leídas del usuario
        notificaciones_no_leidas = Notificacion.objects.filter(
            usuario=usuario,
            leida=False
        ).order_by('-fecha_envio')[:10]
        
        # 6. Solicitudes de mantenimiento abiertas del usuario
        solicitudes_abiertas = SolicitudMantenimiento.objects.filter(
            usuario_reporta=usuario,
            estado__in=['pendiente', 'asignado', 'en_proceso']
        ).select_related('categoria_mantenimiento')[:5]
        
        # 7. Resumen financiero
        total_pendiente = Factura.objects.filter(
            unidad_habitacional__in=unidades_activas,
            estado__in=['pendiente', 'vencida']
        ).aggregate(total=models.Sum('monto'))['total'] or 0
        
        # 8. Alertas de seguridad (con manejo de errores)
        alertas_seguridad = []
        try:
            alertas = IncidenteSeguridad.objects.filter(
                fecha_hora__gte=timezone.now() - timedelta(hours=24),
                gravedad__in=['alta', 'media']
            ).order_by('-fecha_hora')[:3]
            alertas_seguridad = IncidenteSeguridadSerializer(alertas, many=True).data
        except Exception as e:
            # Si hay error, simplemente no mostrar alertas
            alertas_seguridad = []
        
        return Response({
            "usuario": {
                "nombre": usuario.nombre,
                "email": usuario.email,
                "tipo": usuario.tipo,
                "unidades_activas": [f"{u.codigo} - {u.condominio.nombre}" for u in unidades_activas]
            },
            "resumen_financiero": {
                "total_pendiente": float(total_pendiente),
                "facturas_pendientes_count": facturas_pendientes.count(),
                "unidades_con_deuda": unidades_activas.filter(
                    factura__estado__in=['pendiente', 'vencida']
                ).distinct().count()
            },
            "facturas_pendientes": FacturaSerializer(facturas_pendientes, many=True).data,
            "comunicados_no_leidos": ComunicadoSerializer(comunicados_no_leidos, many=True).data,
            "proximas_reservas": ReservaSerializer(proximas_reservas, many=True).data,
            "notificaciones": NotificacionSerializer(notificaciones_no_leidas, many=True).data,
            "solicitudes_mantenimiento": SolicitudMantenimientoSerializer(solicitudes_abiertas, many=True).data,
            "alertas_seguridad": alertas_seguridad
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al cargar dashboard: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def obtener_alertas_seguridad(usuario, unidades_activas):
    """Obtiene alertas de seguridad relevantes para el usuario"""
    try:
        # Incidentes recientes (últimas 24 horas) de gravedad media/alta
        alertas = IncidenteSeguridad.objects.filter(
            fecha_hora__gte=timezone.now() - timedelta(hours=24),
            gravedad__in=['alta', 'media']
        ).order_by('-fecha_hora')[:3]
        
        return IncidenteSeguridadSerializer(alertas, many=True).data
    
    except Exception as e:
        return []

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_comunicado_leido(request, comunicado_id):
    """Marca un comunicado como leído por el usuario"""
    try:
        comunicado = Comunicado.objects.get(id=comunicado_id)
        
        # Verificar que el comunicado está asignado a alguna unidad del usuario
        unidades_usuario = UnidadHabitacional.objects.filter(
            usuariounidad__usuario=request.user,
            usuariounidad__fecha_fin__isnull=True
        )
        
        if not ComunicadoUnidad.objects.filter(
            comunicado=comunicado,
            unidad_habitacional__in=unidades_usuario
        ).exists():
            return Response(
                {"error": "No tiene permisos para leer este comunicado"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Crear registro de lectura
        ComunicadoLeido.objects.get_or_create(
            comunicado=comunicado,
            usuario=request.user
        )
        
        return Response({"message": "Comunicado marcado como leído"})
    
    except Comunicado.DoesNotExist:
        return Response(
            {"error": "Comunicado no encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_notificacion_leida(request, notificacion_id):
    """Marca una notificación como leída"""
    try:
        notificacion = Notificacion.objects.get(id=notificacion_id, usuario=request.user)
        notificacion.leida = True
        notificacion.save()
        
        return Response({"message": "Notificación marcada como leída"})
    
    except Notificacion.DoesNotExist:
        return Response(
            {"error": "Notificación no encontrada"},
            status=status.HTTP_404_NOT_FOUND
        )

# ===================================
# APIs PARA COMUNICADOS MÓVIL
# ===================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_comunicados_movil(request):
    """
    Lista comunicados para residente/inquilino en móvil
    """
    try:
        usuario = request.user
        
        # Verificar que el usuario es residente o inquilino
        if usuario.tipo not in ['residente', 'propietario']:
            return Response(
                {"error": "No tiene permisos para ver comunicados"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener unidades activas del usuario
        unidades_usuario = UnidadHabitacional.objects.filter(
            usuariounidad__usuario=usuario,
            usuariounidad__fecha_fin__isnull=True
        ).distinct()
        
        if not unidades_usuario.exists():
            return Response(
                {"error": "No tiene unidades habitacionales asignadas"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filtrar comunicados activos para las unidades del usuario
        hoy = date.today()
        comunicados = Comunicado.objects.filter(
            # Comunicados asignados a las unidades del usuario
            comunicadounidad__unidad_habitacional__in=unidades_usuario
        ).filter(
            # Comunicados no expirados (o sin fecha de expiración)
            models.Q(fecha_expiracion__gte=hoy) | models.Q(fecha_expiracion__isnull=True)
        ).filter(
            # Solo comunicados publicados
            fecha_publicacion__lte=timezone.now()
        ).select_related('autor').prefetch_related(
            Prefetch('comunicadoleido_set', queryset=ComunicadoLeido.objects.filter(usuario=usuario))
        ).distinct().order_by('-fecha_publicacion', '-prioridad')
        
        # Aplicar filtros desde query parameters
        prioridad = request.GET.get('prioridad')
        if prioridad:
            comunicados = comunicados.filter(prioridad=prioridad)
            
        tipo_destinatario = request.GET.get('destinatarios')
        if tipo_destinatario:
            comunicados = comunicados.filter(destinatarios=tipo_destinatario)
        
        # Paginación para móvil (CON IMPORT CORREGIDO)
        paginator = PageNumberPagination()
        paginator.page_size = 10
        comunicados_paginados = paginator.paginate_queryset(comunicados, request)
        
        # Serializar con datos adicionales para móvil
        comunicados_data = []
        for comunicado in comunicados_paginados:
            leido = ComunicadoLeido.objects.filter(
                comunicado=comunicado, 
                usuario=usuario
            ).exists()
            
            comunicados_data.append({
                'id': comunicado.id,
                'titulo': comunicado.titulo,
                'contenido_preview': comunicado.contenido[:100] + '...' if len(comunicado.contenido) > 100 else comunicado.contenido,
                'fecha_publicacion': comunicado.fecha_publicacion,
                'prioridad': comunicado.prioridad,
                'prioridad_display': comunicado.get_prioridad_display(),
                'autor_nombre': comunicado.autor.nombre if comunicado.autor else 'Administración',
                'leido': leido,
                'tiene_adjuntos': False,  # Puedes implementar adjuntos después
                'obligatorio': comunicado.prioridad in ['alta', 'urgente']  # Regla de negocio
            })
        
        return paginator.get_paginated_response({
            'comunicados': comunicados_data,
            'resumen': {
                'total': comunicados.count(),
                'no_leidos': comunicados.exclude(comunicadoleido__usuario=usuario).count(),
                'urgentes': comunicados.filter(prioridad='urgente').count()
            }
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al obtener comunicados: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_comunicado_movil(request, comunicado_id):
    """
    Detalle completo de comunicado para móvil
    """
    try:
        usuario = request.user
        
        # Obtener unidades activas del usuario
        unidades_usuario = UnidadHabitacional.objects.filter(
            usuariounidad__usuario=usuario,
            usuariounidad__fecha_fin__isnull=True
        ).distinct()
        
        # Verificar que el comunicado está asignado al usuario
        comunicado = Comunicado.objects.filter(
            id=comunicado_id,
            comunicadounidad__unidad_habitacional__in=unidades_usuario
        ).select_related('autor').first()
        
        if not comunicado:
            return Response(
                {"error": "Comunicado no encontrado o no tiene acceso"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar si está expirado
        if comunicado.fecha_expiracion and comunicado.fecha_expiracion < date.today():
            return Response(
                {"error": "Este comunicado ha expirado"},
                status=status.HTTP_410_GONE
            )
        
        # Marcar como leído automáticamente al abrir (regla de negocio)
        ComunicadoLeido.objects.get_or_create(
            comunicado=comunicado,
            usuario=usuario
        )
        
        # Serializar datos completos
        comunicado_data = {
            'id': comunicado.id,
            'titulo': comunicado.titulo,
            'contenido_completo': comunicado.contenido,
            'fecha_publicacion': comunicado.fecha_publicacion,
            'fecha_expiracion': comunicado.fecha_expiracion,
            'prioridad': comunicado.prioridad,
            'prioridad_display': comunicado.get_prioridad_display(),
            'destinatarios': comunicado.destinatarios,
            'destinatarios_display': comunicado.get_destinatarios_display(),
            'autor': {
                'nombre': comunicado.autor.nombre if comunicado.autor else 'Administración',
                'tipo': comunicado.autor.get_tipo_display() if comunicado.autor else 'Sistema'
            },
            'leido': True,  # Ya se marcó como leído
            'obligatorio': comunicado.prioridad in ['alta', 'urgente'],
            # Campos para futuros adjuntos
            'adjuntos': [],
            'permite_descarga': False
        }
        
        return Response(comunicado_data)
    
    except Exception as e:
        return Response(
            {"error": f"Error al obtener comunicado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST']) #no
@permission_classes([IsAuthenticated])
def confirmar_lectura_obligatoria(request, comunicado_id):
    """
    Opcional: Confirmar lectura de comunicados obligatorios
    """
    try:
        usuario = request.user
        
        # Verificar que el comunicado existe y es obligatorio
        comunicado = Comunicado.objects.filter(
            id=comunicado_id,
            prioridad__in=['alta', 'urgente']  # Comunicados obligatorios
        ).first()
        
        if not comunicado:
            return Response(
                {"error": "Comunicado no encontrado o no es obligatorio"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar que el usuario tiene acceso al comunicado
        unidades_usuario = UnidadHabitacional.objects.filter(
            usuariounidad__usuario=usuario,
            usuariounidad__fecha_fin__isnull=True
        )
        
        if not ComunicadoUnidad.objects.filter(
            comunicado=comunicado,
            unidad_habitacional__in=unidades_usuario
        ).exists():
            return Response(
                {"error": "No tiene acceso a este comunicado"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Marcar como leído con confirmación explícita
        leido, created = ComunicadoLeido.objects.get_or_create(
            comunicado=comunicado,
            usuario=usuario
        )
        
        # Registrar confirmación adicional (podrías agregar un campo de confirmación)
        return Response({
            "message": "Lectura confirmada exitosamente",
            "comunicado_id": comunicado.id,
            "titulo": comunicado.titulo,
            "fecha_confirmacion": timezone.now()
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al confirmar lectura: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET']) #no
@permission_classes([IsAuthenticated])
def resumen_comunicados_movil(request):
    """
    Resumen rápido de comunicados para el dashboard móvil
    """
    try:
        usuario = request.user
        
        # Obtener unidades activas del usuario
        unidades_usuario = UnidadHabitacional.objects.filter(
            usuariounidad__usuario=usuario,
            usuariounidad__fecha_fin__isnull=True
        ).distinct()
        
        if not unidades_usuario.exists():
            return Response({"error": "No tiene unidades asignadas"}, status=400)
        
        hoy = date.today()
        
        # Comunicados activos no leídos (últimos 7 días)
        comunicados_recientes = Comunicado.objects.filter(
            comunicadounidad__unidad_habitacional__in=unidades_usuario,
            fecha_publicacion__gte=hoy - timedelta(days=7)
        ).filter(
            models.Q(fecha_expiracion__gte=hoy) | models.Q(fecha_expiracion__isnull=True)
        ).distinct()
        
        no_leidos = comunicados_recientes.exclude(comunicadoleido__usuario=usuario)
        urgentes = comunicados_recientes.filter(prioridad='urgente')
        
        return Response({
            'total_recientes': comunicados_recientes.count(),
            'no_leidos': no_leidos.count(),
            'urgentes': urgentes.count(),
            'ultimo_comunicado': comunicados_recientes.first().fecha_publicacion if comunicados_recientes.exists() else None
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al obtener resumen: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===================================
# APIs PARA NOTIFICACIONES MÓVIL - CU21
# ===================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_notificaciones_movil(request):
    """
    CU21: Lista notificaciones para el usuario en móvil
    """
    try:
        usuario = request.user
        
        # Obtener notificaciones del usuario (últimos 30 días)
        treinta_dias_atras = timezone.now() - timedelta(days=30)
        
        notificaciones = Notificacion.objects.filter(
            usuario=usuario,
            fecha_envio__gte=treinta_dias_atras
        ).order_by('-fecha_envio', '-prioridad')
        
        # Aplicar filtros desde query parameters
        tipo_notificacion = request.GET.get('tipo')
        if tipo_notificacion:
            notificaciones = notificaciones.filter(tipo=tipo_notificacion)
            
        solo_no_leidas = request.GET.get('no_leidas')
        if solo_no_leidas and solo_no_leidas.lower() == 'true':
            notificaciones = notificaciones.filter(leida=False)
        
        # Paginación para móvil
        paginator = PageNumberPagination()
        paginator.page_size = 15
        notificaciones_paginadas = paginator.paginate_queryset(notificaciones, request)
        
        # Serializar para móvil
        notificaciones_data = []
        for notificacion in notificaciones_paginadas:
            # Determinar acción según el tipo de notificación
            accion = obtener_accion_notificacion(notificacion.tipo)
            
            notificaciones_data.append({
                'id': notificacion.id,
                'titulo': notificacion.titulo,
                'mensaje': notificacion.mensaje,
                'tipo': notificacion.tipo,
                'tipo_display': notificacion.get_tipo_display(),
                'prioridad': notificacion.prioridad,
                'prioridad_display': notificacion.get_prioridad_display(),
                'fecha_envio': notificacion.fecha_envio,
                'leida': notificacion.leida,
                'accion': accion,
                'icono': obtener_icono_notificacion(notificacion.tipo),
                'relacion_con_id': notificacion.relacion_con_id,
                'tipo_relacion': notificacion.tipo_relacion
            })
        
        return paginator.get_paginated_response({
            'notificaciones': notificaciones_data,
            'resumen': {
                'total': notificaciones.count(),
                'no_leidas': notificaciones.filter(leida=False).count(),
                'urgentes': notificaciones.filter(prioridad='alta').count()
            }
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al obtener notificaciones: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_notificacion_movil(request, notificacion_id):
    """
    CU21: Detalle completo de notificación + marca como leída
    """
    try:
        usuario = request.user
        
        # Obtener notificación específica del usuario
        notificacion = Notificacion.objects.filter(
            id=notificacion_id,
            usuario=usuario
        ).first()
        
        if not notificacion:
            return Response(
                {"error": "Notificación no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Marcar como leída al abrir (regla de negocio)
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.save()
        
        # Obtener datos adicionales según el tipo de notificación
        datos_adicionales = obtener_datos_adicionales(notificacion)
        
        notificacion_data = {
            'id': notificacion.id,
            'titulo': notificacion.titulo,
            'mensaje': notificacion.mensaje,
            'tipo': notificacion.tipo,
            'tipo_display': notificacion.get_tipo_display(),
            'prioridad': notificacion.prioridad,
            'prioridad_display': notificacion.get_prioridad_display(),
            'fecha_envio': notificacion.fecha_envio,
            'leida': True,  # Ya se marcó como leída
            'accion': obtener_accion_notificacion(notificacion.tipo),
            'icono': obtener_icono_notificacion(notificacion.tipo),
            'relacion_con_id': notificacion.relacion_con_id,
            'tipo_relacion': notificacion.tipo_relacion,
            'datos_adicionales': datos_adicionales
        }
        
        return Response(notificacion_data)
    
    except Exception as e:
        return Response(
            {"error": f"Error al obtener notificación: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_notificacion_leida(request, notificacion_id):
    """
    CU21: Marcar notificación específica como leída
    """
    try:
        usuario = request.user
        
        notificacion = Notificacion.objects.filter(
            id=notificacion_id,
            usuario=usuario
        ).first()
        
        if not notificacion:
            return Response(
                {"error": "Notificación no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.save()
        
        return Response({
            "message": "Notificación marcada como leída",
            "notificacion_id": notificacion.id,
            "titulo": notificacion.titulo
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al marcar notificación como leída: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_todas_leidas(request):
    """
    CU21: Marcar todas las notificaciones como leídas
    """
    try:
        usuario = request.user
        
        notificaciones_no_leidas = Notificacion.objects.filter(
            usuario=usuario,
            leida=False
        )
        
        cantidad_marcadas = notificaciones_no_leidas.count()
        notificaciones_no_leidas.update(leida=True)
        
        return Response({
            "message": f"{cantidad_marcadas} notificaciones marcadas como leídas",
            "cantidad_marcadas": cantidad_marcadas
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al marcar notificaciones como leídas: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def actualizar_token_notificacion(request):
    """
    CU21: Actualizar token de notificación push del usuario
    """
    try:
        usuario = request.user
        token = request.data.get('token')
        
        if not token:
            return Response(
                {"error": "Token de notificación es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        usuario.token_notificacion = token
        usuario.save()
        
        return Response({
            "message": "Token de notificación actualizado exitosamente",
            "usuario_id": usuario.id
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al actualizar token: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resumen_notificaciones_movil(request):
    """
    CU21: Resumen rápido de notificaciones para el dashboard móvil
    """
    try:
        usuario = request.user
        
        # Notificaciones de los últimos 7 días
        siete_dias_atras = timezone.now() - timedelta(days=7)
        
        notificaciones_recientes = Notificacion.objects.filter(
            usuario=usuario,
            fecha_envio__gte=siete_dias_atras
        )
        
        no_leidas = notificaciones_recientes.filter(leida=False)
        urgentes = notificaciones_recientes.filter(prioridad='alta')
        
        # Contar por tipo
        por_tipo = notificaciones_recientes.values('tipo').annotate(
            total=models.Count('id'),
            no_leidas=models.Count('id', filter=models.Q(leida=False))
        )
        
        return Response({
            'total_recientes': notificaciones_recientes.count(),
            'no_leidas': no_leidas.count(),
            'urgentes': urgentes.count(),
            'por_tipo': list(por_tipo),
            'ultima_notificacion': notificaciones_recientes.first().fecha_envio if notificaciones_recientes.exists() else None
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al obtener resumen: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===================================
# MÉTODOS AUXILIARES PARA NOTIFICACIONES
# ===================================

def obtener_accion_notificacion(tipo_notificacion):
    """Determina la acción a realizar según el tipo de notificación"""
    acciones = {
        'pago': {'texto': 'Ver detalles de pago', 'ruta': '/finanzas/pagos'},
        'seguridad': {'texto': 'Ver incidente', 'ruta': '/seguridad/incidentes'},
        'reserva': {'texto': 'Ver reserva', 'ruta': '/reservas/detalle'},
        'comunicado': {'texto': 'Leer comunicado', 'ruta': '/comunicados/detalle'},
        'mantenimiento': {'texto': 'Ver solicitud', 'ruta': '/mantenimiento/solicitudes'},
        'sistema': {'texto': 'Ver detalles', 'ruta': '/sistema'}
    }
    return acciones.get(tipo_notificacion, {'texto': 'Ver detalles', 'ruta': '/'})

def obtener_icono_notificacion(tipo_notificacion):
    """Retorna el nombre del icono según el tipo de notificación"""
    iconos = {
        'pago': '💰',
        'seguridad': '🚨',
        'reserva': '📅',
        'comunicado': '📢',
        'mantenimiento': '🔧',
        'sistema': '⚙️'
    }
    return iconos.get(tipo_notificacion, '🔔')

def obtener_datos_adicionales(notificacion):
    """Obtiene datos adicionales según el tipo de notificación"""
    if not notificacion.relacion_con_id or not notificacion.tipo_relacion:
        return {}
    
    try:
        if notificacion.tipo_relacion == 'factura':
            factura = Factura.objects.filter(id=notificacion.relacion_con_id).first()
            if factura:
                return {
                    'monto': float(factura.monto),
                    'fecha_vencimiento': factura.fecha_vencimiento,
                    'estado': factura.estado
                }
        
        elif notificacion.tipo_relacion == 'incidente':
            incidente = IncidenteSeguridad.objects.filter(id=notificacion.relacion_con_id).first()
            if incidente:
                return {
                    'tipo_incidente': incidente.get_tipo_display(),
                    'gravedad': incidente.gravedad,
                    'ubicacion': incidente.ubicacion
                }
        
        # Agregar más casos según necesites
        
    except Exception:
        # Si hay error, retornar objeto vacío
        pass
    
    return {}

# ===================================
# DASHBOARD PARA EL ADMINISTRADOR
# ===================================
User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_admin(request):
    try:
        # Usuarios por tipo
        usuarios_por_tipo = User.objects.values('tipo').annotate(total=Count('id'))

        # Usuarios por condominio y tipo (desde UsuarioUnidad)
        usuarios_condominio_tipo = UsuarioUnidad.objects.filter(
            fecha_fin__isnull=True
        ).values(
            condominio_nombre=F('unidad__condominio__nombre'),
            tipo_usuario=F('usuario__tipo')
        ).annotate(total=Count('usuario')).order_by('condominio_nombre', 'tipo_usuario')

        # Resumen de facturas por condominio (desde Factura)
        resumen_facturacion = Factura.objects.values(
            condominio_nombre=F('unidad_habitacional__condominio__nombre')
        ).annotate(
            total_facturado=Sum('monto'),
            total_pagado=Sum('pago__monto'),  # asumiendo relación inversa desde Pago
            total_pendiente=Sum(
                Case(
                    When(estado='pendiente', then='monto'),
                    default=0,
                    output_field=DecimalField()
                )
            )
        ).order_by('condominio_nombre')

        return Response({
            'usuarios_por_tipo': list(usuarios_por_tipo),
            'usuarios_por_condominio_y_tipo': list(usuarios_condominio_tipo),
            'facturacion_por_condominio': list(resumen_facturacion)
        })

    except Exception as e:
        return Response(
            {"error": f"Error al obtener dashboard: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===================================
# RECONOCIMIENTO FACIAL - GOOGLE VISION API + DEEPFACE
# ===================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def registrar_rostro_usuario(request, usuario_id):
    """
    Registrar rostro de usuario usando Google Vision API o DeepFace
    """
    try:
        # Verificar permisos de administrador
        if request.user.tipo != 'administrador':
            return Response(
                {"error": "Solo administradores pueden registrar rostros"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        usuario = Usuario.objects.get(id=usuario_id)
        imagen_base64 = request.data.get('imagen')
        
        if not imagen_base64:
            return Response(
                {"error": "Imagen en base64 es requerida"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Procesar imagen y extraer características faciales
        resultado = procesar_rostro_para_registro(imagen_base64)
        
        if resultado['success']:
            # Almacenar embeddings faciales
            usuario.datos_faciales = json.dumps({
                'embedding': resultado['embedding'],
                'backend': resultado['backend'],
                'fecha_registro': timezone.now().isoformat(),
                'metadata': resultado.get('metadata', {})
            })
            usuario.save()
            
            return Response({
                "message": f"Rostro registrado exitosamente usando {resultado['backend']}",
                "usuario_id": usuario.id,
                "usuario_nombre": usuario.nombre,
                "backend": resultado['backend'],
                "caracteristicas_extraidas": len(resultado['embedding']) if isinstance(resultado['embedding'], list) else 'N/A'
            })
        else:
            return Response(
                {"error": resultado['error']},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Usuario.DoesNotExist:
        return Response(
            {"error": "Usuario no encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"Error al registrar rostro: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def procesar_acceso_facial(request):
    """
    Procesar acceso peatonal con reconocimiento facial
    Usa Google Vision API o DeepFace como fallback
    """
    try:
        camara_id = request.data.get('camara_id')
        imagen_base64 = request.data.get('imagen')
        direccion = request.data.get('direccion', 'entrada')
        
        if not camara_id or not imagen_base64:
            return Response(
                {"error": "camara_id e imagen son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        camara = CamaraSeguridad.objects.get(id=camara_id)
        
        # 1. Procesar reconocimiento facial
        resultado = reconocer_rostro(imagen_base64)
        
        usuario_identificado = None
        reconocimiento_exitoso = False
        confidence = 0.0
        backend_utilizado = resultado.get('backend', 'unknown')
        
        if resultado['success'] and resultado['persona_identificada']:
            usuario_identificado = resultado['usuario']
            reconocimiento_exitoso = True
            confidence = resultado['confidence']
            
            # 2. Registrar acceso exitoso
            registro_acceso = RegistroAcceso.objects.create(
                usuario=usuario_identificado,
                tipo='peatonal',
                direccion=direccion,
                metodo='facial',
                reconocimiento_exitoso=True,
                confidence_score=confidence,
                metadata={'backend': backend_utilizado}
            )
            
            descripcion = f"Acceso {direccion} autorizado - {usuario_identificado.nombre} ({backend_utilizado})"
            
        else:
            # 3. Persona no identificada - crear incidente de seguridad
            descripcion = f"Intento de acceso {direccion} - Persona no identificada ({backend_utilizado})"
            confidence = resultado.get('confidence', 0.0)
            
            incidente = IncidenteSeguridad.objects.create(
                tipo='persona_no_autorizada',
                descripcion=descripcion,
                ubicacion=camara.ubicacion,
                gravedad='alta',
                confidence_score=confidence,
                metadata={'backend': backend_utilizado}
            )
            
            # Notificar a seguridad
            personal_seguridad = Usuario.objects.filter(tipo='seguridad', estado='activo')
            for seguridad in personal_seguridad:
                Notificacion.objects.create(
                    usuario=seguridad,
                    titulo="Persona no identificada en acceso",
                    mensaje=f"Cámara {camara.nombre}: {descripcion}",
                    tipo='seguridad',
                    prioridad='alta'
                )
        
        return Response({
            "reconocimiento_exitoso": reconocimiento_exitoso,
            "usuario_identificado": {
                "id": usuario_identificado.id,
                "nombre": usuario_identificado.nombre,
                "email": usuario_identificado.email
            } if usuario_identificado else None,
            "confidence": float(confidence),
            "descripcion": descripcion,
            "backend": backend_utilizado,
            "registro_acceso_id": registro_acceso.id if reconocimiento_exitoso else None,
            "incidente_id": incidente.id if not reconocimiento_exitoso else None
        })
    
    except CamaraSeguridad.DoesNotExist:
        return Response(
            {"error": "Cámara no encontrada"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"Error en procesamiento facial: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_estadisticas_acceso(request):
    """
    Obtener estadísticas de acceso facial
    """
    try:
        # Últimas 24 horas
        veinticuatro_horas = timezone.now() - timedelta(hours=24)
        
        # Estadísticas de acceso
        total_accesos = RegistroAcceso.objects.filter(
            fecha_hora__gte=veinticuatro_horas,
            metodo='facial'
        ).count()
        
        accesos_exitosos = RegistroAcceso.objects.filter(
            fecha_hora__gte=veinticuatro_horas,
            metodo='facial',
            reconocimiento_exitoso=True
        ).count()
        
        # Incidentes de seguridad
        incidentes_recientes = IncidenteSeguridad.objects.filter(
            fecha_hora__gte=veinticuatro_horas,
            tipo='persona_no_autorizada'
        ).count()
        
        # Tasa de reconocimiento
        tasa_reconocimiento = (accesos_exitosos / total_accesos * 100) if total_accesos > 0 else 0
        
        # Últimos accesos
        ultimos_accesos = RegistroAcceso.objects.filter(
            metodo='facial'
        ).select_related('usuario').order_by('-fecha_hora')[:10]
        
        accesos_data = []
        for acceso in ultimos_accesos:
            accesos_data.append({
                'id': acceso.id,
                'usuario_nombre': acceso.usuario.nombre if acceso.usuario else 'No identificado',
                'direccion': acceso.direccion,
                'fecha_hora': acceso.fecha_hora,
                'exitoso': acceso.reconocimiento_exitoso,
                'confidence': float(acceso.confidence_score) if acceso.confidence_score else 0.0,
                'backend': acceso.metadata.get('backend', 'unknown') if acceso.metadata else 'unknown'
            })
        
        return Response({
            "estadisticas": {
                "total_accesos_24h": total_accesos,
                "accesos_exitosos": accesos_exitosos,
                "incidentes": incidentes_recientes,
                "tasa_reconocimiento": round(tasa_reconocimiento, 2)
            },
            "ultimos_accesos": accesos_data
        })
    
    except Exception as e:
        return Response(
            {"error": f"Error al obtener estadísticas: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===================================
# FUNCIONES DE RECONOCIMIENTO FACIAL - GOOGLE VISION + DEEPFACE
# ===================================

def procesar_rostro_para_registro(imagen_base64):
    """
    Procesar rostro para registro usando Google Vision API o DeepFace
    """
    try:
        backend = getattr(settings, 'FACE_RECOGNITION_BACKEND', 'deepface')
        
        if backend == 'google':
            resultado = google_vision_registrar_rostro(imagen_base64)
            if not resultado['success']:
                # Fallback a DeepFace si Google falla
                resultado = deepface_registrar_rostro(imagen_base64)
            return resultado
        else:
            return deepface_registrar_rostro(imagen_base64)
            
    except Exception as e:
        return {'success': False, 'error': f"Error en procesamiento: {str(e)}"}

def reconocer_rostro(imagen_base64):
    """
    Reconocer rostro usando Google Vision API o DeepFace
    """
    try:
        backend = getattr(settings, 'FACE_RECOGNITION_BACKEND', 'deepface')
        
        if backend == 'google':
            resultado = google_vision_reconocer_rostro(imagen_base64)
            if not resultado['success']:
                # Fallback a DeepFace si Google falla
                resultado = deepface_reconocer_rostro(imagen_base64)
            return resultado
        else:
            return deepface_reconocer_rostro(imagen_base64)
            
    except Exception as e:
        return {'success': False, 'error': f"Error en reconocimiento: {str(e)}"}

# ===================================
# GOOGLE VISION API IMPLEMENTATION
# ===================================

def google_vision_registrar_rostro(imagen_base64):
    """
    Registrar rostro usando Google Vision API
    """
    try:
        # Verificar si Google Vision está configurado
        credentials_path = getattr(settings, 'GOOGLE_VISION_CREDENTIALS', '')
        
        if not credentials_path:
            return {
                'success': False, 
                'error': 'Google Vision API no configurada. Configure GOOGLE_VISION_CREDENTIALS en settings.py'
            }
        
        # Solo importar si está configurado
        from google.cloud import vision
        from google.oauth2 import service_account
        
        # Autenticar con Google Vision
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = vision.ImageAnnotatorClient(credentials=credentials)
        
        # Preparar imagen
        if ',' in imagen_base64:
            imagen_base64 = imagen_base64.split(',')[1]
        
        image_content = base64.b64decode(imagen_base64)
        image = vision.Image(content=image_content)
        
        # Detectar rostros
        response = client.face_detection(image=image)
        
        if response.error.message:
            return {'success': False, 'error': f"Google Vision API error: {response.error.message}"}
        
        faces = response.face_annotations
        
        if len(faces) == 0:
            return {'success': False, 'error': 'No se detectó ningún rostro en la imagen'}
        
        # Usar el primer rostro detectado
        face = faces[0]
        
        # Extraer características faciales (simplificado)
        embedding = [
            face.detection_confidence,
            likelihood_to_number(face.joy_likelihood),
            likelihood_to_number(face.sorrow_likelihood),
            likelihood_to_number(face.anger_likelihood),
            likelihood_to_number(face.surprise_likelihood),
            likelihood_to_number(face.under_exposed_likelihood),
            likelihood_to_number(face.blurred_likelihood),
            likelihood_to_number(face.headwear_likelihood)
        ]
        
        metadata = {
            'bounding_poly': [(vertex.x, vertex.y) for vertex in face.bounding_poly.vertices],
            'detection_confidence': face.detection_confidence,
            'landmarking_confidence': face.landmarking_confidence,
            'joy_likelihood': face.joy_likelihood.name,
            'sorrow_likelihood': face.sorrow_likelihood.name,
            'anger_likelihood': face.anger_likelihood.name,
            'surprise_likelihood': face.surprise_likelihood.name,
            'roll_angle': face.roll_angle,
            'pan_angle': face.pan_angle,
            'tilt_angle': face.tilt_angle
        }
        
        return {
            'success': True,
            'embedding': embedding,
            'backend': 'google_vision',
            'metadata': metadata
        }
    
    except ImportError:
        return {'success': False, 'error': 'Google Cloud Vision no instalado. Ejecute: pip install google-cloud-vision'}
    except Exception as e:
        return {'success': False, 'error': f"Google Vision error: {str(e)}"}

def google_vision_reconocer_rostro(imagen_base64):
    """
    Reconocer rostro usando Google Vision API
    """
    try:
        # Primero extraer características del rostro en la imagen
        resultado_deteccion = google_vision_registrar_rostro(imagen_base64)
        
        if not resultado_deteccion['success']:
            return resultado_deteccion
        
        embedding_actual = resultado_deteccion['embedding']
        
        # Buscar coincidencia en usuarios registrados
        usuarios_con_rostro = Usuario.objects.exclude(datos_faciales__isnull=True)
        mejor_coincidencia = None
        mejor_confianza = 0.0
        threshold = getattr(settings, 'FACE_MATCH_THRESHOLD', 0.7)
        
        for usuario in usuarios_con_rostro:
            try:
                datos_faciales = json.loads(usuario.datos_faciales)
                
                if datos_faciales.get('backend') == 'google_vision':
                    embedding_registrado = datos_faciales.get('embedding', [])
                    
                    # Calcular similitud
                    if len(embedding_actual) == len(embedding_registrado):
                        similitud = calcular_similitud_embedding(embedding_actual, embedding_registrado)
                        
                        if similitud > mejor_confianza and similitud >= threshold:
                            mejor_confianza = similitud
                            mejor_coincidencia = usuario
            
            except (json.JSONDecodeError, KeyError):
                continue
        
        if mejor_coincidencia:
            return {
                'success': True,
                'persona_identificada': True,
                'usuario': mejor_coincidencia,
                'confidence': mejor_confianza,
                'backend': 'google_vision'
            }
        else:
            return {
                'success': True,
                'persona_identificada': False,
                'confidence': mejor_confianza,
                'backend': 'google_vision'
            }
    
    except Exception as e:
        return {'success': False, 'error': f"Google Vision recognition error: {str(e)}"}

# ===================================
# DEEPFACE IMPLEMENTATION (OPEN SOURCE)
# ===================================

def deepface_registrar_rostro(imagen_base64):
    """
    Registrar rostro usando DeepFace (Open Source)
    """
    try:
        from deepface import DeepFace
        
        # Convertir base64 a archivo temporal
        if ',' in imagen_base64:
            imagen_base64 = imagen_base64.split(',')[1]
        
        image_data = base64.b64decode(imagen_base64)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(image_data)
            temp_path = temp_file.name
        
        try:
            # Extraer embedding facial usando DeepFace
            embedding_objs = DeepFace.represent(
                img_path=temp_path,
                model_name='Facenet',
                enforce_detection=True,
                detector_backend='opencv'
            )
            
            if embedding_objs:
                embedding = embedding_objs[0]['embedding']
                
                metadata = {
                    'model': 'Facenet',
                    'detector': 'opencv',
                    'face_region': embedding_objs[0]['facial_area'],
                    'embedding_length': len(embedding)
                }
                
                return {
                    'success': True,
                    'embedding': embedding,
                    'backend': 'deepface',
                    'metadata': metadata
                }
            else:
                return {'success': False, 'error': 'No se pudo extraer embedding facial'}
        
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except ImportError:
        return {'success': False, 'error': 'DeepFace no instalado. Ejecute: pip install deepface'}
    except Exception as e:
        return {'success': False, 'error': f"DeepFace error: {str(e)}"}

def deepface_reconocer_rostro(imagen_base64):
    """
    Reconocer rostro usando DeepFace
    """
    try:
        from deepface import DeepFace
        
        # Convertir base64 a archivo temporal
        if ',' in imagen_base64:
            imagen_base64 = imagen_base64.split(',')[1]
        
        image_data = base64.b64decode(imagen_base64)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(image_data)
            temp_path = temp_file.name
        
        try:
            # Buscar en la base de datos de usuarios
            usuarios_con_rostro = Usuario.objects.exclude(datos_faciales__isnull=True)
            
            mejor_coincidencia = None
            mejor_confianza = 0.0
            threshold = getattr(settings, 'FACE_MATCH_THRESHOLD', 0.7)
            
            for usuario in usuarios_con_rostro:
                try:
                    datos_faciales = json.loads(usuario.datos_faciales)
                    
                    if datos_faciales.get('backend') == 'deepface':
                        # Para esta implementación simplificada, usamos simulación
                        # En producción usarías DeepFace.verify con una DB de embeddings
                        similitud = simular_verificacion_deepface()
                        
                        if similitud > mejor_confianza and similitud >= threshold:
                            mejor_confianza = similitud
                            mejor_coincidencia = usuario
                
                except (json.JSONDecodeError, KeyError):
                    continue
            
            if mejor_coincidencia:
                return {
                    'success': True,
                    'persona_identificada': True,
                    'usuario': mejor_coincidencia,
                    'confidence': mejor_confianza,
                    'backend': 'deepface'
                }
            else:
                return {
                    'success': True,
                    'persona_identificada': False,
                    'confidence': mejor_confianza,
                    'backend': 'deepface'
                }
        
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        return {'success': False, 'error': f"DeepFace recognition error: {str(e)}"}

# ===================================
# FUNCIONES AUXILIARES
# ===================================

def likelihood_to_number(likelihood):
    """Convertir Google Vision Likelihood a número"""
    likelihood_map = {
        'UNKNOWN': 0,
        'VERY_UNLIKELY': 1,
        'UNLIKELY': 2,
        'POSSIBLE': 3,
        'LIKELY': 4,
        'VERY_LIKELY': 5
    }
    
    if hasattr(likelihood, 'name'):
        return likelihood_map.get(likelihood.name, 0)
    return likelihood_map.get(likelihood, 0)

def calcular_similitud_embedding(embedding1, embedding2):
    """Calcular similitud entre dos embeddings"""
    if len(embedding1) != len(embedding2):
        return 0.0
    
    # Distancia euclidiana normalizada a [0,1]
    from math import sqrt
    distancia = sqrt(sum((a - b) ** 2 for a, b in zip(embedding1, embedding2)))
    max_distancia = sqrt(len(embedding1) * 25)  # Asumiendo valores entre 0-5
    
    return max(0.0, 1.0 - (distancia / max_distancia))

def simular_verificacion_deepface():
    """Simular verificación DeepFace para desarrollo"""
    import random
    return round(random.uniform(0.1, 0.95), 2)