let priceChart = null;
let performanceChart = null;
let candlestickChart = null;
let purchaseDates = [];
const chartColors = ['#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f', '#edc948', '#b07aa1'];

// Cargar símbolos al iniciar
document.addEventListener('DOMContentLoaded', function() {
    loadSymbols();
    
    document.getElementById('symbol-select').addEventListener('change', function() {
        if (this.value) {
            loadMetrics(this.value);
            loadHistoricalData(this.value);
        }
    });

    document.getElementById('start-date').addEventListener('change', handleDateChange);
    document.getElementById('end-date').addEventListener('change', handleDateChange);
});

function handleDateChange() {
    const selectedSymbol = document.getElementById('symbol-select').value;
    if (selectedSymbol) {
        loadHistoricalData(selectedSymbol);
    }
}

function loadSymbols() {
    fetch('/investment/api/symbols')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('symbol-select');
            data.forEach(symbol => {
                const option = document.createElement('option');
                option.value = symbol.Symbol;
                option.textContent = `${symbol.Description} (${symbol.Symbol}) - ${symbol.LastDate}`;
                select.appendChild(option);
            });
        });
}

function formatCurrency(amount) {
    const number = parseFloat(amount);
    if (isNaN(number)) {
        return "0,00 €";
    }

    const positiveAmount = Math.abs(number);
    const parts = positiveAmount.toFixed(2).split(".");
    const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    const decimalPart = parts[1];

    return `${integerPart},${decimalPart} €`;
}

function loadMetrics(symbol) {
    fetch(`/investment/api/symbols/${symbol}/metrics`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('latest-close').textContent = formatCurrency(data.last_close);
            document.getElementById('last-year-pct').textContent = `${data.last_year_pct.toFixed(2)}%`;
            document.getElementById('ytd-pct').textContent = `${data.ytd_pct.toFixed(2)}%`;
            document.getElementById('mtd-pct').textContent = `${data.mtd_pct.toFixed(2)}%`;
            document.getElementById('wtd-pct').textContent = `${data.wtd_pct.toFixed(2)}%`;
            document.getElementById('day-pct').textContent = `${data.day_pct.toFixed(2)}%`;
        })
        .catch(error => {
            console.error('Error cargando métricas:', error);
            document.getElementById('latest-close').textContent = '-';
            document.getElementById('last-year-pct').textContent = '-';
            document.getElementById('ytd-pct').textContent = '-';
            document.getElementById('mtd-pct').textContent = '-';
            document.getElementById('wtd-pct').textContent = '-';
            document.getElementById('day-pct').textContent = '-';
        });
}

function loadHistoricalData(symbol) {
    // Primero cargamos los datos históricos completos para el candlestick
    fetch(`/investment/api/symbols/${symbol}/history-full`)
        .then(response => response.json())
        .then(fullData => {
            // Luego cargamos las fechas de compra
            fetch(`/investment/api/symbols/${symbol}/purchases`)
                .then(response => response.json())
                .then(purchases => {
                    purchaseDates = purchases;
                    
                    // Actualizamos el gráfico candlestick con todos los datos
                    updateCandlestickChart(fullData);
                    
                    // Filtramos los datos según los filtros de fecha para los otros gráficos
                    const startDate = document.getElementById('start-date').value;
                    const endDate = document.getElementById('end-date').value;
                    
                    const filteredData = fullData.filter(d => 
                        (!startDate || d.Date >= startDate) && 
                        (!endDate || d.Date <= endDate)
                    );
                    
                    updateCharts(filteredData);
                });
        });
}

function updateCharts(data) {
    updatePriceChart(data);
    updatePerformanceChart(data);
}

function calculateMA(data, windowSize) {
    const result = [];
    for (let i = 0; i < data.length; i++) {
        if (i < windowSize - 1) {
            result.push('-');
            continue;
        }
        let sum = 0;
        for (let j = 0; j < windowSize; j++) {
            sum += data[i - j].Close;
        }
        result.push(+(sum / windowSize).toFixed(2));
    }
    return result;
}

