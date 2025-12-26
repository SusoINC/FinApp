import yfinance as yf
import pymysql
import requests
from datetime import datetime, timedelta

# Configuración de la conexión a la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'user': 'jmsantiago',
    'password': 'PeTresCuP3Q',
    'database': 'Investment'
}

# Configuración de la API de EODHD
EODHD_API_TOKEN = '67d9e7a52a1ac5.86979060'

class TransactionCounter:
    def __init__(self):
        self.inserted = 0
        self.updated = 0
        self.skipped = 0
    
    def reset(self):
        """Resetea los contadores."""
        self.inserted = 0
        self.updated = 0
        self.skipped = 0
    
    def get_counts(self):
        """Devuelve una cadena con los contadores actuales."""
        return f"Insertados: {self.inserted}, Actualizados: {self.updated}, Omitidos: {self.skipped}"

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def fetch_symbols():
    """Obtiene los símbolos habilitados de la tabla Symbols."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Symbol, System FROM Symbols WHERE Enabled = 1")
    symbols = [(row[0], row[1]) for row in cursor.fetchall()]
    conn.close()
    return symbols

def fetch_market_data_yfinance(symbol):
    """Obtiene los datos de mercado de los últimos 28 días para un símbolo usando yfinance."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=28)
    return yf.download(symbol, start=start_date)

def fetch_market_data_eodhd(symbol):
    """Obtiene los datos de mercado de los últimos 2 años para un símbolo usando EODHD."""
    url = f"https://eodhd.com/api/eod/{symbol}?api_token={EODHD_API_TOKEN}&fmt=json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    print(f"Error EODHD para {symbol}: {response.status_code} - {response.text}")
    return None

def compare_and_update(cursor, symbol, date, new_data):
    """
    Compara los datos existentes con los nuevos y decide si insertar o actualizar.
    Devuelve 'inserted', 'updated' o 'skipped'.
    """
    # Verificar si ya existe un registro para esta fecha y símbolo
    cursor.execute("""
        SELECT Open, High, Low, Close, Volume 
        FROM MarketTransact 
        WHERE Date = %s AND Symbol = %s
    """, (date, symbol))
    
    existing = cursor.fetchone()
    
    if existing:
        # Convertir los datos existentes a un diccionario para comparar
        existing_data = {
            'Open': float(existing[0]),
            'High': float(existing[1]),
            'Low': float(existing[2]),
            'Close': float(existing[3]),
            'Volume': int(existing[4])
        }
        
        # Comparar los datos existentes con los nuevos
        if existing_data != new_data:
            # Actualizar el registro si los datos son diferentes
            cursor.execute("""
                UPDATE MarketTransact 
                SET Open = %s, High = %s, Low = %s, Close = %s, Volume = %s 
                WHERE Date = %s AND Symbol = %s
            """, (
                new_data['Open'], new_data['High'], new_data['Low'],
                new_data['Close'], new_data['Volume'], date, symbol
            ))
            return 'updated'
        else:
            # Omitir si los datos son iguales
            return 'skipped'
    else:
        # Insertar un nuevo registro si no existe
        cursor.execute("""
            INSERT INTO MarketTransact 
            (Date, Symbol, Open, High, Low, Close, Volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (date, symbol, *new_data.values()))
        return 'inserted'

def process_transactions(symbol, data, system, counter):
    """Procesa las transacciones con verificación de datos existentes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if system == 'yfinance':
            for index, row in data.iterrows():
                date = index.strftime('%Y-%m-%d')
                new_data = {
                    'Open': float(row['Open'].iloc[0]),
                    'High': float(row['High'].iloc[0]),
                    'Low': float(row['Low'].iloc[0]),
                    'Close': float(row['Close'].iloc[0]),
                    'Volume': int(row['Volume'].iloc[0])
                }
                
                result = compare_and_update(cursor, symbol, date, new_data)
                if result == 'inserted':
                    counter.inserted += 1
                elif result == 'updated':
                    counter.updated += 1
                else:
                    counter.skipped += 1
        
        elif system == 'eodhd':
            for entry in data:
                date = entry['date']
                new_data = {
                    'Open': float(entry['open']),
                    'High': float(entry['high']),
                    'Low': float(entry['low']),
                    'Close': float(entry['close']),
                    'Volume': int(entry['volume'])
                }
                
                result = compare_and_update(cursor, symbol, date, new_data)
                if result == 'inserted':
                    counter.inserted += 1
                elif result == 'updated':
                    counter.updated += 1
                else:
                    counter.skipped += 1
        
        conn.commit()
    finally:
        conn.close()

def main():
    global_counter = TransactionCounter()  # Contador global para el proceso completo
    symbols = fetch_symbols()
    
    # Inicio de ejecución
    print("=" * 50)
    print(f"[{datetime.now()}] Inicio de ejecución")
    print("=" * 50)
    
    for symbol, system in symbols:
        symbol_counter = TransactionCounter()  # Contador específico para el símbolo actual
        print(f"[{datetime.now()}] Procesando símbolo: {symbol} ({system})")
        
        try:
            if system == 'yfinance':
                data = fetch_market_data_yfinance(symbol)
                if data.empty:
                    print(f"[{datetime.now()}] Sin datos para {symbol} (yfinance)")
                    continue
            elif system == 'eodhd':
                data = fetch_market_data_eodhd(symbol)
                if not data:
                    print(f"[{datetime.now()}] Sin datos para {symbol} (eodhd)")
                    continue
            else:
                print(f"[{datetime.now()}] Sistema no soportado: {system} para {symbol}")
                continue
            
            process_transactions(symbol, data, system, symbol_counter)
            
            # Actualizar el contador global
            global_counter.inserted += symbol_counter.inserted
            global_counter.updated += symbol_counter.updated
            global_counter.skipped += symbol_counter.skipped
            
            # Mostrar resultados del símbolo actual
            print(f"[{datetime.now()}] Fin de procesamiento de {symbol} | {symbol_counter.get_counts()}")
        except Exception as e:
            print(f"[{datetime.now()}] Error en {symbol}: {str(e)}")
    
    # Fin de ejecución (mostrar contadores globales)
    print("=" * 50)
    print(f"[{datetime.now()}] Proceso completado | {global_counter.get_counts()}")
    print("=" * 50)

if __name__ == "__main__":
    main()