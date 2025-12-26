from flask import render_template, request, jsonify, current_app # Añadir current_app
from . import finance_bp # Blueprint
from app import get_db_connection_finance # Funciones de conexión
import pymysql
import os
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
import sys
from datetime import datetime

# Tu ruta raíz puede ir aquí o en un blueprint 'core'
# Si es el dashboard de finanzas:
@finance_bp.route('/') # Ahora será /finance/

def allowed_file(filename): # Mueve o importa esta función
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# Finance - Ruta para categorizar
@finance_bp.route('/categorize')
def categorize():
    conn = get_db_connection_finance()
    cursor = conn.cursor(cursor = pymysql.cursors.DictCursor)
    cursor.execute("""SELECT id, 
                             Entity, 
                             Type, 
                             Class, 
                             Category, 
                             Detail, 
                             Company, 
                             Op_Date, 
                             Categoria, 
                             Subcategoria, 
                             Description, 
                             Comment, 
                             Amount, 
                             FreeText 
                      FROM Transact 
                      WHERE (Type IS NULL OR Type = '') AND 
                            YEAR(Op_Date) = 2025
                      ORDER BY Op_Date ASC""")
    transacciones = cursor.fetchall()

    cursor.execute("""SELECT id, 
                             IBAN 
                      FROM Entity
                      ORDER BY id""")
    entities = cursor.fetchall()

    cursor.execute("""SELECT 0 AS id, 
                             '' AS Item
                      UNION ALL
                      SELECT id, 
                             Item 
                      FROM Type
                      ORDER BY id""")
    types = cursor.fetchall()

    cursor.execute("""SELECT 0 AS id, 
                             '' AS Item
                      UNION ALL
                      SELECT id, 
                             Item 
                      FROM Class
                      ORDER BY id""")
    classes = cursor.fetchall()

    cursor.execute("""SELECT 0 AS id, 
                             '' AS Item
                      UNION ALL
                      SELECT id, 
                             Item 
                      FROM Category
                      ORDER BY CASE WHEN Item = '' THEN 0 ELSE 1 END, Item""")
    categories = cursor.fetchall()

    conn.close()
    return render_template('categorize.html', 
                           transacciones=transacciones, 
                           entities=entities,
                           types=types,
                           classes=classes,
                           categories=categories)

# Finance - Ruta para actualizar transacciones
@finance_bp.route('/actualizar', methods=['POST'])
def actualizar_transacciones():
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()  # Usar get_json() en lugar de .json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        conn = get_db_connection_finance()
        cursor = conn.cursor()

        actualizados = 0
        errores = 0
        detalles = []
        
        for transaccion in data:
            try:
                # Validación de datos
                if not transaccion.get('id'):
                    raise ValueError("ID de transacción faltante")
                
                # Extrae los valores
                id_transaccion = transaccion.get('id')
                entity = transaccion.get('Entity')
                type_value = transaccion.get('Type')
                class_value = transaccion.get('Class')
                category_value = transaccion.get('Category')
                detail_value = transaccion.get('Detail', '')
                company_value = transaccion.get('Company', '')
                freetext_value = transaccion.get('FreeText', '')
            
                print(f"Procesando transacción ID={id_transaccion}, Type={type_value}")
            
                # Verificar que tengamos un Type válido
                if not type_value or type_value == "0" or type_value == "":
                    print(f"Saltando transacción ID={id_transaccion} - Type inválido")
                    detalles.append(f"ID {id_transaccion}: Type inválido")
                    continue
                
                # Preparar valores para la base de datos
                type_value = None if not type_value or type_value == "0" or type_value == "" else type_value
                class_value = None if not class_value or class_value == "0" or class_value == "" else class_value
                category_value = None if not category_value or category_value == "0" or category_value == "" else category_value
                detail_value = None if not detail_value or detail_value.strip() == "" else detail_value
                freetext_value = None if not freetext_value or freetext_value.strip() == "" else freetext_value
            
                # Ejecutar la actualización
                cursor.execute("""UPDATE Transact 
                                  SET Entity = %s, 
                                      Type = %s, 
                                      Class = %s, 
                                      Category = %s, 
                                      Detail = %s, 
                                      Company = %s,
                                      FreeText = %s
                                      WHERE id = %s""",
                               (entity, 
                                type_value, 
                                class_value, 
                                category_value, 
                                detail_value, 
                                company_value, 
                                freetext_value, 
                                id_transaccion))
            
                if cursor.rowcount > 0:
                    actualizados += 1
                    print(f"Transacción ID={id_transaccion} actualizada correctamente")
                else:
                    errores += 1
                    detalles.append(f"ID {id_transaccion}: No encontrado o sin cambios")
                    print(f"Transacción ID={id_transaccion} no actualizada")
                
            except Exception as e:
                errores += 1
                detalles.append(f"ID {transaccion.get('id', 'unknown')}: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'mensaje': f'Actualización completada. Actualizados: {actualizados}, Errores: {errores}',
            'actualizados': actualizados,
            'errores': errores,
            'detalles': detalles if errores > 0 else []
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'mensaje': 'Error en el servidor al procesar la solicitud'
        }), 500

