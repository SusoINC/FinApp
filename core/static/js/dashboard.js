// Variables globales para los gráficos
let categoriesChart = null;
let monthlyChart = null;

// Colores para los gráficos
const chartColors = [
    '#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f',
    '#edc949', '#af7aa1', '#ff9da7', '#9c755f', '#bab0ab'
];

// Función para formatear números como moneda
function formatCurrency(amount) {
    // Asegurar que el valor sea un número válido
    const number = parseFloat(amount);
    if (isNaN(number)) {
        return "0,00 €"; // Valor por defecto si no es un número válido
    }

    // Tomar el valor absoluto para asegurar que sea positivo
    const positiveAmount = Math.abs(number);

    // Formatear el número con separador de miles (.) y dos decimales (,)
    const parts = positiveAmount.toFixed(2).split(".");
    const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    const decimalPart = parts[1];

    return `${integerPart},${decimalPart} €`;
}

// Función para cargar los datos del dashboard
function loadDashboardData() {
    // Mostrar estado de carga
    document.getElementById('total-amount').textContent = "Cargando...";
    document.getElementById('income-amount').textContent = "Cargando...";
    document.getElementById('expense-amount').textContent = "Cargando...";
    document.getElementById('investments-amount').textContent = "Cargando...";
    document.getElementById('quality-amount').textContent = "Cargando...";
    
    // Obtener valores de los filtros
    const yearSelect = document.getElementById('year-filter');
    const year = yearSelect.value || (yearSelect.options.length > 0 ? yearSelect.options[0].value : '2025');
    
    const month = document.getElementById('month-filter').value;
    const entity = document.getElementById('entity-filter').value;
    const type = document.getElementById('type-filter').value;
    
    // Construir URL con parámetros de filtro
    let url = `/api/dashboard/summary?year=${year}`;
    if (month) url += `&month=${month}`;
    if (entity) url += `&entity=${entity}`;
    if (type) url += `&type=${type}`;
    
    // Realizar la petición AJAX
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Datos recibidos:", data);
            
            // Verificar si hay un error en la respuesta
            if (data.error) {
                console.error("Error del servidor:", data.error);
                alert("Error al cargar los datos: " + data.error);
            }
            
            // Actualizar tarjetas de resumen
            document.getElementById('total-amount').textContent = formatCurrency(data.summary.total);
            document.getElementById('income-amount').textContent = formatCurrency(data.summary.income);
            document.getElementById('expense-amount').textContent = formatCurrency(data.summary.expense);
            document.getElementById('investments-amount').textContent = formatCurrency(data.summary.investments);
            document.getElementById('quality-amount').textContent = `${data.summary.quality}%`;
            
            // Actualizar gráficos
            updateCategoriesChart(data.categories);
            updateMonthlyChart(data.monthly);
            
            // Llenar selectores de filtro
            updateFilterOptions(data.filters);
        })
        .catch(error => {
            console.error('Error al cargar los datos del dashboard:', error);
            document.getElementById('total-amount').textContent = "Error de carga";
            document.getElementById('income-amount').textContent = "Error de carga";
            document.getElementById('expense-amount').textContent = "Error de carga";
            document.getElementById('investments-amount').textContent = "Error de carga";
            document.getElementById('quality-amount').textContent = "Error de carga";
            
            // Mostrar mensaje de error en la página
            alert("Error al cargar los datos del dashboard. Consulte la consola para más detalles.");
        });
}

