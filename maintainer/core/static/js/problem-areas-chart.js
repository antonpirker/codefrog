/**
 * Create a bubble diagram displaying the complexity and change frequency of
 * all the files in the source tree
 */
function createProblemAreasDiagram(elementId, dataTree, minChanges, maxChanges, fileClickCallback) {
    let heatmapColour = d3.scaleLinear()
        .domain([0, 1])
        .range(["#fcebec", "#df2935"])
        .interpolate(d3.interpolateHcl);

    let c = d3.scaleLinear().domain([minChanges, maxChanges/2]).range([0,1]);

    color = d3.scaleLinear()
        .domain([0, 10])
        .range(["#ffffff", "#a9a9a9"])
        .interpolate(d3.interpolateHcl);
    format = d3.format(",d");
    width = 932;
    height = width;

    pack = data_tree => d3.pack()
        .size([width, height])
        .padding(3)
    (d3.hierarchy(data_tree)
        .sum(d => d.size)
        .sort((a, b) => b.size - a.size));

    const root = pack(dataTree);
    let focus = root;
    let view;

    const svg = d3.select("#"+elementId).append("svg")
        .attr("viewBox", `-${width / 2} -${height / 2} ${width} ${height}`)
        .style("display", "block")
        .style("background", color(0))
        .style("cursor", "pointer")
        .on("click", () => zoom(root));

    const node = svg.append("g")
        .selectAll("circle")
        .data(root.descendants().slice(1))
        .join("circle")
            .attr("fill", d => d.children ? color(d.depth) : heatmapColour(c(d.data.changes)))
            .attr("pointer-events", d => !d.children ? null : null)
            .on("mouseover", function(d) {
              d3.select(this).attr("stroke", "#000");
            })
            .on("mouseout", function() {
              d3.select(this).attr("stroke", null);
            })
            .on("click", function(d) {
              if(focus !== d) {
                  if(d.children) {
                      zoom(d);
                      d3.event.stopPropagation();
                  }
                  fileClickCallback(d.data.path, d.data.repo_link);
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
            .filter(function(d) { return d.parent === focus || this.style.display === "inline"; })
            .transition(transition)
            .style("fill-opacity", d => d.parent === focus ? 1 : 0)
            .on("start", function(d) { if (d.parent === focus) this.style.display = "inline"; })
            .on("end", function(d) { if (d.parent !== focus) this.style.display = "none"; });
    }
}

