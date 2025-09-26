# core_url.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *  # Incluye LoginView y (nuevo) LogoutView
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

    # Endpoints de autenticación JWT (se mantienen)
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # Nueva ruta para gestión de unidades por usuario
    path('usuarios/<int:usuario_id>/unidades/', gestionar_unidades_usuario, name='gestionar-unidades-usuario'),
    
    # MÓVIL (se mantiene)
    path('auth/login/', LoginView.as_view(), name='login'),

    # NUEVO: logout (registra en Bitácora)
    path('auth/logout/', LogoutView.as_view(), name='logout'),
]
