function renderContents() {
    drawChart("posts-canvas", posts);
    drawChart("comments-canvas", comments);
}

function drawChart(id, data) {
    var canvas = $("#" + id);
    canvas.attr("width", canvas.parent().width()); // Resize canvas
    var ctx = canvas.get(0).getContext("2d");
    new Chart(ctx).Line(data, {});
}

$(document).ready(renderContents);
