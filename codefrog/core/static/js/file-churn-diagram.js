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
	        color: chart_colors[1]
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
            showticklabels: false
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
    let descriptionTemplate = `You made ${descriptionContext.changes} changes to ${descriptionContext.filesChanged} files (~${descriptionContext.filesChangedPercentage}%) of a total of ${descriptionContext.filesTotal} files in your codebase.`;
    let description = document.getElementById('file-churn-diagram-description');
    description.innerHTML = descriptionTemplate;

    // Update list of Top 5 most changed files
    let list = document.getElementById('file-churn-top5-list');
    list.innerHTML = '';
    let top5 = fileChanges.slice(0, 5);
    for(let i in top5) {
        let ctx = top5[i];
        let listItemTemplate = `<li><a href="${ctx.repo_link}" target="_blank">${ctx.file_path}</a> - ${ctx.changes} changes</li>`;
        list.innerHTML = list.innerHTML + listItemTemplate;
    }
}
