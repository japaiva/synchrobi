# core/models/usuario.py - MODELO DE USUÁRIO

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class Usuario(AbstractUser):
    """
    Modelo de usuário customizado para o SynchroBI
    Baseado no portalcomercial com foco em gestão financeira
    """
    NIVEL_CHOICES = [
        ('admin', 'Administrador'),
        ('gestor', 'Gestor'),
        ('diretor', 'Diretor'),
    ]

    # Desabilitar relacionamentos explicitamente
    groups = None  # Remove o relacionamento com grupos
    user_permissions = None  # Remove o relacionamento com permissões individuais
    
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='analista')
    is_superuser = models.BooleanField(default=False)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    
    # Campos específicos para controle financeiro
    centro_custo = models.CharField(max_length=20, blank=True, null=True,
                                   help_text="Centro de custo do usuário")
    unidade_negocio = models.CharField(max_length=50, blank=True, null=True,
                                      help_text="Unidade de negócio")
    
    def __str__(self):
        nome_completo = f"{self.first_name} {self.last_name}".strip()
        return nome_completo or self.username
    
    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'