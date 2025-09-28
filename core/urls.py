# core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *  # Incluye LoginView, LogoutView y los nuevos endpoints de reportes
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)

router = DefaultRouter()

# Ciclo 1
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')
router.register(r'condominios', CondominioViewSet, basename='condominios')
router.register(r'unidades', UnidadHabitacionalViewSet, basename='unidades')
router.register('conceptos-cobro', ConceptoCobroViewSet)
router.register('facturas', FacturaViewSet)
router.register('comunicados', ComunicadoViewSet)
router.register('comunicado-unidades', ComunicadoUnidadViewSet)
router.register(r'comunicados-leidos', ComunicadoLeidoViewSet, basename='comunicado-leido')
router.register('notificaciones', NotificacionViewSet)

# Ciclo 2
router.register(r'areas-comunes', AreaComunViewSet)
router.register(r'reservas', ReservaViewSet)
router.register(r'categorias-mantenimiento', CategoriaMantenimientoViewSet)
router.register(r'solicitudes-mantenimiento', SolicitudMantenimientoViewSet)
router.register(r'tareas-mantenimiento', TareaMantenimientoViewSet)
router.register(r'mantenimiento-preventivo', MantenimientoPreventivoViewSet)
router.register('pagos', PagoViewSet)

# Ciclo 3
router.register(r'vehiculos', VehiculoViewSet)
router.register(r'registros-acceso', RegistroAccesoViewSet)
router.register(r'visitantes', VisitanteViewSet)
router.register(r'incidentes-seguridad', IncidenteSeguridadViewSet)
router.register(r'bitacora', BitacoraViewSet)

router.register(r'camaras-seguridad', CamaraSeguridadViewSet)
router.register(r'usuario-unidades', UsuarioUnidadViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # Endpoints de autenticación JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # Nueva ruta para gestión de unidades por usuario
    path('usuarios/<int:usuario_id>/unidades/', gestionar_unidades_usuario, name='gestionar-unidades-usuario'),

    # Autenticación
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # === NUEVOS ENDPOINTS DE REPORTES ===
    path('reportes/financieros/', IndicadoresFinancierosView.as_view(), name='indicadores-financieros'),
    path('reportes/areas-comunes/', ReporteAreasComunesView.as_view(), name='reporte-areas-comunes'),
    path('reportes/visuales/', ReporteVisualesView.as_view(), name='reporte-visuales'),

    # Endpoints MÓVIL
    path('movil/dashboard/', dashboard_movil, name='movil_dashboard'),
    path('movil/cuotas-servicios/', consultar_cuotas_servicios, name='movil_consultar_cuotas'),

    # COMUNICADOS MÓVIL
    path('movil/comunicados/', listar_comunicados_movil, name='movil_comunicados_lista'),
    path('movil/comunicados/<int:comunicado_id>/', detalle_comunicado_movil, name='movil_comunicados_detalle'),
    path('movil/comunicados/<int:comunicado_id>/leer/', marcar_comunicado_leido, name='marcar_comunicado_leido'),
    path('movil/comunicados/<int:comunicado_id>/confirmar/', confirmar_lectura_obligatoria, name='movil_comunicados_confirmar'),
    path('movil/comunicados/resumen/', resumen_comunicados_movil, name='movil_comunicados_resumen'),

    # NOTIFICACIONES MÓVIL
    path('movil/notificaciones/', listar_notificaciones_movil, name='movil_notificaciones_lista'),
    path('movil/notificaciones/<int:notificacion_id>/', detalle_notificacion_movil, name='movil_notificaciones_detalle'),
    path('movil/notificaciones/<int:notificacion_id>/leer/', marcar_notificacion_leida, name='movil_notificaciones_leer'),
    path('movil/notificaciones/leer-todas/', marcar_todas_leidas, name='movil_notificaciones_leer_todas'),
    path('movil/notificaciones/actualizar-token/', actualizar_token_notificacion, name='movil_notificaciones_actualizar_token'),
    path('movil/notificaciones/resumen/', resumen_notificaciones_movil, name='movil_notificaciones_resumen'),
]
