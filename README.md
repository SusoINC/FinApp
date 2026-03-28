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

## 📁 Estructura del proyecto (Technical info)

## 🏗️ Arquitectura y Detalles Técnicos por Módulo

El proyecto está diseñado bajo una arquitectura modular para separar lógicas de negocio, facilitar la escalabilidad y mantener un código limpio. La aplicación se divide en los siguientes submódulos principales:

### ⚙️ `core/` (Núcleo y Autenticación)
Este es el motor base de la aplicación.
* **Responsabilidad:** Gestiona la configuración central, la conexión a la base de datos y la seguridad.
* **Técnico:** Aquí se implementan los controladores para el registro, *login* y manejo de sesiones de usuario (middlewares o decoradores de autenticación). También centraliza el enrutamiento hacia las vistas de inicio (*Dashboards* globales) y el manejo de errores HTTP (404, 500).

### 🏦 `finance/` (Módulo Financiero)
Encargado de la lógica transaccional del día a día.
* **Responsabilidad:** Procesar y almacenar el flujo de caja del usuario.
* **Técnico:** Implementa operaciones CRUD (Crear, Leer, Actualizar, Borrar) para ingresos y gastos. Utiliza modelos relacionales para vincular transacciones con categorías personalizadas y usuarios. Prepara consultas de agregación (GROUP BY, SUM) en la base de datos para enviar datos estructurados al frontend y renderizar gráficos de balance.

### 📈 `investment/` (Módulo de Inversiones)
Maneja la lógica compleja de cálculo de rentabilidades y seguimiento de activos.
* **Responsabilidad:** Calcular el valor del portafolio en tiempo real y registrar el histórico de operaciones.
* **Técnico:** Este módulo estructura modelos de datos específicos para diferentes tipos de activos (acciones, criptos, fondos). Probablemente se integre con APIs externas financieras para obtener cotizaciones actualizadas. Contiene la lógica matemática para calcular métricas como el ROI (Retorno de Inversión), el precio medio de compra (DCA) y la distribución del portafolio.

### 🚗 `car/` (Módulo de Vehículos)
Un micro-gestor de flotas orientado al usuario final.
* **Responsabilidad:** Calcular la eficiencia del vehículo y predecir mantenimientos.
* **Técnico:** Gestiona entidades de vehículos y registros dependientes (repostajes, facturas de taller). Incluye lógica de cálculo para determinar el consumo medio (ej. litros/100km o km/litro) basado en el odómetro y el volumen de combustible. Puede incluir funciones de comparación de fechas para generar alertas de vencimiento (ITV, seguro).

### 🤖 `autoRun/` (Automatización y Tareas en Segundo Plano)
Maneja los procesos desatendidos del servidor.
* **Responsabilidad:** Mantener los datos actualizados sin requerir la interacción directa del usuario.
* **Técnico:** Contiene *scripts* ejecutables de Python diseñados para correr como tareas programadas (cron jobs) o procesos en segundo plano. Ejemplos de uso: consultar APIs de bolsa diariamente al cierre del mercado, realizar copias de seguridad de la base de datos de SQLite/PostgreSQL, o generar y enviar notificaciones por correo electrónico.

### 🎨 `templates/` y `static/` (Frontend y Capa de Presentación)
La interfaz de usuario y la experiencia visual.
* **Responsabilidad:** Renderizar los datos del backend de forma interactiva y *responsive*.
* **Técnico:** * `templates/`: Utiliza un motor de plantillas (como Jinja2) para realizar *Server-Side Rendering (SSR)*, inyectando variables dinámicas y estructuras de control (bucles `for`, condicionales `if`) directamente en el HTML.
  * `static/`: Sirve los *assets* estáticos. Utiliza JavaScript (posiblemente con librerías como Chart.js o similar) para peticiones asíncronas (AJAX/Fetch) que actualizan los datos de la interfaz sin recargar la página, y CSS para el diseño de la cuadrícula y adaptabilidad a dispositivos móviles.
