from flask import Flask
import pymysql
import os
from flask_wtf.csrf import CSRFProtect

from .config import Config

# Variables globales para las conexiones, si las prefieres así
# O mejor, pásalas a los blueprints o usa el contexto de la app
db_conn_finance = None
db_conn_investment = None
csrf = CSRFProtect()

def create_app(config_object=Config):
    global db_conn_finance, db_conn_investment
    
    app = Flask(__name__)
    app.config.from_object(config_object)

    csrf.init_app(app)

    # Inicializar conexiones a DB (ejemplo simple)
    # En una app más grande, considera usar una extensión como Flask-SQLAlchemy o Flask-PyMySQL
    try:
        db_conn_finance = pymysql.connect(**app.config['FINANCE_DB_CONFIG'])
        db_conn_investment = pymysql.connect(**app.config['INVESTMENT_DB_CONFIG'])
    except pymysql.Error as e:
        print(f"Error connecting to database: {e}")
        # Decide cómo manejar esto: salir, reintentar, etc.

    # Registrar Blueprints
    from .finance import finance_bp
    app.register_blueprint(finance_bp, url_prefix='/finance')

    from .investment import investment_bp
    app.register_blueprint(investment_bp, url_prefix='/investment')

    from .car import car_bp # Asumiendo que crearás uno
    app.register_blueprint(car_bp, url_prefix='/car')

    # (Opcional) Blueprint para rutas "core" o la página de inicio principal
    from .core import core_bp # Asumiendo que crearás uno
    app.register_blueprint(core_bp) # Sin prefijo si es la raíz

    # Asegúrate de que UPLOAD_FOLDER está configurado
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    return app

# Funciones para obtener conexiones (puedes moverlas a utils.py)
def get_db_connection_finance():
    # Esta es una forma simple. En producción, manejarías la reconexión si la conexión se pierde.
    # O mejor aún, obtén la conexión del pool de conexiones por solicitud.
    global db_conn_finance
    if db_conn_finance is None or not db_conn_finance.open:
        # Esto es problemático, necesitas la config aquí. Mejor pasar app.config o usar current_app
        from flask import current_app
        db_conn_finance = pymysql.connect(**current_app.config['FINANCE_DB_CONFIG'])
    return db_conn_finance

def get_db_connection_invest():
    global db_conn_investment
    if db_conn_investment is None or not db_conn_investment.open:
        from flask import current_app
        db_conn_investment = pymysql.connect(**current_app.config['INVESTMENT_DB_CONFIG'])
    return db_conn_investment