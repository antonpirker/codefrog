/**
 *
 * @param elementId
 * @param datasetLabel
 * @param labels
 * @param values
 * @returns {Chart}
 */
function createPieChart(elementId, labels, values) {
    colors = [];
    window.usedColors = [];
    window.labelColors = {};

    for(const label of labels) {
        let nextColor = null;
        // find an unused color
        for(nextColor of window.chartColors) {
            if(window.usedColors.indexOf(nextColor) == -1) {
                window.usedColors.push(nextColor);
                break;
            }
        }

        // if the label has not yet a color, assign the unused one.
        if(!window.labelColors[label]) {
            window.labelColors[label] = nextColor;
        }

        // add the assigned color
        colors.push(window.labelColors[label]);
    }

    let config = {
        type: 'pie',
        data: {
            datasets: [{
                data: values,
                backgroundColor: colors,
            }],
            labels: labels,
        },
        options: {
            responsive: true,
            legend: {
                position: 'right'
            }
        }
    };

    let ctx = document.getElementById(elementId).getContext('2d');
    return new Chart(ctx, config);
}


/**
 *
 * @param elementId
 * @param datasetLabel
 * @param labels
 * @param values
 * @returns {Chart}
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
