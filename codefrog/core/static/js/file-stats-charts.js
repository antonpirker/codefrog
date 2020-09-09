/**
 *
 * @param elementId
 * @param labels
 * @param values
 * @returns
 */
function createPieChart(elementId, labels, values) {
    let trace = {
	    labels: labels,
	    values: values,
        type: 'pie',
        textinfo: "label",
        textposition: "none"
    }
    let data = [trace];

    // Layout of the chart
    let layout = {
        legend: {
            orientation: "h"
        },
        margin: {
            l: 0,
            r: 0,
            t: 0,
            b: 0
        }
    }

    // General chart configuration
    let config = {
        displayModeBar: false
    }

    let htmlElement = document.getElementById(elementId);
    Plotly.newPlot(htmlElement, data, layout, config);
}


/**
 *
 * @param elementId
 * @param labels
 * @param values
 * @returns
 */
function createSparkline(elementId, labels, values) {
    let trace = {
	    x: labels,
	    y: values,
        type: 'scatter',
        mode: 'lines'
    }
    let data = [trace];

    // Layout of the chart
    let layout = {
        showlegend: false,
        xaxis: {
            showgrid: false,
            zeroline: false,
            showline: false,
            showticklabels: false,
            fixedrange: true
        },
        yaxis: {
            showgrid: false,
            zeroline: false,
            showline: false,
            showticklabels: false,
            fixedrange: true
        },
        margin: {
            l: 0,
            r: 0
        }
    }

    // General chart configuration
    let config = {
        displayModeBar: false
    }

    let htmlElement = document.getElementById(elementId);
    Plotly.newPlot(htmlElement, data, layout, config);
}
