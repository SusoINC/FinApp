from flask import render_template
from . import car_bp

@car_bp.route('/')
def index():
    return "Módulo Car Próximamente" # O render_template('car/index.html')