function updateCandlestickChart(data) {
    const chartDom = document.getElementById('candlestick-chart');
    
    if (candlestickChart) {
        candlestickChart.dispose();
    }
    
    candlestickChart = echarts.init(chartDom);
    
    // Ordenar los datos por fecha (por si acaso)
    data.sort((a, b) => new Date(a.Date) - new Date(b.Date));
    
    // Preparar datos para el candlestick
    const dates = data.map(item => item.Date);
    const values = data.map(item => [item.Open, item.Close, item.Low, item.High]);
    const volumes = data.map((item, idx) => [
        idx,
        item.Volume,
        item.Open > item.Close ? 1 : -1
    ]);
    
    // Calcular medias móviles
    const ma5 = calculateMA(data, 5);
    const ma10 = calculateMA(data, 10);
    const ma20 = calculateMA(data, 20);
    const ma30 = calculateMA(data, 30);
    
    const option = {
        backgroundColor: '#fff',
        animation: true,
        legend: {
            data: ['K-line', 'MA5', 'MA10', 'MA20', 'MA30', 'Volumen'],
            inactiveColor: '#777',
            textStyle: {
                color: '#333'
            }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross',
                label: {
                    backgroundColor: '#283b56'
                }
            },
            formatter: function(params) {
                const date = params[0].axisValue;
                const candleData = params[0].data;
                const volumeData = params[1] ? params[1].data : null;
                
                let tooltip = `<div style="font-weight:bold;margin-bottom:5px">${date}</div>`;
                
                if (candleData) {
                    tooltip += `
                        <div>Apertura: ${formatCurrency(candleData[1])}</div>
                        <div>Cierre: ${formatCurrency(candleData[2])}</div>
                        <div>Mínimo: ${formatCurrency(candleData[3])}</div>
                        <div>Máximo: ${formatCurrency(candleData[4])}</div>
                    `;
                }
                
                // Añadir medias móviles
                params.slice(2).forEach(param => {
                    if (param.seriesName.startsWith('MA') && param.data !== '-') {
                        tooltip += `<div>${param.seriesName}: ${formatCurrency(param.data)}</div>`;
                    }
                });
                
                if (volumeData) {
                    tooltip += `<div>Volumen: ${volumeData[1].toLocaleString()}</div>`;
                }
                
                // Marcar días de compra
                if (purchaseDates.includes(date)) {
                    tooltip += '<div style="color:#d62728;margin-top:5px">★ Día de compra</div>';
                }
                
                return tooltip;
            }
        },
        axisPointer: {
            link: { xAxisIndex: 'all' },
            label: {
                backgroundColor: '#283b56'
            }
        },
        grid: [
            {
                left: '10%',
                right: '8%',
                height: '60%'
            },
            {
                left: '10%',
                right: '8%',
                top: '75%',
                height: '15%'
            }
        ],
        xAxis: [
            {
                type: 'category',
                data: dates,
                scale: true,
                boundaryGap: false,
                axisLine: { onZero: false },
                splitLine: { show: false },
                splitNumber: 20,
                min: 'dataMin',
                max: 'dataMax',
                axisPointer: {
                    z: 100
                }
            },
            {
                type: 'category',
                gridIndex: 1,
                data: dates,
                scale: true,
                boundaryGap: false,
                axisLine: { onZero: false },
                axisTick: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false },
                min: 'dataMin',
                max: 'dataMax'
            }
        ],
        yAxis: [
            {
                scale: true,
                splitArea: {
                    show: true
                },
                axisLabel: {
                    formatter: function(value) {
                        return formatCurrency(value);
                    }
                }
            },
            {
                scale: true,
                gridIndex: 1,
                splitNumber: 2,
                axisLabel: { show: false },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { show: false }
            }
        ],
        dataZoom: [
            {
                type: 'inside',
                xAxisIndex: [0, 1],
                start: 80,
                end: 100
            },
            {
                show: true,
                xAxisIndex: [0, 1],
                type: 'slider',
                bottom: 10,
                start: 80,
                end: 100
            }
        ],
        series: [
            {
                name: 'K-line',
                type: 'candlestick',
                data: values,
                itemStyle: {
                    color: '#e15759',
                    color0: '#59a14f',
                    borderColor: '#e15759',
                    borderColor0: '#59a14f'
                },
                markPoint: {
                    data: purchaseDates.map(date => {
                        const idx = dates.indexOf(date);
                        if (idx !== -1) {
                            return {
                                name: 'Compra',
                                coord: [date, values[idx][1]], // Usamos el precio de cierre
                                value: values[idx][1],
                                symbol: 'pin',
                                symbolSize: 16,
                                itemStyle: {
                                    color: '#d62728'
                                },
                                label: {
                                    formatter: 'Compra',
                                    position: 'top'
                                }
                            };
                        }
                        return null;
                    }).filter(Boolean)
                }
            },
            {
                name: 'MA5',
                type: 'line',
                data: ma5,
                smooth: true,
                lineStyle: {
                    opacity: 0.8,
                    width: 1
                },
                symbol: 'none'
            },
            {
                name: 'MA10',
                type: 'line',
                data: ma10,
                smooth: true,
                lineStyle: {
                    opacity: 0.8,
                    width: 1
                },
                symbol: 'none'
            },
            {
                name: 'MA20',
                type: 'line',
                data: ma20,
                smooth: true,
                lineStyle: {
                    opacity: 0.8,
                    width: 1
                },
                symbol: 'none'
            },
            {
                name: 'MA30',
                type: 'line',
                data: ma30,
                smooth: true,
                lineStyle: {
                    opacity: 0.8,
                    width: 1
                },
                symbol: 'none'
            },
            {
                name: 'Volumen',
                type: 'bar',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: volumes,
                itemStyle: {
                    color: function(params) {
                        const colorList = params.data[2] > 0 ? '#e15759' : '#59a14f';
                        return colorList;
                    }
                }
            }
        ]
    };
    
    candlestickChart.setOption(option);
    
    window.addEventListener('resize', function() {
        candlestickChart.resize();
    });
}