# Página para cargar archivos
@finance_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    conn = get_db_connection_finance()
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    
    # Obtener la lista de entidades para el select
    cursor.execute("SELECT id, IBAN FROM Entity ORDER BY IBAN")
    entities = cursor.fetchall()
    
    result = None
    
    if request.method == 'POST':
        # Comprobar si se envió un archivo
        if 'file' not in request.files:
            return render_template('finance/upload.html', entities=entities, 
                                  result={'message': 'No se seleccionó ningún archivo', 'imported': 0, 'errors': []})
        
        file = request.files['file']
        
        # Si el usuario no selecciona un archivo
        if file.filename == '':
            return render_template('finance/upload.html', entities=entities, 
                                  result={'message': 'No se seleccionó ningún archivo', 'imported': 0, 'errors': []})
        
        # Obtener entidad y formato de fecha seleccionados
        entity_id = request.form.get('entity')
        date_format = request.form.get('date_format', 'DD.MM.YYYY')
        sheet_name = request.form.get('sheet', None)
        
        if file and allowed_file(file.filename):
            # Guardar el archivo temporalmente
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Procesar el archivo Excel
                result = process_excel_file(filepath, entity_id, date_format, sheet_name, conn)
                
                # Eliminar el archivo después de procesarlo
                os.unlink(filepath)
                
            except Exception as e:
                result = {
                    'message': f'Error al procesar el archivo: {str(e)}',
                    'imported': 0,
                    'errors': [str(e)]
                }
    
    conn.close()
    return render_template('upload.html', entities=entities, result=result)

