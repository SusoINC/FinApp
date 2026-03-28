# FinApp

**Tu aplicación personal de finanzas, inversiones y gestión de vehículos.**

FinApp es una aplicación web desarrollada en **Flask + Python** que permite gestionar de forma centralizada tus **finanzas personales**, **inversiones** y **vehículos**. Utiliza MySQL como base de datos y plantillas HTML + JavaScript para la interfaz.

---

## ✨ Módulos y Funcionalidades

### 💰 **Módulo Finance** (`finance/`)
Este módulo es el núcleo de la gestión de **finanzas personales**. Está completamente orientado a **transacciones bancarias reales**, categorización y control presupuestario.

**Funcionalidades principales:**

- **Carga masiva de extractos bancarios**  
  - Ruta `/upload`: Permite subir archivos Excel (de bancos como ING, N26, etc.).  
  - Procesa automáticamente columnas: `F. VALOR`, `CATEGORÍA`, `SUBCATEGORÍA`, `DESCRIPCIÓN`, `COMENTARIO`, `IMPORTE (€)`.  
  - Convierte fechas y importes (soporta múltiples formatos: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD).  
  - Inserta los datos en la tabla `Transact`.

- **Categorización inteligente de transacciones**  
  - Ruta `/categorize`: Muestra todas las transacciones sin clasificar (año > 2024 y `Type` vacío).  
  - Permite asignar en lote: `Entity` (cuenta bancaria/IBAN), `Type` (Ingreso/Gasto), `Class`, `Category`, `Detail`, `Company` y `FreeText`.

- **Edición y actualización masiva**  
  - Ruta `/editTransactions`: Filtra y edita transacciones ya clasificadas (por fechas, entidad, tipo, etc.).  
  - Ruta `/actualizar` (POST): Actualiza múltiples transacciones a la vez vía JSON.

- **Dashboard financiero**  
  - Ruta `/dashboard`: Vista principal.  
  - API `/api/dashboard/summary`: Devuelve totales (ingresos, gastos, inversiones), % de transacciones categorizadas, top 10 gastos por categoría y evolución mensual.

- **Gestión de presupuestos**  
  - Ruta `/budget`: Crear y editar presupuestos (tabla `Budget`).  
  - Ruta `/saveBudget`: Guarda presupuestos por mes, clase y categoría.  
  - Ruta `/budgetStatus` + API `/api/budget/status`: Compara **presupuesto vs gasto real** mes a mes, calcula porcentajes de cumplimiento y muestra indicadores visuales.  
  - Incluye `Project` y `Observations` para mayor detalle.

**Tecnología interna**: Usa `pymysql`, `pandas` para procesar Excel, y conexiones específicas `get_db_connection_finance()`.

---

### 📈 **Módulo Investment** (`investment/`)
Módulo dedicado a la **gestión de inversiones** en carteras y activos financieros.

**Funcionalidades principales:**

- **Gestión de carteras y transacciones**  
  - Ruta `/investments`: Página principal.  
  - Muestra listas de **Wallets** (carteras), **Platforms** (brokers/plataformas) y **Symbols** (acciones, ETF, cripto, etc.).  
  - Ruta `/guardar_inversiones` (POST): Guarda **múltiples transacciones** en lote vía JSON.  
    - Campos: `Date`, `Wallet`, `Platform`, `Symbol`, `Amount`, `Fee`, `Shares`.  
    - Inserta en la tabla `WalletTransact`.

- **Análisis de símbolos**  
  - Ruta `/symbolAnalysis`: Página dedicada al análisis de activos.  
  - API `/api/symbols`: Devuelve todos los símbolos activos (`Enabled = 1`) con descripción y **última fecha de transacción** en mercado (`LastDate`).

**Tecnología interna**: Usa conexión específica `get_db_connection_invest()`, manejo robusto de errores JSON y logging detallado.

---

### 🚗 **Módulo Car** (`car/`)
Gestión completa de vehículos (gastos de mantenimiento, combustible, seguros, impuestos, revisiones, etc.).  
*(Módulo básico con estructura similar: rutas y plantillas propias)*

---

### 🧩 **Módulo Core** (`core/`)
Funcionalidades compartidas (conexiones a base de datos, utilidades comunes, etc.).

---

## 🛠️ Tecnologías utilizadas

- **Backend**: Python + Flask (Blueprints por módulo)
- **Base de datos**: MySQL (pymysql)
- **Procesamiento de datos**: pandas
- **Frontend**: HTML (Jinja2 templates), CSS, JavaScript
- **Estructura**: Blueprints independientes (`finance_bp`, `investment_bp`, etc.)

---

## 📁 Estructura del proyecto (resumen)
