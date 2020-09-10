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
        textposition: "none",
        marker: {
            colors: colorGradient
        },
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
    htmlElement.innerHTML = '';
    Plotly.newPlot(htmlElement, data, layout, config);
}


/**
 *
 * @param elementId
 * @param labels
 * @param values
 * @returns
 */
function createSparkDiagram(elementId, labels, values, lineColor, fillColor, diagramType) {
    diagramType = diagramType || 'lines'
    let trace = {
	    x: labels,
	    y: values,
        line: {
	        color: lineColor,
	        width: 2
        },
        marker: {
	        color: lineColor
        },
    }
    if (diagramType == 'bars') {
        trace['type'] = 'bar'
    } else {
        trace['type'] = 'scatter'
        trace['mode'] = 'lines'
    }
    if (fillColor) {
        trace['fill'] = 'tozeroy';
        trace['fillcolor'] = fillColor;
    }
    let data = [trace];

    // Layout of the chart
    let layout = {
        showlegend: false,
        xaxis: {
            showgrid: false,
            zeroline: false,
            showticklabels: false,
            showline: true,
            fixedrange: true,
            ticks: 'outside',
            tickwidth: 2,
            ticklen: 5,
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
            r: 0,
            t: 0,
            b: 50,
        }
    }

    // General chart configuration
    let config = {
        displayModeBar: false,
        responsive: true
    }

    let htmlElement = document.getElementById(elementId);
    htmlElement.innerHTML = '';
    Plotly.newPlot(htmlElement, data, layout, config);
}
