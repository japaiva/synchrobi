# gunicorn.conf.py - Configurações do Gunicorn para SynchroBI

import multiprocessing

# Bind
bind = "0.0.0.0:8000"

# Workers
# Fórmula recomendada: (2 x $num_cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"

# Timeout
# Aumentado para 300 segundos (5 minutos) para permitir importação de arquivos grandes
timeout = 300
graceful_timeout = 60
keepalive = 5

# Request limits
# Reinicia workers após N requisições para prevenir memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Process naming
proc_name = "synchrobi"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (descomente se necessário)
# keyfile = None
# certfile = None
