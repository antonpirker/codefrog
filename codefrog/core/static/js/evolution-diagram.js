/**
 * Create a bubble diagram displaying the complexity and change frequency of
 * all the files in the source tree
 */
function createEvolutionDiagram(elementId, labels, complexityValues, issuesClosed,
                                leadTimes, releases, evolutionChartFrequency) {
    let releaseAnnotations = [];
    for (const release of releases) {
        releaseAnnotations.push({
            type: "line",
            mode: "vertical",
            scaleID: "x-axis-0",
            value: release.date,
            borderColor: "red",
            label: {
                content: release.name,
                enabled: true,
                position: "bottom"
            }
        });
    }

    const data = {
        labels: labels,
        datasets: [{
            label: 'Complexity of the code base',
            type: 'line',
            data: complexityValues,
            fill: false,
            borderColor: chart_colors[0],
            borderDash: [10, 5],
            backgroundColor: chart_colors[0],
            pointRadius: 4,
            lineTension: 0,
            cubicInterpolationMode: 'monotone',
            yAxisID: "y-axis-0",
        }, {
            label: 'Number of issues closed',
            data: issuesClosed,
            fill: false,
            borderColor: chart_colors[1],
            backgroundColor: chart_colors[1],
            lineTension: 0,
            yAxisID: "y-axis-1",
        }, {
            label: 'Lead Time (Days to close issues)',
            data: leadTimes,
            fill: false,
            borderColor: chart_colors[2],
            backgroundColor: chart_colors[2],
            lineTension: 0,
            yAxisID: "y-axis-2",
        }]
    };

    const timeUnits = {
        'D': 'day',
        'W': 'week',
        'M': 'month',
        'Q': 'quarter'
    };
    let timeUnit = timeUnits[evolutionChartFrequency] || 'day';

    const options = {
        type: 'bar',
        data: data,
        options: {
            fill: false,
            responsive: true,
            maintainAspectRatio: false,
            onClick: function(event, elements) {
                if(elements.length > 0) {
                    count('project.evolution.diagram.chart.clicked');
                } else {
                    count('project.evolution.diagram.chrome.clicked');
                }
            },
            scales: {
                xAxes: [{
                    "id": "x-axis-0",
                    type: 'time',
                    offset: true,
                    distribution: 'linear',
                    ticks: {
                        source: evolutionChartFrequency === 'Q' ? 'labels' : 'auto',
                    },
                    time: {
                        parser: 'YYYY-MM-DD HH:mm:ss',
                        unit: timeUnit,
                        displayFormats: {
                            day: 'LL',
                            week: '[Week] WW - YYYY',
                            month: 'MMM YYYY',
                            quarter: '[Q]Q - YYYY',
                            year: 'YYYY'
                        },
                    },
                    scaleLabel: {
                        display: true,
                        labelString: "Date",
                    }
                }],
                yAxes: [{
                    "id": "y-axis-0",
                    display: false
                }, {
                    "id": "y-axis-1",
                    display: false,
                    ticks: {
                        beginAtZero: true
                    }
                }, {
                    "id": "y-axis-2",
                    display: false,
                    ticks: {
                        beginAtZero: true
                    }
                }]
            },
            legend: {
                position: 'bottom'
            },
            annotation: {
                annotations: releaseAnnotations
            },
            tooltips: {
                mode: 'index',
                intersect: false,
                callbacks: {
                    title: function (tooltipItem, data) {
                        const formatStrings = {
                            'D': 'LL',
                            'W': '[Week] WW - YYYY',
                            'M': 'MMM YYYY',
                            'Q': '[Q]Q - YYYY'
                        };
                        let date = moment(tooltipItem[0].xLabel);
                        title = date.format(formatStrings[evolutionChartFrequency] || 'D');
                        return title;
                    },
                    label: function (tooltipItem, data) {
                        const COMPLEXITY = 0;
                        const ISSUES_CLOSED = 1;
                        const LEAD_TIME = 2;

                        let out = '';

                        if (tooltipItem.datasetIndex === LEAD_TIME) {
                            out += 'Lead Time (in Days): ' + tooltipItem.yLabel.toFixed(1);

                        } else if (tooltipItem.datasetIndex === ISSUES_CLOSED) {
                            out += 'Issues Closed: ' + tooltipItem.yLabel.toFixed(0);

                        } else if (tooltipItem.datasetIndex === COMPLEXITY) {
                            out += 'Complexity';
                        }

                        return out;
                    }
                }
            }
        }
    };

    const ctx = document.getElementById(elementId).getContext('2d');
    return new Chart(ctx, options);
}
