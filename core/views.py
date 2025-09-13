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
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'usuario': {
                'id': user.id,
                'nombre': user.nombre,
                'apellidos': user.apellidos,
                'email': user.email,
                'tipo': user.tipo,
                'roles': user.roles,
            }
        })

class CondominioViewSet(ModelViewSet):
    queryset = Condominio.objects.all()
    serializer_class = CondominioSerializer
    permission_classes = [IsAuthenticated]


class UnidadHabitacionalViewSet(ModelViewSet):
    queryset = UnidadHabitacional.objects.all()
    serializer_class = UnidadHabitacionalSerializer
    permission_classes = [IsAuthenticated]