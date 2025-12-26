from flask import Blueprint

investment_bp = Blueprint('investment', 
                          __name__,
                          template_folder='templates',
                          static_folder='static',
                          static_url_path='/investment/static')
from . import routes