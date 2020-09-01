/**
 * Create diagram for evolution of issues
 */
function createEvolutionOfIssuesDiagram(metrics) {
    metrics = window.projectMetrics // TODO: make loading of data more stable

    let htmlElement = document.getElementById('evolution-issues-diagram');

    let layout = {
        showlegend: true,
        legend: {
            orientation: "h"
        },
        yaxis: {
            showgrid: false,
            zeroline: false,
            showline: false,
            showticklabels: false
        },
        yaxis2: {
            showgrid: false,
            zeroline: false,
            showline: false,
            showticklabels: false,
            anchor: 'free',
            overlaying: 'y'
        },
        yaxis3: {
            showgrid: false,
            zeroline: false,
            showline: false,
            showticklabels: false,
            anchor: 'free',
            overlaying: 'y'
        },
        margin: {
            l: 0,
            r: 0,
            t: 0,
            b: 0
        },
    }

    let xData = [];
    let complexityData = [];
    let issuesClosedData = [];
    let issueAgeData = [];

    for(let i in metrics) {
        xData.push(metrics[i]['date'])
        complexityData.push(metrics[i]['complexity'])
        issuesClosedData.push(metrics[i]['github_issues_closed'])
        issueAgeData.push(metrics[i]['github_issue_age'])
    }

    let complexity = {
	    x: xData,
	    y: complexityData,
        name: 'Complexity',
        type: 'scatter',
        mode: 'lines',
        line: {
	        width: 0
        },
        fill: 'tozeroy',
        fillcolor: '#ddd'
    }

    let issues_closed = {
	    x: xData,
	    y: issuesClosedData,
        name: 'Issue Closed',
        type: 'bar',
        yaxis: 'y2',
        marker: {
	        color: chart_colors[1]
        },
    }

    let issue_age = {
	    x: xData,
	    y: issueAgeData,
        name: 'Issue Age',
        mode: 'lines+markers',
        yaxis: 'y3',
        marker: {
	        color: chart_colors[0],
	        size: 10
        },
        line: {
	        color: chart_colors[0]
        }
    }

    let data = [complexity, issues_closed, issue_age]

	Plotly.newPlot(htmlElement, data, layout);
}

/**
 * Create a bubble diagram displaying the complexity and change frequency of
 * all the files in the source tree
 */
function createEvolutionDiagram(elementId, labels, values1, values2, values3, values4,
                                releases, evolutionChartFrequency) {
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
            data: values1,
            fill: false,
            borderColor: chart_colors[0],
            borderDash: [10, 5],
            backgroundColor: chart_colors[0],
            pointRadius: 4,
            lineTension: 0,
            cubicInterpolationMode: 'monotone',
            yAxisID: "y-axis-0",
        }, {
            label: 'Avg age of PRs (in hours)',
            type: 'line',
            data: values4,
            fill: false,
            borderColor: chart_colors[3],
            backgroundColor: chart_colors[3],
            lineTension: 0,
            yAxisID: "y-axis-3",
        }, {
            label: 'Number of issues closed',
            data: values2,
            fill: false,
            borderColor: chart_colors[1],
            backgroundColor: chart_colors[1],
            lineTension: 0,
            yAxisID: "y-axis-1",
        }, {
            label: 'Number of PRs merged',
            data: values3,
            fill: false,
            borderColor: chart_colors[2],
            backgroundColor: chart_colors[2],
            lineTension: 0,
            yAxisID: "y-axis-2",
        }]
    };

    const toolTipLabels = {
        0: 'Complexity',
        1: 'Issues Closed: ',
        2: 'PRs Merged: ',
        3: 'Avg PR Age [h]: '
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
                }, {
                    "id": "y-axis-3",
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
                        let out = toolTipLabels[tooltipItem.datasetIndex];
                        if(tooltipItem.datasetIndex>0) {
                            out += tooltipItem.yLabel.toFixed(0);
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
