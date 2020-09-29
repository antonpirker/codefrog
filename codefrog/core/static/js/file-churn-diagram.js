/**
 * Create a bar chart showing what files are changed the most.
 */
function createFileChurnDiagram(fileChanges) {
    // Data to display on the chart
    let xData = [];
    let numberOfChanges = [];

    for(let i in fileChanges) {
        xData.push(fileChanges[i]['file_path']);
        numberOfChanges.push(fileChanges[i]['changes']);
    }

    let fileChangesTrace = {
	    x: xData,
	    y: numberOfChanges,
        name: 'Number of changes to file',
        type: 'bar',
        marker: {
	        color: chartColors[COLOR_FILE_CHANGES]
        },
    }
    let data = [fileChangesTrace];


    // Layout of the chart
    let layout = {
        showlegend: true,
        legend: {
            orientation: "h"
        },
        xaxis: {
            showticklabels: false,
            showline: true,
            showgrid: false,
            ticks: 'outside',
            tickwidth: 2,
            ticklen: 5,
        },
        yaxis: {
            showgrid: false,
            zeroline: false,
            showline: false,
            showticklabels: false
        },
        margin: {
            l: 0,
            r: 0,
            t: 0,
            b: 0
        },
    }

    // General chart configuration
    let config = {
        displayModeBar: false,
        responsive: true
    }
    let htmlElement = document.getElementById('file-churn-diagram');
    htmlElement.innerHTML = '';
    Plotly.newPlot(htmlElement, data, layout, config);

    htmlElement.on('plotly_click', function(data){
        let path = data.points[0].x;
        bubbleClickCallback(path, 'file-churn-file-information', true);
    });

    // Show a text description of how many files where changed
    let totalChanges = fileChanges.reduce((a, b) => {
        return {
            'changes': a['changes'] + b['changes']
        }
    })['changes'];

    let filesChanged = fileChanges.reduce((a, b) => {
        let count = 0;
        if (b['changes'] > 0) {
            count = 1;
        }
        return a + count;
    }, 0);

    let descriptionContext = {
        changes: totalChanges,
        filesChanged: filesChanged,
        filesTotal: fileChanges.length
    };
    descriptionContext.filesChangedPercentage = Math.round(descriptionContext.filesChanged / descriptionContext.filesTotal * 100);

    descriptionContext.changes = Number(descriptionContext.changes).toLocaleString();
    descriptionContext.filesChanged = Number(descriptionContext.filesChanged).toLocaleString();
    descriptionContext.filesTotal = Number(descriptionContext.filesTotal).toLocaleString();
    descriptionContext.filesChangedPercentage = Number(descriptionContext.filesChangedPercentage).toLocaleString();

    let descriptionTemplate = `You made changes to ${descriptionContext.filesChanged} files (of a total of ${descriptionContext.filesTotal} files) in your codebase. All your work was done in ~${descriptionContext.filesChangedPercentage}% of your code base.`;
    let description = document.getElementById('file-churn-diagram-description');
    description.innerHTML = descriptionTemplate;
}
