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
                    display: false
                }],
                yAxes: [{
                    "id": "y-axis",
                    display: true,
                    ticks: {
                        beginAtZero: true,
                        precision: 0
                    }
                }]
            },
            plugins: {
                zoom: {
                    pan: {
                        enabled: true,
                        mode: 'x'
                    },
                    zoom: {
                        enabled: true,
                        drag: false,
                        mode: 'x',
                        sensitivity: 0,
                        speed: 1,
                        // Function called once zooming is completed
                        onZoomComplete: function({chart}) {
                            let resetButton = document.getElementById('file-churn-diagram-reset-zoom');
                            resetButton.style.display = 'block';
                        }
                    }
                }
            }
        }
    };

    const ctx = document.getElementById(elementId).getContext('2d');
    let churnChart = new Chart(ctx, options);

    // Setup up reset zoom button
    let resetButton = document.getElementById(elementId+'-reset-zoom');
    resetButton && resetButton.addEventListener('click', (element) => {
        churnChart.resetZoom();
    });

    // Show a text description of how many files where changed
    let countOnlyChanges = n => n === 0.1 ? 0 : n;
    let changes = values.reduce((a, b)=> countOnlyChanges(a) + countOnlyChanges(b), 0);

    let descriptionContext = {
        changes: changes,
        filesChanged: values.indexOf(0.1) - 1,
        filesTotal: labels.length
    };
    descriptionContext.filesChangedPercentage = Math.round(descriptionContext.filesChanged / descriptionContext.filesTotal * 100);
    let descriptionTemplate = `You made ${descriptionContext.changes} changes to ${descriptionContext.filesChanged} files (~${descriptionContext.filesChangedPercentage}%) of a total of ${descriptionContext.filesTotal} files in your codebase over the last 30 days.`;
    let description = document.getElementById(elementId+'-description');
    description.innerHTML = descriptionTemplate;

    return churnChart;
}
