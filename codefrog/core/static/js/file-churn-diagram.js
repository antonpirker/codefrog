/**
 * Create a bar chart showing what files are changed the most.
 */
function createFileChurnDiagram(elementId, labels, values) {
    const data = {
        labels: labels,
        datasets: [{
            data: values,
            label: 'Changes',
            borderColor: chart_colors[2],
            backgroundColor: chart_colors[2],
            xAxisID: 'x-axis',
            yAxisID: 'y-axis'
        }]
    };

    const options = {
        type: 'bar',
        data: data,
        options: {
            fill: false,
            responsive: true,
            maintainAspectRatio: false,
            legend: {
                display: false
            },
            scales: {
                xAxes: [{
                    "id": "x-axis",
                    display: false,
                }],
                yAxes: [{
                    "id": "y-axis",
                    display: true,
                    ticks: {
                        beginAtZero: true,
                        precision: 0
                    }
                }]
            }
        }
    };

    const ctx = document.getElementById(elementId).getContext('2d');
    return new Chart(ctx, options);
}
