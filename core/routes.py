from flask import render_template, request, jsonify, current_app # Añadir current_app
from app import get_db_connection_finance # Funciones de conexión
import pymysql
from . import core_bp



@core_bp.route('/')
def index():
    return render_template('core/index.html') # Asume que mueves index.html aquí

@core_bp.route('/api/dashboard/summary')
def dashboard_summary():
    # Obtener parámetros de filtro de la solicitud
    year = request.args.get('year', '2025')
    month = request.args.get('month', None)
    type_id = request.args.get('type', None)
    entity_id = request.args.get('entity', None)
    
    try:
        conn = get_db_connection_finance()
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        
        # Obtener lista de años para el filtro
        cursor.execute("SELECT DISTINCT YEAR(Op_Date) as year FROM Transact ORDER BY year DESC")
        years = [row['year'] for row in cursor.fetchall()]
        
        # Si no hay años en la base de datos, agregar el año actual como opción
        if not years:
            years = [2025]  # Asegurar que al menos exista un año
        
        # Obtener entidades para el filtro
        cursor.execute("SELECT id, IBAN FROM Entity ORDER BY IBAN")
        entities = cursor.fetchall()
        
        # Obtener tipos para el filtro
        cursor.execute("SELECT id, Item FROM Type ORDER BY Item")
        types = cursor.fetchall()
        
        # Construir la consulta base con la condición de año
        base_query = """
            SELECT 
                SUM(Amount) as total,
                SUM(CASE WHEN Type = 'T01' THEN Amount ELSE 0 END) as income,
                SUM(CASE WHEN Type IN ('T02', 'T05') THEN Amount ELSE 0 END) as expense,
                SUM(CASE WHEN Type = 'T04' THEN Amount ELSE 0 END) as investments,
                COUNT(CASE WHEN Type IS NOT NULL AND Type != '' THEN 1 END) as type_informed,
                COUNT(*) as total_rows
            FROM Transact 
            WHERE YEAR(Op_Date) = %s
        """
        params = [year]
        
        # Agregar filtros adicionales si están presentes
        if month:
            base_query += " AND MONTH(Op_Date) = %s"
            params.append(month)
        if type_id and type_id != '0':
            base_query += " AND Type = %s"
            params.append(type_id)
        if entity_id and entity_id != '0':
            base_query += " AND Entity = %s"
            params.append(entity_id)
        
        # Ejecutar consulta para obtener los totales
        cursor.execute(base_query, params)
        result = cursor.fetchone()
        
        # Calcular el porcentaje de filas con Type informado
        if result['total_rows'] > 0:
            quality_percentage = (result['type_informed'] / result['total_rows']) * 100
        else:
            quality_percentage = 0
        
        # Obtener datos para el gráfico de categorías
        category_query = """
            SELECT 
                COALESCE(Category.Item, 'Sin categoría') as category,
                SUM(Transact.Amount) as amount
            FROM Transact
            LEFT JOIN Category ON Transact.Category = Category.id
            WHERE Type = 'T02' AND YEAR(Transact.Op_Date) = %s
        """
        category_params = [year]
        
        if month:
            category_query += " AND MONTH(Transact.Op_Date) = %s"
            category_params.append(month)
        if type_id and type_id != '0':
            category_query += " AND Transact.Type = %s"
            category_params.append(type_id)
        if entity_id and entity_id != '0':
            category_query += " AND Transact.Entity = %s"
            category_params.append(entity_id)
        
        category_query += " GROUP BY Category.Item ORDER BY ABS(SUM(Transact.Amount)) DESC LIMIT 10"
        
        cursor.execute(category_query, category_params)
        categories = cursor.fetchall()
        
        # Si no hay categorías, crear datos de muestra
        if not categories:
            categories = [
                {'category': 'Sin datos', 'amount': 0}
            ]
        
        # Datos para el gráfico mensual
        monthly_query = """
            SELECT 
                MONTH(Op_Date) as month, 
                SUM(CASE WHEN Type = 'T01' THEN Amount ELSE 0 END) as income,
                SUM(CASE WHEN Type IN ('T02', 'T05') THEN Amount ELSE 0 END) as expense
            FROM Transact
            WHERE YEAR(Op_Date) = %s
        """
        monthly_params = [year]
        
        if type_id and type_id != '0':
            monthly_query += " AND Type = %s"
            monthly_params.append(type_id)
        if entity_id and entity_id != '0':
            monthly_query += " AND Entity = %s"
            monthly_params.append(entity_id)
        
        monthly_query += " GROUP BY MONTH(Op_Date) ORDER BY MONTH(Op_Date)"
        
        cursor.execute(monthly_query, monthly_params)
        monthly_data = cursor.fetchall()
        
        # Si no hay datos mensuales, crear datos de muestra
        if not monthly_data:
            monthly_data = [{'month': i, 'amount': 0} for i in range(1, 13)]
        
        conn.close()
        
        return jsonify({
            'summary': {
                'total': float(result['total']) if result['total'] else 0,
                'income': float(result['income']) if result['income'] else 0,
                'expense': float(result['expense']) if result['expense'] else 0,
                'investments': float(result['investments']) if result['investments'] else 0,
                'quality': round(quality_percentage, 2)  # Redondear a 2 decimales
            },
            'categories': [
                {'category': cat['category'], 'amount': float(cat['amount'])} 
                for cat in categories
            ],
            'monthly': [
                {'month': mon['month'], 
                 'income': float(mon['income']), 
                 'expense': float(mon['expense'])}
                for mon in monthly_data
            ],
            'filters': {
                'years': years,
                'entities': entities,
                'types': types
            }
        })
    except Exception as e:
        print(f"Error en dashboard_summary: {str(e)}")
        return jsonify({
            'error': str(e),
            'summary': {'total': 0, 'income': 0, 'expense': 0, 'investments': 0, 'quality': 0},
            'categories': [{'category': 'Error', 'amount': 0}],
            'monthly': [{'month': i, 'amount': 0} for i in range(1, 13)],
            'filters': {'years': [2025], 'entities': [], 'types': []}
        }), 500
