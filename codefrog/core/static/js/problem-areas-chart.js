/**
 *
 * @param path
 * @param link
 */
let fileClickCallback = function (path, link) {
    let elem = document.getElementById('file-information');
    elem.innerHTML = '';

    let dateRange = getDateRange();
    let fileStatusUrl = '/api-internal/projects/' + window.project.id + '/file-status/' +
        '?path=' + path +
        '&date_from=' + dateRange['date_from'].format('YYYY-MM-DD') +
        '&date_to=' + dateRange['date_to'].format('YYYY-MM-DD');

    fetch(fileStatusUrl)
        .then(response => response.json())
        .then(updateFileStats);
};


/**
 *
 * @param data
 */
let updateFileStats = function (data) {
    data = data[0];
    const ctx = {
        path: data.path,
        link: data.link  // TODO: this is complete garbage....
    };

    let infoTemplate = `
        <div class="grid-x grid-padding-x grid-padding-y">
            <div class="large-12 cell dashboard-card" style="margin-top: 0;">
                <h5>Source file (on GitHub)</h5>
                <h5><a href="${ctx.link}" target="_blank" id="file-details">${ctx.path}</a></h5>
            </div>

            <div class="large-12 cell dashboard-card">
                <h5>Who owns the code in the file</h5>
                <div id="diagram-code-ownership" style="width:100%; height: 12em;"></div>
            </div>

            <div class="large-12 cell dashboard-card">
                <h5>Who made changes</h5>
                <div id="diagram-commit-count" style="width:100%; height: 12em;"></div>
            </div>

            <div class="large-12 cell dashboard-card">
                <h5>Number of file changes</h5>
                <div id="diagram-changes" style="width:100%; height: 4em;"></div>
            </div>

            <div class="large-12 cell dashboard-card">
                <h5>Complexity trend</h5>
                <div id="diagram-complexity" style="width:100%; height: 4em;"></div>
            </div>
        </div>
    `;

    let elem = document.getElementById('file-information');
    elem.innerHTML = infoTemplate;

    let el = document.querySelector('#file-details');
    el && el.addEventListener('click', (element) => {
        count('project.problem_areas.file_details.clicked');
    });

    // convert the date labels into real date objects for better display
    for (let i in data.complexity_trend_labels) {
        data.complexity_trend_labels[i] = moment(data.complexity_trend_labels[i]).toDate();
    }
    for (let i in data.changes_trend_labels) {
        data.changes_trend_labels[i] = moment(data.changes_trend_labels[i]).toDate();
    }

    const complexityDiagram = createSparkline(
        "diagram-complexity",
        data.complexity_trend_labels,
        data.complexity_trend,
    );
    const changesDiagram = createSparkline(
        "diagram-changes",
        data.changes_trend_labels,
        data.changes_trend,
    );
    const commitCountDiagram = createPieChart(
        "diagram-commit-count",
        data.commit_counts_labels,
        data.commit_counts,
    );
    const codeOwnershipDiagram = createPieChart(
        "diagram-code-ownership",
        data.code_ownership_labels,
        data.code_ownership,
    );
};


/**
 * Create a bubble diagram displaying the complexity and change frequency of
 * all the files in the source tree
 *
 * @param data
 */
let createProblemAreasDiagram = function (data) {
    if (data === [] || data === {} || !data) {
        return
    }

    let dataTree = data['tree'];
    let minChanges = data['min_changes'];
    let maxChanges = data['max_chnages'];

    let heatmapColour = d3.scaleLinear()
        .domain([0, 1])
        .range(["#fcebec", "#df2935"])
        .interpolate(d3.interpolateHcl);

    let c = d3.scaleLinear().domain([minChanges, maxChanges / 2]).range([0, 1]);

    let color = d3.scaleLinear()
        .domain([0, 10])
        .range(["#ffffff", "#a9a9a9"])
        .interpolate(d3.interpolateHcl);
    let format = d3.format(",d");
    let width = 932;
    let height = width;

    let pack = data_tree => d3.pack()
        .size([width, height])
        .padding(3)
    (d3.hierarchy(data_tree)
        .sum(d => d.size)
        .sort((a, b) => b.size - a.size));

    const root = pack(dataTree);
    let focus = root;
    let view;

    let htmlElement = document.getElementById('problem-areas-diagram');
    htmlElement.innerHTML = '';

    const svg = d3.select("#problem-areas-diagram").append("svg")
        .attr("viewBox", `-${width / 2} -${height / 2} ${width} ${height}`)
        .style("display", "block")
        .style("background", color(0))
        .style("cursor", "pointer");
    //.on("click", () => zoom(root));

    const node = svg.append("g")
        .selectAll("circle")
        .data(root.descendants().slice(1))
        .join("circle")
        .attr("fill", d => d.children ? color(d.depth) : heatmapColour(c(d.data.changes)))
        .attr("pointer-events", d => !d.children ? null : null)
        .on("mouseover", function (d) {
            d3.select(this).attr("stroke", "#000");
        })
        .on("mouseout", function () {
            d3.select(this).attr("stroke", null);
        })
        .on("click", function (d) {
            if (focus !== d) {
                if (d.children) {
                    zoom(d);
                    d3.event.stopPropagation();
                }

                if (d.data.path && d.data.repo_link) {
                    count('project.problem_areas.file.clicked');
                    fileClickCallback(d.data.path, d.data.repo_link);
                } else {
                    count('project.problem_areas.directory.clicked');
                }
            }
        });

    const label = svg.append("g")
        .style("font", "10px sans-serif")
        .attr("pointer-events", "none")
        .attr("text-anchor", "middle")
        .selectAll("text")
        .data(root.descendants())
        .join("text")
        .style("fill-opacity", d => d.parent === root ? 1 : 0)
        .style("display", d => d.parent === root ? "inline" : "none")
        .text(d => d.data.name);

    zoomTo([root.x, root.y, root.r * 2]);

    function zoomTo(v) {
        const k = width / v[2];

        view = v;

        label.attr("transform", d => `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`);
        node.attr("transform", d => `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`);
        node.attr("r", d => d.r * k);
    }

    function zoom(d) {
        const focus0 = focus;
        focus = d;

        const transition = svg.transition()
            .duration(d3.event.altKey ? 7500 : 750)
            .tween("zoom", d => {
                const i = d3.interpolateZoom(view, [focus.x, focus.y, focus.r * 2]);
                return t => zoomTo(i(t));
            });

        label
            .filter(function (d) {
                return d.parent === focus || this.style.display === "inline";
            })
            .transition(transition)
            .style("fill-opacity", d => d.parent === focus ? 1 : 0)
            .on("start", function (d) {
                if (d.parent === focus) this.style.display = "inline";
            })
            .on("end", function (d) {
                if (d.parent !== focus) this.style.display = "none";
            });
    }
}

