/**
 * Create diagram for evolution of issues
 */
function createEvolutionOfIssuesDiagram(metrics, releases) {
    // Data to display on the chart
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
        line: {
	        color: COLOR_COMPLEXITY,
	        width: 2
        },
        fill: 'tozeroy',
        fillcolor: COLOR_COMPLEXITY_FILL,
        hoverinfo: 'skip'
    }

    let issues_closed = {
	    x: xData,
	    y: issuesClosedData,
        name: 'Issue Closed',
        type: 'bar',
        yaxis: 'y2',
        marker: {
	        color: chartColors[COLOR_METRIC1]
        },
    }

    let issue_age = {
	    x: xData,
	    y: issueAgeData,
        name: 'Issue Age',
        mode: 'lines+markers',
        yaxis: 'y3',
        marker: {
	        color: chartColors[COLOR_METRIC1_ALT],
	        size: 10
        },
        line: {
	        color: chartColors[COLOR_METRIC1_ALT]
        },
        hovertemplate: '%{y:.1f} days',
    }

    let data = [complexity, issues_closed, issue_age]

    // Paint releases to the chart
    let shapes = [];
    let annotations = [];

    for(let i in releases) {
        let releaseDate = releases[i]['date'].split('T')[0]
        shapes.push({
            type: 'line',
            x0: releaseDate,
            y0: 0,
            x1: releaseDate,
            yref: 'paper',
            y1: 1,
            line: {
                color: '#999',
                width: 1.5,
                dash: 'dot'
            }
        })
        annotations.push({
            text: releases[i]['name'],
            showarrow: false,
            x: releaseDate,
            yref: 'paper',
            y: 1,
            bgcolor: '#fff',
        })
    }

    // Layout of the chart
    let layout = {
        showlegend: true,
        legend: {
            orientation: "h"
        },
        shapes: shapes,
        annotations: annotations,
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

    // General chart configuration
    let config = {
        displayModeBar: false,
        responsive: true
    }

    let htmlElement = document.getElementById('evolution-issues-diagram');
    htmlElement.innerHTML = '';
    Plotly.newPlot(htmlElement, data, layout, config);
}


/**
 * Create diagram for evolution of pull requests
 */
function createEvolutionOfPullRequestsDiagram(metrics, releases) {
    // Data to display on the chart
    let xData = [];
    let complexityData = [];
    let pullRequestsClosedData = [];
    let pullRequestAgeData = [];

    for(let i in metrics) {
        xData.push(metrics[i]['date'])
        complexityData.push(metrics[i]['complexity'])
        pullRequestsClosedData.push(metrics[i]['github_pull_requests_merged'])
        pullRequestAgeData.push(metrics[i]['github_avg_pull_request_age'])
    }

    let complexity = {
	    x: xData,
	    y: complexityData,
        name: 'Complexity',
        type: 'scatter',
        mode: 'lines',
        line: {
	        color: COLOR_COMPLEXITY,
	        width: 2
        },
        fill: 'tozeroy',
        fillcolor: COLOR_COMPLEXITY_FILL,
        hoverinfo: 'skip'
    }

    let prs_closed = {
	    x: xData,
	    y: pullRequestsClosedData,
        name: 'Pull Requests Closed',
        type: 'bar',
        yaxis: 'y2',
        marker: {
	        color: chartColors[COLOR_METRIC2]
        },
    }

    let pr_age = {
	    x: xData,
	    y: pullRequestAgeData,
        name: 'Pull Request Age',
        mode: 'lines+markers',
        yaxis: 'y3',
        marker: {
	        color: chartColors[COLOR_METRIC2_ALT],
	        size: 10
        },
        line: {
	        color: chartColors[COLOR_METRIC2_ALT]
        },
        hovertemplate: '%{y:.1f} days',
    }

    let data = [complexity, prs_closed, pr_age];

    // Paint releases to the chart
    let shapes = [];
    let annotations = [];

    for(let i in releases) {
        let releaseDate = releases[i]['date'].split('T')[0]
        shapes.push({
            type: 'line',
            x0: releaseDate,
            y0: 0,
            x1: releaseDate,
            yref: 'paper',
            y1: 1,
            line: {
                color: '#999',
                width: 1.5,
                dash: 'dot'
            }
        })
        annotations.push({
            text: releases[i]['name'],
            showarrow: false,
            x: releaseDate,
            yref: 'paper',
            y: 1,
            bgcolor: '#fff',
        })
    }

    // Layout of the chart
    let layout = {
        showlegend: true,
        legend: {
            orientation: "h"
        },
        shapes: shapes,
        annotations: annotations,
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

    // General chart configuration
    let config = {
        displayModeBar: false,
        responsive: true
    }

    let htmlElement = document.getElementById('evolution-pull-requests-diagram');
    htmlElement.innerHTML = '';
    Plotly.newPlot(htmlElement, data, layout, config);
}
