from flask import render_template, request, jsonify, current_app, make_response # Añadir current_app
from . import investment_bp # Blueprint
from app import get_db_connection_invest # Funciones de conexión
import pymysql
import os
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
import sys
import traceback

# Manejador de errores para el Blueprint (400 Bad Request)
@investment_bp.app_errorhandler(400)
def handle_400_error(e):
    """Fuerza una respuesta JSON para cualquier error 400 generado automáticamente por Flask."""
    
    response_data = {
        # 'e' tiene un objeto de excepción con detalles del error
        'mensaje': f'Error 400 (Interceptado): El servidor no pudo procesar la solicitud (posiblemente JSON inválido o nulo). Detalles: {getattr(e, "description", str(e))}',
        'actualizados': 0,
        'errores': 1,
        'detalles': ['El servidor devolvió un error 400, no es un problema de enrutamiento.']
    }
    
    # 1. Creamos la respuesta JSON
    response = make_response(jsonify(response_data), 400)
    # 2. Forzamos la cabecera Content-Type a 'application/json'
    response.headers['Content-Type'] = 'application/json'
    return response

@investment_bp.route('/investments')
def investments():
    conn = get_db_connection_invest()
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    
    # Obtener las carteras disponibles
    cursor.execute("SELECT id, Name FROM Wallets ORDER BY Name")
    wallets = cursor.fetchall()

    # Obtener las plataformas disponibles
    cursor.execute("SELECT id, Name FROM Platforms ORDER BY Name")
    platforms = cursor.fetchall()
    
    # Obtener los símbolos disponibles
    cursor.execute("SELECT Symbol, Description FROM Symbols ORDER BY Description")
    symbols = cursor.fetchall()
    
    conn.close()
    return render_template('investments.html', wallets=wallets, symbols=symbols, platforms=platforms)

