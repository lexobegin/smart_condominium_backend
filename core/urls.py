from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')
router.register(r'condominios', CondominioViewSet, basename='condominios')
router.register(r'unidades', UnidadHabitacionalViewSet, basename='unidades')

router.register('conceptos-cobro', ConceptoCobroViewSet)
router.register('facturas', FacturaViewSet)
router.register('pagos', PagoViewSet)
router.register('comunicados', ComunicadoViewSet)
router.register('comunicado-unidades', ComunicadoUnidadViewSet)
router.register('notificaciones', NotificacionViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # Endpoints de autenticación JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    
    path('auth/login/', LoginView.as_view(), name='login'),
]