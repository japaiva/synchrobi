# core/models/fornecedor.py - MODELO DE FORNECEDOR ATUALIZADO

import logging
import re
from django.db import models
from django.core.exceptions import ValidationError

logger = logging.getLogger('synchrobi')

class Fornecedor(models.Model):
    """Cadastro de fornecedores com dados simplificados - VERSÃO ATUALIZADA"""
    
    codigo = models.CharField(max_length=20, primary_key=True, verbose_name="Código")
    razao_social = models.CharField(
        max_length=255, 
        verbose_name="Razão Social",
        db_index=True  # ÍNDICE PARA BUSCA POR NOME
    )
    nome_fantasia = models.CharField(max_length=255, blank=True, verbose_name="Nome Fantasia")
    cnpj_cpf = models.CharField(max_length=18, blank=True, verbose_name="CNPJ/CPF")
    
    # Dados de contato
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    email = models.EmailField(blank=True, verbose_name="E-mail")
    endereco = models.TextField(blank=True, verbose_name="Endereço")
    
    # Controle
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_automaticamente = models.BooleanField(default=False, verbose_name="Criado Automaticamente")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_alteracao = models.DateTimeField(auto_now=True)
    
    # Campos para rastreamento da origem
    origem_historico = models.TextField(
        blank=True, 
        verbose_name="Histórico de Origem",
        help_text="Histórico original de onde foi extraído"
    )
    
    def clean(self):
        """Validação customizada"""
        super().clean()
        
        # Limpar razão social
        if self.razao_social:
            self.razao_social = self.razao_social.strip().upper()
        
        # Validar CNPJ/CPF se fornecido
        if self.cnpj_cpf:
            cnpj_cpf_limpo = re.sub(r'[^\d]', '', self.cnpj_cpf)
            if len(cnpj_cpf_limpo) not in [11, 14]:
                raise ValidationError({
                    'cnpj_cpf': 'CNPJ deve ter 14 dígitos ou CPF deve ter 11 dígitos'
                })
    
    @property
    def nome_display(self):
        """Nome para exibição (nome fantasia se houver, senão razão social)"""
        return self.nome_fantasia or self.razao_social
    
    @property
    def cnpj_cpf_formatado(self):
        """CNPJ/CPF formatado"""
        if not self.cnpj_cpf:
            return ''
        
        numeros = re.sub(r'[^\d]', '', self.cnpj_cpf)
        
        if len(numeros) == 14:  # CNPJ
            return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:14]}"
        elif len(numeros) == 11:  # CPF
            return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:11]}"
        else:
            return self.cnpj_cpf
    
    @property
    def tipo_pessoa(self):
        """Retorna se é PF ou PJ baseado no CNPJ/CPF"""
        if not self.cnpj_cpf:
            return 'Não informado'
        
        numeros = re.sub(r'[^\d]', '', self.cnpj_cpf)
        
        if len(numeros) == 14:
            return 'Pessoa Jurídica'
        elif len(numeros) == 11:
            return 'Pessoa Física'
        else:
            return 'Inválido'
    
    @classmethod
    def buscar_por_nome(cls, nome, apenas_ativos=True):
        """
        Busca fornecedor por nome (busca exata na razão social)
        """
        if not nome:
            return None
        
        nome_limpo = nome.strip().upper()
        
        try:
            query = cls.objects.filter(razao_social=nome_limpo)
            if apenas_ativos:
                query = query.filter(ativo=True)
            
            return query.first()
            
        except Exception as e:
            logger.error(f'Erro ao buscar fornecedor por nome {nome}: {str(e)}')
            return None
    
    @classmethod
    def buscar_por_nome_parcial(cls, nome_parcial, apenas_ativos=True):
        """
        Busca fornecedores por nome parcial (contém)
        """
        if not nome_parcial or len(nome_parcial) < 3:
            return cls.objects.none()
        
        nome_limpo = nome_parcial.strip().upper()
        
        try:
            query = cls.objects.filter(razao_social__icontains=nome_limpo)
            if apenas_ativos:
                query = query.filter(ativo=True)
            
            return query.order_by('razao_social')
            
        except Exception as e:
            logger.error(f'Erro na busca parcial por nome {nome_parcial}: {str(e)}')
            return cls.objects.none()
    
    @classmethod
    def gerar_codigo_automatico(cls, nome):
        """
        Gera código automático baseado no nome do fornecedor
        """
        import hashlib
        
        if not nome:
            return "AUTO0001"
        
        nome_limpo = nome.upper().strip()
        
        # Pegar primeiras letras de cada palavra
        palavras = nome_limpo.split()
        iniciais = ''.join([palavra[0] for palavra in palavras if palavra])[:4]
        
        # Se não conseguir 4 iniciais, preencher com primeiras letras
        if len(iniciais) < 4:
            iniciais = (nome_limpo.replace(' ', '')[:4]).ljust(4, 'X')
        
        # Adicionar hash do nome para evitar duplicatas
        hash_nome = hashlib.md5(nome_limpo.encode()).hexdigest()[:4].upper()
        codigo_base = f"{iniciais}{hash_nome}"
        
        # Verificar se código já existe e incrementar se necessário
        codigo_final = codigo_base
        contador = 1
        
        while cls.objects.filter(codigo=codigo_final).exists():
            codigo_final = f"{codigo_base}{contador:02d}"
            contador += 1
            if contador > 99:  # Limite de segurança
                # Se não conseguir gerar código único, usar timestamp
                import time
                codigo_final = f"AUTO{int(time.time()) % 10000:04d}"
                break
        
        return codigo_final
    
    @classmethod
    def extrair_do_historico(cls, historico, salvar=True):
        """
        Extrai fornecedor do histórico - VERSÃO ATUALIZADA SEM NÚMEROS
        Exemplo: "... - 826498 AUTOPEL AUTOMACAO COMERCIAL E INFORMATICA LTDA - ..."
        Extrai apenas: "AUTOPEL AUTOMACAO COMERCIAL E INFORMATICA LTDA"
        """
        if not historico:
            return None
        
        # Busca por "- NÚMERO NOME_COMPLETO -" mas pega apenas o NOME
        matches = re.findall(r'- \d+\s+([A-Z\s&\.\-_]+?) -', historico)
        
        if not matches:
            return None
        
        # Pegar o último match (mais provável de ser o fornecedor principal)
        nome = matches[-1].strip()
        
        if len(nome) < 3:  # Nome muito curto
            return None
        
        nome_limpo = nome.upper().strip()
        
        # Verificar se fornecedor já existe pelo nome
        fornecedor_existente = cls.buscar_por_nome(nome_limpo)
        if fornecedor_existente:
            logger.info(f'Fornecedor existente encontrado por nome: {fornecedor_existente.codigo} - {nome_limpo}')
            return fornecedor_existente
        
        # Se não vai salvar, retornar instância não salva para preview
        if not salvar:
            codigo_preview = cls.gerar_codigo_automatico(nome_limpo)
            return cls(
                codigo=codigo_preview,
                razao_social=nome_limpo,
                criado_automaticamente=True,
                origem_historico=historico[:500]
            )
        
        # Criar novo fornecedor
        try:
            codigo_auto = cls.gerar_codigo_automatico(nome_limpo)
            
            fornecedor = cls.objects.create(
                codigo=codigo_auto,
                razao_social=nome_limpo,
                criado_automaticamente=True,
                origem_historico=historico[:500]
            )
            
            logger.info(f'Novo fornecedor criado: {codigo_auto} - {nome_limpo}')
            return fornecedor
            
        except Exception as e:
            logger.error(f'Erro ao criar fornecedor para {nome_limpo}: {str(e)}')
            return None
    
    def __str__(self):
        return f"{self.codigo} - {self.nome_display}"
    
    class Meta:
        db_table = 'fornecedores'
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['razao_social']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['razao_social']),  # ÍNDICE PRINCIPAL PARA BUSCA POR NOME
            models.Index(fields=['ativo']),
            models.Index(fields=['criado_automaticamente']),
            models.Index(fields=['razao_social', 'ativo']),  # ÍNDICE COMPOSTO
        ]