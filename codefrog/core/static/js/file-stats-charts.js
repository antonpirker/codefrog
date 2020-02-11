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
    let config = {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                fill: false,
                borderColor: '#999',
                backgroundColor: '#999',
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            scales: {
                xAxes: [{
                    display: false
                }],
                yAxes: [{
                    display: false
                }]
            },
            legend: {
                display: false
            },
            tooltips: {
                enabled: false
            },
            layout: {
                padding: {
                    left: 10,
                    right: 10,
                    top: 10,
                    bottom: 10
                }
            }
        }
    };

    let ctx = document.getElementById(elementId).getContext('2d');
    return new Chart(ctx, config);
}