function updatePriceChart(data) {
    const chartDom = document.getElementById('price-chart');
    
    if (priceChart) {
        priceChart.dispose();
    }
    
    priceChart = echarts.init(chartDom);
    
    // Preparamos los datos para las marcas
    const markPoints = [];
    data.forEach((d, index) => {
        if (purchaseDates.includes(d.Date)) {
            markPoints.push({
                name: 'Buy',
                coord: [d.Date, d.Close],
                value: d.Close,
                symbol: 'pin',
                symbolSize: 16,
                itemStyle: {
                    color: '#d62728'
                },
                label: {
                    formatter: 'Buy',
                    position: 'top'
                }
            });
        }
    });
    
    const option = {
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                let tooltip = `${params[0].axisValue}<br/>${params[0].marker} ${params[0].seriesName}: ${formatCurrency(params[0].data)}`;
                
                if (params[0].dataIndex !== undefined) {
                    const pointDate = data[params[0].dataIndex].Date;
                    if (purchaseDates.includes(pointDate)) {
                        tooltip += '<br/><span style="color:#d62728">★ Día de compra</span>';
                    }
                }
                
                return tooltip;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: data.map(d => d.Date)
        },
        yAxis: {
            type: 'value',
            axisLabel: {
                formatter: function(value) {
                    return formatCurrency(value);
                }
            }
        },
        series: [
            {
                name: 'Close Price',
                type: 'line',
                smooth: true,
                lineStyle: {
                    color: chartColors[0],
                    width: 3
                },
                itemStyle: {
                    color: chartColors[0]
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {
                            offset: 0,
                            color: chartColors[0] + '80'
                        },
                        {
                            offset: 1,
                            color: chartColors[0] + '00'
                        }
                    ])
                },
                data: data.map(d => d.Close),
                markPoint: {
                    data: markPoints,
                    symbol: 'pin',
                    symbolSize: 16,
                    label: {
                        show: true,
                        formatter: '{b}',
                        position: 'top'
                    },
                    itemStyle: {
                        color: '#d62728'
                    },
                    emphasis: {
                        label: {
                            show: true
                        }
                    }
                }
            }
        ]
    };
    
    priceChart.setOption(option);
    
    window.addEventListener('resize', function() {
        priceChart.resize();
    });
}

function updatePerformanceChart(data) {
    const chartDom = document.getElementById('performance-chart');
    
    if (performanceChart) {
        performanceChart.dispose();
    }
    
    performanceChart = echarts.init(chartDom);
    
    const baseValue = data[0]?.Close || 1;
    const performanceData = data.map(d => ((d.Close - baseValue) / baseValue * 100).toFixed(2));
    
    const option = {
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                return `${params[0].axisValue}<br/>${params[0].marker} ${params[0].seriesName}: ${params[0].data}%`;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: data.map(d => d.Date)
        },
        yAxis: {
            type: 'value',
            axisLabel: {
                formatter: '{value}%'
            }
        },
        series: [
            {
                name: 'Variación %',
                type: 'line',
                smooth: true,
                lineStyle: {
                    color: chartColors[1],
                    width: 3
                },
                itemStyle: {
                    color: chartColors[1]
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {
                            offset: 0,
                            color: chartColors[1] + '80'
                        },
                        {
                            offset: 1,
                            color: chartColors[1] + '00'
                        }
                    ])
                },
                data: performanceData
            }
        ]
    };
    
    performanceChart.setOption(option);
    
    window.addEventListener('resize', function() {
        performanceChart.resize();
    });
}