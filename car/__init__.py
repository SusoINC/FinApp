from flask import Blueprint

car_bp = Blueprint('car',
                   __name__,
                   template_folder='templates',
                   static_folder='static')

from . import routes