import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-dificil-de-adivinar'
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'uploads') # Apunta al directorio 'uploads' en la raíz

    FINANCE_DB_CONFIG = {
        'host': 'localhost',
        'user': 'jmsantiago',
        'password': 'PeTresCuP3Q',
        'database': 'Finance'
    }
    INVESTMENT_DB_CONFIG = {
        'host': 'localhost',
        'user': 'jmsantiago',
        'password': 'PeTresCuP3Q',
        'database': 'Investment'
    }
    ALLOWED_EXTENSIONS = {'xls', 'xlsx'}

# Asegúrate de crear el directorio uploads si no existe
if not os.path.exists(Config.UPLOAD_FOLDER):
    os.makedirs(Config.UPLOAD_FOLDER)