# Función para procesar el archivo Excel
def process_excel_file(filepath, entity_id, date_format, sheet_name, conn):
    cursor = conn.cursor()
    imported = 0
    errors = []
    
    try:
        # Cargar el archivo Excel
        if sheet_name and sheet_name.strip():
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=5)
        else:
            df = pd.read_excel(filepath, header=3)
        
        # Verificar que las columnas necesarias existan
        required_columns = ['F. VALOR', 'CATEGORÍA', 'SUBCATEGORÍA', 'DESCRIPCIÓN', 'COMENTARIO', 'IMPORTE (€)']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'message': f'El archivo no contiene las columnas requeridas: {", ".join(missing_columns)}',
                'imported': 0,
                'errors': [f'Columnas faltantes: {", ".join(missing_columns)}']
            }
        
        # Convertir formato de fecha
        date_parser = None
        if date_format == 'DD.MM.YYYY':
            date_parser = lambda x: datetime.strptime(x, '%d.%m.%Y') if isinstance(x, str) else pd.to_datetime(x)
        elif date_format == 'DD/MM/YYYY':
            date_parser = lambda x: datetime.strptime(x, '%d/%m/%Y') if isinstance(x, str) else pd.to_datetime(x)
        elif date_format == 'YYYY-MM-DD':
            date_parser = lambda x: datetime.strptime(x, '%Y-%m-%d') if isinstance(x, str) else pd.to_datetime(x)
        
        # Procesar cada fila
        for index, row in df.iterrows():
            try:
                # Extracción de datos
                if pd.notna(row['F. VALOR']):
                    try:
                        op_date = date_parser(row['F. VALOR'])
                    except:
                        errors.append(f"Fila {index+1}: Error al convertir la fecha '{row['F. VALOR']}'")
                        continue
                else:
                    errors.append(f"Fila {index+1}: Fecha vacía")
                    continue
                
                categoria = str(row['CATEGORÍA']) if pd.notna(row['CATEGORÍA']) else None
                subcategoria = str(row['SUBCATEGORÍA']) if pd.notna(row['SUBCATEGORÍA']) else None
                description = str(row['DESCRIPCIÓN']) if pd.notna(row['DESCRIPCIÓN']) else None
                comment = str(row['COMENTARIO']) if pd.notna(row['COMENTARIO']) else None
                
                # Asegurar que el importe es un número
                if pd.notna(row['IMPORTE (€)']):
                    try:
                        amount = float(str(row['IMPORTE (€)']).replace(',', '.'))
                    except:
                        errors.append(f"Fila {index+1}: Error al convertir el importe '{row['IMPORTE (€)']}'")
                        continue
                else:
                    errors.append(f"Fila {index+1}: Importe vacío")
                    continue
                
                # Insertar en la base de datos
                cursor.execute("""
                    INSERT INTO Transact (Entity, Op_Date, Categoria, Subcategoria, Description, Comment, Amount) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (entity_id, op_date, categoria, subcategoria, description, comment, amount))
                
                imported += 1
                
            except Exception as e:
                errors.append(f"Fila {index+1}: {str(e)}")
        
        # Confirmar la transacción
        conn.commit()
        
        message = f'Archivo procesado correctamente. {imported} registros importados.'
        if errors:
            message += f' {len(errors)} errores encontrados.'
        
        return {
            'message': message,
            'imported': imported,
            'errors': errors
        }
        
    except Exception as e:
        # Revertir cualquier cambio si hay un error
        conn.rollback()
        return {
            'message': f'Error al procesar el archivo: {str(e)}',
            'imported': 0,
            'errors': [str(e)]
        }


@finance_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# API endpoint para obtener datos resumidos para el dashboard
@finance_bp.route('/api/dashboard/summary')
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

############## /Dashboard

@finance_bp.route('/editTransactions', methods=['GET', 'POST'])
def edit_transactions():
    conn = get_db_connection_finance()
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    # Inicializar la lista de transacciones vacía
    transacciones = []

    # Obtener parámetros de filtro del formulario (si se envió)
    filters = {}
    if request.method == 'POST':
        filters['start_date'] = request.form.get('start_date')
        filters['end_date'] = request.form.get('end_date')
        filters['entity'] = request.form.get('entity')
        filters['type'] = request.form.get('type')
        filters['class'] = request.form.get('class')
        filters['category'] = request.form.get('category')
        filters['detail'] = request.form.get('detail')
        filters['company'] = request.form.get('company')

    # Construir la consulta base
    query = """SELECT id, 
                      Entity, 
                      Type, 
                      Class, 
                      Category, 
                      IFNULL(Detail, '') AS Detail, 
                      IFNULL(Company, '') AS Company, 
                      Op_Date, 
                      Categoria, 
                      Subcategoria, 
                      Description, 
                      Comment, 
                      Amount, 
                      IFNULL(FreeText, '') AS FreeText 
               FROM Transact 
               WHERE Type IS NOT NULL AND Type <> ''
               """
    params = []

    # Aplicar filtros
    if filters.get('start_date'):
        query += " AND Op_Date >= %s"
        params.append(filters['start_date'])
    if filters.get('end_date'):
        query += " AND Op_Date <= %s"
        params.append(filters['end_date'])
    if filters.get('entity') and filters['entity'] != '':
        query += " AND Entity = %s"
        params.append(filters['entity'])
    if filters.get('type') and filters['type'] != '':
        query += " AND Type = %s"
        params.append(filters['type'])
    if filters.get('class') and filters['class'] != '':
        query += " AND Class = %s"
        params.append(filters['class'])
    if filters.get('category') and filters['category'] != '':
        query += " AND Category = %s"
        params.append(filters['category'])
    if filters.get('detail') and filters['detail'] != '':
        query += " AND Detail LIKE %s"
        params.append(f'%{filters["detail"]}%')
    if filters.get('company') and filters['company'] != '':
        query += " AND Company LIKE %s"
        params.append(f'%{filters["company"]}%')

    query += """ORDER BY OP_Date ASC"""

    # Ejecutar la consulta
    cursor.execute(query, params)
    if request.method == 'POST':
        transacciones = cursor.fetchall()

    # Obtener listas para los filtros
    cursor.execute("SELECT id, IBAN FROM Entity ORDER BY IBAN")
    entities = cursor.fetchall()

    cursor.execute("SELECT id, Item FROM Type ORDER BY Item")
    types = cursor.fetchall()

    cursor.execute("SELECT id, Item FROM Class ORDER BY Item")
    classes = cursor.fetchall()

    cursor.execute("SELECT id, Item FROM Category ORDER BY Item")
    categories = cursor.fetchall()

    conn.close()

    # Renderizar la plantilla con los datos
    return render_template('editTransactions.html', 
                          transacciones=transacciones, 
                          entities=entities,
                          types=types,
                          classes=classes,
                          categories=categories,
                          filters=filters)

#####BUDGET
# Nueva ruta para la página de presupuesto
@finance_bp.route('/budget')
def budget():
    conn = get_db_connection_finance()
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    
    # Obtener datos para los selects
    cursor.execute("SELECT id, Item FROM Type ORDER BY Item")
    types = cursor.fetchall()
    
    cursor.execute("SELECT id, Item FROM Class ORDER BY Item")
    classes = cursor.fetchall()
    
    cursor.execute("SELECT id, Item FROM Category ORDER BY Item")
    categories = cursor.fetchall()
    
    conn.close()
    
    return render_template('budget.html', 
                         types=types,
                         classes=classes,
                         categories=categories,
                         current_year=datetime.now().year)

# API para datos del presupuesto (MODIFICADA)
@finance_bp.route('/api/budget/summary')
def budget_summary():
    year = request.args.get('year', str(datetime.now().year))
    
    try:
        conn = get_db_connection_finance()
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        
        print(f"Conectado a la base de datos. Obteniendo datos para el año {year}")  # Log

        # Consulta para resumen de ingresos
        income_summary_query = """
            SELECT Class.Item as class, 
                   Category.Item as category,
                   MONTH(Op_Date) as month,
                   SUM(Amount) as total
            FROM Budget
            LEFT JOIN Class ON Budget.Class = Class.id
            LEFT JOIN Category ON Budget.Category = Category.id
            WHERE YEAR(Op_Date) = %s AND Budget.Type = 'T01'
            GROUP BY Class.Item, Category.Item, MONTH(Op_Date)
            ORDER BY Class.Item, Category.Item
        """
        
        print("Ejecutando consulta de resumen de ingresos...")  # Log
        cursor.execute(income_summary_query, (year,))
        income_summary_data = cursor.fetchall()
        print(f"Obtenidos {len(income_summary_data)} registros de ingresos")  # Log
        
        # Consulta para resumen de gastos
        expense_summary_query = """
            SELECT Class.Item as class, 
                   Category.Item as category,
                   MONTH(Op_Date) as month,
                   SUM(Amount) as total
            FROM Budget
            LEFT JOIN Class ON Budget.Class = Class.id
            LEFT JOIN Category ON Budget.Category = Category.id
            WHERE YEAR(Op_Date) = %s AND Budget.Type = 'T02'
            GROUP BY Class.Item, Category.Item, MONTH(Op_Date)
            ORDER BY Class.Item, Category.Item
        """
        
        print("Ejecutando consulta de resumen de gastos...")  # Log
        cursor.execute(expense_summary_query, (year,))
        expense_summary_data = cursor.fetchall()
        print(f"Obtenidos {len(expense_summary_data)} registros de gastos")  # Log

        # Consultas para detalles
        income_details_query = """
            SELECT 
                DATE_FORMAT(Op_Date, '%%Y-%%m') as month_year,
                MONTH(Op_Date) as month,
                IFNULL(Class.Item, 'Sin clase') as class_name,
                IFNULL(Category.Item, 'Sin categoría') as category_name,
                IFNULL(Project, '') as project,
                IFNULL(Observations, '') as observations,
                Amount as amount
            FROM Budget
            LEFT JOIN Class ON Budget.Class = Class.id
            LEFT JOIN Category ON Budget.Category = Category.id
            WHERE YEAR(Op_Date) = %s AND Budget.Type = 'T01'
            ORDER BY Op_Date ASC
        """

        print("Ejecutando consulta de detalle de ingresos...")  # Log
        cursor.execute(income_details_query, (year,))
        income_detail_data = cursor.fetchall()
        print(f"Obtenidos {len(income_detail_data)} registros de detalle de ingresos")  # Log

        expense_details_query = """
            SELECT 
                DATE_FORMAT(Op_Date, '%%Y-%%m') as month_year, 
                MONTH(Op_Date) as month,
                IFNULL(Class.Item, 'Sin clase') as class_name,
                IFNULL(Category.Item, 'Sin categoría') as category_name,
                IFNULL(Project, '') as project,
                IFNULL(Observations, '') as observations,
                Amount as amount
            FROM Budget
            LEFT JOIN Class ON Budget.Class = Class.id
            LEFT JOIN Category ON Budget.Category = Category.id
            WHERE YEAR(Op_Date) = %s AND Budget.Type = 'T02'
            ORDER BY Op_Date ASC
        """
        
        print("Ejecutando consulta de detalle de gastos...")  # Log
        cursor.execute(expense_details_query, (year,))
        expense_detail_data = cursor.fetchall()
        print(f"Obtenidos {len(expense_detail_data)} registros de detalle de gastos")  # Log
        
        conn.close()
        
        # Mapeo de número de mes a nombre corto
        month_map = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }

        response = {
            'income_summary': [{
                'class': row['class'],
                'category': row['category'],
                'month': int(row['month']),
                'total': float(row['total'])
            } for row in income_summary_data],
            'expense_summary': [{
                'class': row['class'],
                'category': row['category'],
                'month': int(row['month']),
                'total': float(row['total'])
            } for row in expense_summary_data],
            'income_details': [{
                'month_name': month_map.get(int(row['month']), 'Inv'),
                'class_name': row['class_name'],
                'category_name': row['category_name'],
                'project': row['project'],
                'observations': row['observations'],
                'amount': float(row['amount'])
            } for row in income_detail_data],
            'expense_details': [{
                'month_name': month_map.get(int(row['month']), 'Inv'),
                'class_name': row['class_name'],
                'category_name': row['category_name'],
                'project': row['project'],
                'observations': row['observations'],
                'amount': float(row['amount'])
            } for row in expense_detail_data]
        }

        print("Datos preparados para enviar como respuesta")  # Log
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in budget_summary: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

# Ruta para guardar presupuesto
@finance_bp.route('/saveBudget', methods=['POST'])
def save_budget():
    data = request.json
    conn = get_db_connection_finance()
    cursor = conn.cursor()
    
    actualizados = 0
    errores = 0
    
    for item in data:
        try:
            cursor.execute("""
                INSERT INTO Budget (Op_Date, Type, Class, Category, Project, Observations, Amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                item['Date'],
                item['Type'],
                item['Class'],
                item['Category'],
                item['Project'],
                item['Observations'],
                item['Amount']
            ))
            actualizados += 1
        except Exception as e:
            print(f"Error insertando registro: {str(e)}")
            errores += 1
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'mensaje': f'Datos guardados. Correctos: {actualizados}, Errores: {errores}',
        'actualizados': actualizados,
        'errores': errores
    })


