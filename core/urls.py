from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
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

urlpatterns = [
    path('', include(router.urls)),

    # Endpoints de autenticación JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    
    # MOVIL
    path('auth/login/', LoginView.as_view(), name='login'),
    path('cuotas-servicios/', consultar_cuotas_servicios, name='movil_consultar_cuotas'),
]