@investment_bp.route('/guardar_inversiones', methods=['POST'])
def guardar_inversiones():
    # Intenta obtener el JSON de forma segura
    # Aunque force=True ignora Content-Type, lo mejor es asegurar que el cuerpo es JSON.
    data = request.get_json(silent=True) 

    if data is None:
        # Devuelve una respuesta JSON explícita para el 400, forzando la respuesta JSON
        response_data = {
            'mensaje': 'Error 400: La solicitud no contiene JSON válido. (¿JSON vacío o Content-Type incorrecto?)',
            'actualizados': 0,
            'errores': 1,
            'detalles': ['No se pudo decodificar el JSON de la solicitud.']
        }
        
        # 1. Creamos la respuesta JSON
        # 2. Asignamos explícitamente el código de estado (400)
        # 3. Forzamos la cabecera Content-Type a 'application/json'
        response = make_response(jsonify(response_data), 400)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    conn = get_db_connection_invest()
    cursor = conn.cursor()

    actualizados = 0
    errores = 0
    detalles = []
    
    for transaccion in data:
        try:
            # Validar que Date y Amount estén presentes
            if not transaccion.get('Date') or not transaccion.get('Amount'):
                errores += 1
                detalles.append(f"Transacción omitida: Fecha o Importe no informados - {transaccion}")
                continue

            cursor.execute("""INSERT INTO WalletTransact (Date, 
                                                          Wallet, 
                                                          Platform, 
                                                          Symbol, 
                                                          Amount, 
                                                          Fee, 
                                                          Shares)
                              VALUES (%s, %s, %s, %s, %s, %s, %s)""", 
                           (transaccion['Date'], 
                            transaccion['Wallet'], 
                            transaccion['Platform'], 
                            transaccion['Symbol'], 
                            transaccion['Amount'], 
                            transaccion['Fee'], 
                            transaccion['Shares']))
            
            if cursor.rowcount > 0:
                actualizados += 1
            else:
                errores += 1
                detalles.append(f"Error al insertar transacción: {transaccion}")
                
        except Exception as e:
            # Líneas de depuración CRUCIALES para ver el error real
            print("--- ERROR EN guardado_inversiones ---", file=sys.stderr)
            print(f"Transacción con error: {transaccion}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr) # Imprime el error completo
            print("-----------------------------------", file=sys.stderr)

            errores += 1
            detalles.append(f"Error: {str(e)}. Ver consola del servidor para más detalles.")
    
    conn.commit()
    conn.close()
    
    mensaje = f"Inversiones guardadas. Actualizados: {actualizados}, Errores: {errores}"
    if detalles:
        mensaje += ". Detalles en la consola del servidor."
    
    return jsonify({
        'mensaje': mensaje,
        'actualizados': actualizados,
        'errores': errores,
        'detalles': detalles if errores > 0 else []
    })

# Ruta para la página de análisis de símbolos
@investment_bp.route('/symbolAnalysis')
def symbol_analysis():
    return render_template('symbolAnalysis.html')

# API para obtener lista de símbolos
@investment_bp.route('/api/symbols')
def get_symbols():
    conn = get_db_connection_invest()
    cursor = conn.cursor()
    cursor.execute("""SELECT S.Symbol, 
                             S.Description,
							 DATE_FORMAT(T.LastDate, '%Y-%m-%d') AS "LastDate"
                      FROM Symbols S
                      LEFT JOIN (SELECT Symbol,
                                        MAX(Date) AS "LastDate"
                                 FROM MarketTransact
                                 WHERE 1
                                 GROUP BY Symbol) T
                      ON S.Symbol = T.Symbol
                      WHERE S.Enabled = 1 
                      ORDER BY S.Type, S.Description""")
    symbols = [{'Symbol': row[0], 'Description': row[1], 'LastDate': row[2]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(symbols)

# API para obtener métricas
@investment_bp.route('/api/symbols/<symbol>/metrics')
def get_symbol_metrics(symbol):
    conn = get_db_connection_invest()
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    
    # Último close
    cursor.execute("SELECT Close FROM MarketTransact WHERE Symbol = %s ORDER BY Date DESC LIMIT 1", (symbol,))
    result = cursor.fetchone()
    last_close = float(result["Close"]) if result and "Close" in result else 0.0
    
    # Last Year %
    cursor.execute("""WITH MaxDates AS (SELECT Symbol, 
                                               MAX(Date) AS max_date 
                                        FROM MarketTransact 
                                        WHERE Symbol = %s
                                        GROUP BY Symbol)
                      SELECT (SELECT Close 
                              FROM MarketTransact 
                              WHERE Symbol = mt.Symbol AND 
                                    YEAR(Date) = YEAR(MaxDates.max_date) - 1 
                              ORDER BY Date ASC 
                              LIMIT 1) AS first_close_ly,
                             (SELECT Close 
                              FROM MarketTransact 
                              WHERE Symbol = mt.Symbol AND 
                                    YEAR(Date) = YEAR(MaxDates.max_date) - 1 
                              ORDER BY Date DESC 
                              LIMIT 1) AS last_close_ly,
                             (SELECT Close 
                              FROM MarketTransact 
                              WHERE Symbol = mt.Symbol AND 
                                    YEAR(Date) = YEAR(MaxDates.max_date)
                              ORDER BY Date ASC 
                              LIMIT 1) AS first_close_ty,
                             (SELECT Close FROM MarketTransact 
                              WHERE Symbol = mt.Symbol AND 
                                    YEAR(Date) = YEAR(MaxDates.max_date) AND 
                                    MONTH(Date) = MONTH(MaxDates.max_date) 
                              ORDER BY Date ASC 
                              LIMIT 1) AS first_close_tm,
                             (SELECT Close FROM MarketTransact 
                              WHERE Symbol = mt.Symbol AND 
                                    YEAR(Date) = YEAR(MaxDates.max_date) AND 
                                    WEEK(Date, 1) = WEEK(MaxDates.max_date, 1)
                              ORDER BY Date ASC 
                              LIMIT 1) AS first_close_tw,
                             (SELECT Close 
                              FROM MarketTransact 
                              WHERE Symbol = mt.Symbol AND 
                                    YEAR(Date) = YEAR(MaxDates.max_date)
                              ORDER BY Date DESC 
                              LIMIT 1 OFFSET 1) AS penul_close,
                             (SELECT Close 
                              FROM MarketTransact 
                              WHERE Symbol = mt.Symbol AND 
                                    YEAR(Date) = YEAR(MaxDates.max_date)
                              ORDER BY Date DESC 
                              LIMIT 1) AS last_close
                      FROM Symbols mt
                      INNER JOIN MaxDates
                      ON mt.Symbol = MaxDates.Symbol
                      WHERE 1""", (symbol,))
    result = cursor.fetchone()
    first_close_ly = float(result["first_close_ly"]) if result and "first_close_ly" in result else 0.0
    last_close_ly = float(result["last_close_ly"]) if result and "last_close_ly" in result else 0.0
    first_close_ty = float(result["first_close_ty"]) if result and "first_close_ty" in result else 0.0
    first_close_tm = float(result["first_close_tm"]) if result and "first_close_tm" in result else 0.0
    first_close_tw = float(result["first_close_tw"]) if result and "first_close_tw" in result else 0.0
    penul_close = float(result["penul_close"]) if result and "penul_close" in result else 0.0
    last_close = float(result["last_close"]) if result and "last_close" in result else 0.0

    # Cálculos de porcentajes (implementar lógica según tus necesidades)
    # Ejemplo simplificado:
    metrics = {
        'last_close': last_close,
        'last_year_pct': ((last_close_ly - first_close_ly) / first_close_ly * 100),
        'ytd_pct': ((last_close - first_close_ty) / first_close_ty * 100),
        'mtd_pct': ((last_close - first_close_tm) / first_close_tm * 100),
        'wtd_pct': ((last_close - first_close_tw) / first_close_tw * 100),
        'day_pct': ((last_close - penul_close) / penul_close * 100),
    }
    
    conn.close()
    return jsonify(metrics)

# API para datos históricos
@investment_bp.route('/api/symbols/<symbol>/history')
def get_symbol_history(symbol):
    conn = get_db_connection_invest()
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    cursor.execute("""SELECT Date, Close 
                      FROM MarketTransact 
                      WHERE Symbol = %s 
                      ORDER BY Date""", 
                   (symbol,))
    data = cursor.fetchall()
    conn.close()
    return jsonify([{'Date': row['Date'].strftime('%Y-%m-%d'), 'Close': row['Close']} for row in data])

# API para datos históricos completos (candlestick)
@investment_bp.route('/api/symbols/<symbol>/history-full')
def get_symbol_history_full(symbol):
    conn = get_db_connection_invest()
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    cursor.execute("""SELECT Date, Open, Close, Low, High, Volume 
                      FROM MarketTransact 
                      WHERE Symbol = %s 
                      ORDER BY Date""", 
                   (symbol,))
    data = cursor.fetchall()
    conn.close()
    return jsonify([{
        'Date': row['Date'].strftime('%Y-%m-%d'), 
        'Open': row['Open'],
        'Close': row['Close'],
        'Low': row['Low'],
        'High': row['High'],
        'Volume': row['Volume']
    } for row in data])

# API para fechas de compra
@investment_bp.route('/api/symbols/<symbol>/purchases')
def get_symbol_purchases(symbol):
    conn = get_db_connection_invest()
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    cursor.execute("""SELECT DISTINCT DATE(Date) as purchase_date 
                      FROM WalletTransact 
                      WHERE Symbol = %s AND Wallet = 'W01'
                      ORDER BY purchase_date""", 
                   (symbol,))
    data = cursor.fetchall()
    conn.close()
    return jsonify([row['purchase_date'].strftime('%Y-%m-%d') for row in data])

# Ruta para la página de análisis de símbolos
@investment_bp.route('/walletAnalysis')
def wallet_analysis():
    return render_template('walletAnalysis.html')

# API para obtener lista de wallets
@investment_bp.route('/api/WalletsAndPlatforms')
def get_WalletsAndPlatforms():
    conn = get_db_connection_invest()
    cursor = conn.cursor()

    # Obtener Wallets
    cursor.execute("SELECT id, Description FROM Wallets WHERE 1 ORDER BY id")
    wallets = [{'id': row[0], 'Description': row[1]} for row in cursor.fetchall()]

    # Obtener plataformas
    cursor.execute("SELECT id, Name FROM Platforms ORDER BY Name")
    platforms = [{'id': row[0], 'Name': row[1]} for row in cursor.fetchall()]

    conn.close()
    return jsonify({
        'wallets': wallets,
        'platforms': platforms
    })

