function renderContents() {
    drawChart("posts-canvas").Line(postsChart, {});
    drawChart("comments-canvas").Line(commentsChart, {});
    drawChart("poster-canvas").Doughnut(posters, {});
    drawChart("commenter-canvas").Doughnut(commenters, {});
}

function drawChart(id) {
    var canvas = $("#" + id);
    canvas.attr("width", canvas.parent().width()); // Resize canvas
    var ctx = canvas.get(0).getContext("2d");
    return new Chart(ctx);
}

$(document).ready(renderContents);
