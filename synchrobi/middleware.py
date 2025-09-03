# synchrobi/middleware.py

from django.db.models import Q
import logging

logger = logging.getLogger('synchrobi')

class NotificacaoMiddleware:
    """Middleware para injetar notificações e alertas de sistema"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Injetar informações para usuários autenticados
        if request.user.is_authenticated:
            # Futuro: implementar notificações de alertas do DRE
            # Por exemplo: metas não atingidas, gastos acima do orçamento, etc.
            request.user.alertas_nao_lidos = 0
            request.user.notificacoes_sistema = []
        
        return response
    
class AppContextMiddleware:
    """Middleware para detectar contexto da aplicação baseado na URL"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        
        # Determinar contexto baseado no caminho da URL
        if '/gestor/' in path:
            request.session['app_context'] = 'gestor'
            request.session['app_name'] = 'SynchroBI - Gestão'
        elif '/api/' in path:
            request.session['app_context'] = 'api'
            request.session['app_name'] = 'SynchroBI - API'
        elif '/admin/' in path:
            request.session['app_context'] = 'admin'
            request.session['app_name'] = 'SynchroBI - Administração'
        else:
            request.session['app_context'] = 'home'
            request.session['app_name'] = 'SynchroBI'
        
        response = self.get_response(request)
        return response

class LoggingMiddleware:
    """Middleware para logging detalhado de requisições importantes"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log de requisições importantes (DRE, relatórios, etc.)
        if any(path in request.path for path in ['/api/', '/gestor/dre/', '/gestor/relatorio/']):
            logger.info(f"Requisição: {request.method} {request.path} - Usuário: {request.user}")
        
        response = self.get_response(request)
        
        # Log de erros de resposta
        if response.status_code >= 400:
            logger.warning(f"Resposta com erro: {response.status_code} para {request.path}")
        
        return response