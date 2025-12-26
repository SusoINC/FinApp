from flask import Blueprint

finance_bp = Blueprint('finance', 
                       __name__,
                       template_folder='templates',
                       static_folder='static', # Si tienes estáticos específicos
                       static_url_path='/finance/static') # URL para estáticos de este blueprint

from . import routes # Importa las rutas al final para evitar importaciones circulares