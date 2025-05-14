import multiprocessing

# Server socket configuration
bind = "0.0.0.0:$PORT"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Process naming
proc_name = 'medical_app'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# SSL configuration
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Process management
preload_app = True
reload = False
daemon = False

# Server mechanics
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50

# Debug
spew = False
check_config = False