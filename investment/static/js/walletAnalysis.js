let priceChart = null;
let performanceChart = null;
const chartColors = ['#4e79a7', '#f28e2c'];

// Cargar símbolos al iniciar
document.addEventListener('DOMContentLoaded', function() {
    loadWalletsAndPlatforms();
    
    document.getElementById('wallet-select').addEventListener('change', function() {
        if (this.value) {
            loadMetrics(this.value);
            loadHistoricalData(this.value);
        }
    });

    document.getElementById('start-date').addEventListener('change', updateCharts);
    document.getElementById('end-date').addEventListener('change', updateCharts);
});

function loadWalletsAndPlatforms() {
    fetch('/investment/api/WalletsAndPlatforms')
        .then(response => response.json())
        .then(data => {
            // Cargar wallets
            const walletSelect = document.getElementById('wallet-select');
            data.wallets.forEach(wallet => {
                const option = document.createElement('option');
                option.value = wallet.id;
                option.textContent = `${wallet.Description || wallet.Name} (${wallet.id})`;
                walletSelect.appendChild(option);
            });

            // Cargar plataformas
            const platformSelect = document.getElementById('platform-select');
            // Limpiar opciones existentes (excepto la primera opción "Todas")
            while (platformSelect.options.length > 1) {
                platformSelect.remove(1);
            }
            
            data.platforms.forEach(platform => {
                const option = document.createElement('option');
                option.value = platform.id;
                option.textContent = platform.Name;
                platformSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error cargando datos:', error);
        });
}

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

function loadMetrics(symbol) {
    fetch(`/investment/api/symbols/${symbol}/metrics`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('amount-invested').textContent = formatCurrency(data.last_close);
            document.getElementById('symbols-count').textContent = `${data.last_year_pct.toFixed(2)}%`;
            document.getElementById('platform-count').textContent = `${data.ytd_pct.toFixed(2)}%`;
            document.getElementById('amount-available').textContent = `${data.mtd_pct.toFixed(2)}%`;
            document.getElementById('performance').textContent = `${data.wtd_pct.toFixed(2)}%`;
            document.getElementById('anual-performance').textContent = `${data.day_pct.toFixed(2)}%`;
        })
        .catch(error => {
            console.error('Error cargando métricas:', error);
            // Mostrar valores por defecto en caso de error
            document.getElementById('amount-invested').textContent = '-';
            document.getElementById('symbols-count').textContent = '-';
            document.getElementById('platform-count').textContent = '-';
            document.getElementById('amount-available').textContent = '-';
            document.getElementById('performance').textContent = '-';
            document.getElementById('anual-performance').textContent = '-';
        });
}

function loadHistoricalData(symbol) {
    fetch(`/investment/api/symbols/${symbol}/history`)
        .then(response => response.json())
        .then(data => {
            updateCharts(data);
        });
}

function updateCharts(data) {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    // Filtrar datos por fecha
    const filteredData = data.filter(d => 
        (!startDate || d.Date >= startDate) && 
        (!endDate || d.Date <= endDate)
    );

    // Actualizar gráfico de precios
    updatePriceChart(filteredData);
    
    // Actualizar gráfico de rendimiento
    updatePerformanceChart(filteredData);
}

function updatePriceChart(data) {
    const ctx = document.getElementById('price-chart').getContext('2d');
    if (priceChart) priceChart.destroy();

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.Date),
            datasets: [{
                label: 'Close Price',
                data: data.map(d => d.Close),
                borderColor: chartColors[0],
                tension: 0.1
            }]
        }
    });
}

function updatePerformanceChart(data) {
    const ctx = document.getElementById('performance-chart').getContext('2d');
    if (performanceChart) performanceChart.destroy();

    const baseValue = data[0]?.Close || 1;
    const performanceData = data.map(d => ((d.Close - baseValue) / baseValue * 100).toFixed(2));

    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.Date),
            datasets: [{
                label: 'Variación %',
                data: performanceData,
                borderColor: chartColors[1],
                tension: 0.1
            }]
        },
        options: {
            scales: {
                y: {
                    ticks: {
                        callback: value => `${value}%`
                    }
                }
            }
        }
    });
}