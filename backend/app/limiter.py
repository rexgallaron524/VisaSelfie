from slowapi import Limiter
from slowapi.util import get_remote_address

# One API worker for the demo. Use a shared Redis limiter before adding replicas.
# Forwarded IP headers are not trusted by the API server.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