# Añadir al blueprint finance
@finance_bp.route('/budgetStatus')
def budget_status():
    return render_template('budgetStatus.html', datetime=datetime)

@finance_bp.route('/api/budget/status')
def api_budget_status_data():
    year_str = request.args.get('year', str(datetime.now().year))
    try:
        year = int(year_str)
    except ValueError:
        year = datetime.now().year

    current_dt = datetime.now()
    current_year = current_dt.year
    current_month = current_dt.month

    try:
        conn = get_db_connection_finance()
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

        budget_query = """
            SELECT 
                IFNULL(c.Item, 'Sin Clase') as class_name, 
                IFNULL(cat.Item, 'Sin Categoría') as category_name,
                MONTH(b.Op_Date) as month,
                SUM(b.Amount) as budget_amount
            FROM Budget b
            LEFT JOIN Class c ON b.Class = c.id
            LEFT JOIN Category cat ON b.Category = cat.id
            WHERE YEAR(b.Op_Date) = %s AND b.Type = 'T02'
            GROUP BY class_name, category_name, month
        """
        cursor.execute(budget_query, (year,))
        budget_items = cursor.fetchall()
        
        actual_query = """
            SELECT
                IFNULL(cl.Item, 'Sin Clase') as class_name,
                IFNULL(ca.Item, 'Sin Categoría') as category_name,
                MONTH(t.Op_Date) as month,
                SUM(t.Amount) as actual_amount
            FROM Transact t
            LEFT JOIN Class cl ON t.Class = cl.id
            LEFT JOIN Category ca ON t.Category = ca.id
            WHERE YEAR(t.Op_Date) = %s AND t.Type = 'T02'
            GROUP BY class_name, category_name, month
        """
        cursor.execute(actual_query, (year,))
        actual_items = cursor.fetchall()
        
        conn.close()

        processed_data = {}
        month_keys_map = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }

        all_keys = set()
        for item in budget_items + actual_items:
            key = f"{item['class_name']} - {item['category_name']}"
            all_keys.add(key)

        for key in all_keys:
            processed_data[key] = {
                month_num: {'budget': 0.0, 'actual': 0.0} for month_num in range(1, 13)
            }
            # No necesitamos 'row_total_budget' y 'row_total_actual' aquí, se calcularán después

        for item in budget_items:
            key = f"{item['class_name']} - {item['category_name']}"
            month = item['month']
            if key in processed_data and month in processed_data[key]:
                processed_data[key][month]['budget'] = float(item['budget_amount'] or 0.0)

        for item in actual_items:
            key = f"{item['class_name']} - {item['category_name']}"
            month = item['month']
            if key in processed_data and month in processed_data[key]:
                processed_data[key][month]['actual'] = abs(float(item['actual_amount'] or 0.0))

        datatables_data = []
        for category_key, monthly_values in processed_data.items():
            row_data = {'category_display_name': category_key}
            
            # Para los totales de la fila (sumando todos los meses, no solo los que tienen presupuesto > 0 para el % total)
            # Estos son los que se mostrarán en las nuevas columnas
            grand_total_row_budget = 0.0
            grand_total_row_actual = 0.0

            # Para el cálculo del porcentaje total de la fila (como antes, solo donde budget > 0)
            percentage_calc_total_budget = 0.0
            percentage_calc_total_actual = 0.0

            for month_num in range(1, 13):
                month_label = month_keys_map[month_num]
                budget_amount_month = monthly_values[month_num]['budget']
                actual_amount_month = monthly_values[month_num]['actual']
                
                row_data[month_label] = {
                    'budget_amount': budget_amount_month,
                    'actual_amount': actual_amount_month,
                    'is_future_month': (year == current_year and month_num > current_month),
                    'is_current_or_past_month': (year < current_year or (year == current_year and month_num <= current_month))
                }
                
                # Sumar para los montos totales de la fila (NUEVAS COLUMNAS)
                # Aquí sumamos todo, independientemente de si es futuro o no,
                # ya que es un total de lo que hay en la BD para el año.
                grand_total_row_budget += budget_amount_month
                grand_total_row_actual += actual_amount_month

                # Acumular para el cálculo del PORCENTAJE TOTAL de la fila (COLUMNA TOTAL %)
                # (misma lógica que antes para esta columna específica)
                if not (year == current_year and month_num > current_month): # No considerar meses futuros
                    if budget_amount_month > 0: 
                        percentage_calc_total_budget += budget_amount_month
                        percentage_calc_total_actual += actual_amount_month
                    # No sumamos gastos sin presupuesto a percentage_calc_total_budget/actual
                    # para no distorsionar el % de cumplimiento.

            # Datos para las NUEVAS COLUMNAS
            row_data['sum_actual_amount_row'] = grand_total_row_actual
            row_data['sum_budget_amount_row'] = grand_total_row_budget

            # Datos para la COLUMNA TOTAL % (como antes)
            if percentage_calc_total_budget > 0:
                row_data['row_total_percentage'] = round((percentage_calc_total_actual / percentage_calc_total_budget) * 100, 1)
            else:
                row_data['row_total_percentage'] = None 

            datatables_data.append(row_data)

        return jsonify(datatables_data)

    except Exception as e:
        current_app.logger.error(f"Error in api_budget_status_data: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'message': 'Error en el servidor al procesar datos del estado del presupuesto.'}), 500