// Función para actualizar las opciones de los filtros
function updateFilterOptions(filters) {
    // Llenar selector de años
    const yearFilter = document.getElementById('year-filter');
    if (yearFilter.options.length <= 1) {  // Solo actualizar si no está ya lleno
        console.log("Actualizando opciones de años:", filters.years);
        yearFilter.innerHTML = ''; // Limpiar opciones existentes
        
        filters.years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearFilter.appendChild(option);
        });
        
        // Seleccionar el primer año si no hay uno seleccionado
        if (yearFilter.value === "" && yearFilter.options.length > 0) {
            yearFilter.value = yearFilter.options[0].value;
        }
    }
    
    // Llenar selector de entidades
    const entityFilter = document.getElementById('entity-filter');
    if (entityFilter.options.length <= 1) {  // Solo la opción "Todas"
        console.log("Actualizando opciones de entidades:", filters.entities);
        
        // Mantener la opción "Todas"
        const allOption = document.createElement('option');
        allOption.value = "";
        allOption.textContent = "Todas";
        
        entityFilter.innerHTML = ''; // Limpiar opciones existentes
        entityFilter.appendChild(allOption);
        
        if (filters.entities && filters.entities.length > 0) {
            filters.entities.forEach(entity => {
                const option = document.createElement('option');
                option.value = entity.id;
                option.textContent = entity.IBAN;
                entityFilter.appendChild(option);
            });
        }
    }
    
    // Llenar selector de tipos
    const typeFilter = document.getElementById('type-filter');
    if (typeFilter.options.length <= 1) {  // Solo la opción "Todos"
        console.log("Actualizando opciones de tipos:", filters.types);
        
        // Mantener la opción "Todos"
        const allOption = document.createElement('option');
        allOption.value = "";
        allOption.textContent = "Todos";
        
        typeFilter.innerHTML = ''; // Limpiar opciones existentes
        typeFilter.appendChild(allOption);
        
        if (filters.types && filters.types.length > 0) {
            filters.types.forEach(type => {
                const option = document.createElement('option');
                option.value = type.id;
                option.textContent = type.Item;
                typeFilter.appendChild(option);
            });
        }
    }
}

// Función para actualizar el gráfico de categorías
function updateCategoriesChart(categories) {
    const ctx = document.getElementById('categories-chart').getContext('2d');
    
    // Verificar si hay datos
    if (!categories || categories.length === 0) {
        categories = [{ category: 'Sin datos', amount: 100 }];
    }
    
    // Preparar datos para el gráfico
    const labels = categories.map(item => item.category || 'Sin categoría');
    const amounts = categories.map(item => Math.abs(parseFloat(item.amount) || 0)); // Valor absoluto para visualización
    
    // Destruir gráfico anterior si existe
    if (categoriesChart) {
        categoriesChart.destroy();
    }
    
    // Crear nuevo gráfico
    categoriesChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: amounts,
                backgroundColor: chartColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            return `${context.label}: ${formatCurrency(value)}`;
                        }
                    }
                }
            }
        }
    });
}

// Función para actualizar el gráfico mensual
function updateMonthlyChart(monthlyData) {
    const ctx = document.getElementById('monthly-chart').getContext('2d');
    
    // Verificar si hay datos
    if (!monthlyData || monthlyData.length === 0) {
        monthlyData = Array.from({length: 12}, (_, i) => ({ month: i+1, income: 0, expense: 0 }));
    }
    
    // Mapear números de mes a nombres
    const monthNames = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ];
    
    // Organizar datos mensuales
    const organizedData = Array.from({length: 12}, (_, i) => ({ month: i+1, income: 0, expense: 0 }));
    monthlyData.forEach(item => {
        const monthIndex = parseInt(item.month) - 1;
        if (monthIndex >= 0 && monthIndex < 12) {
            organizedData[monthIndex].income = parseFloat(item.income) || 0;
            organizedData[monthIndex].expense = parseFloat(item.expense) || 0;
        }
    });
    
    // Preparar datos para el gráfico
    const labels = organizedData.map(item => monthNames[item.month - 1]);
    const incomeData = organizedData.map(item => item.income > 0 ? item.income : 0);
    const expenseData = organizedData.map(item => item.expense < 0 ? Math.abs(item.expense) : 0);
    
    // Destruir gráfico anterior si existe
    if (monthlyChart) {
        monthlyChart.destroy();
    }
    
    // Crear nuevo gráfico
    monthlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Ingresos',
                    data: incomeData,
                    backgroundColor: '#59a14f',
                    borderWidth: 1
                },
                {
                    label: 'Gastos',
                    data: expenseData,
                    backgroundColor: '#e15759',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    stacked: false,
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            return `${context.dataset.label}: ${formatCurrency(value)}`;
                        }
                    }
                }
            }
        }
    });
}

// Inicializar el dashboard cuando se cargue la página
document.addEventListener('DOMContentLoaded', function() {
    console.log("Inicializando dashboard...");
    
    // Cargar datos iniciales
    loadDashboardData();
    
    // Agregar eventos de cambio a los filtros
    document.getElementById('year-filter').addEventListener('change', loadDashboardData);
    document.getElementById('month-filter').addEventListener('change', loadDashboardData);
    document.getElementById('entity-filter').addEventListener('change', loadDashboardData);
    document.getElementById('type-filter').addEventListener('change', loadDashboardData);
});