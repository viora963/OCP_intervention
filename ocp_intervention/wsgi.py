"""
WSGI config for ocp_intervention project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocp_intervention.settings')

application = get_wsgi_application()
