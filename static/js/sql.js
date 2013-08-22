var examples = {"Posts by most recent":
                "SELECT * FROM post ORDER BY updated_time DESC",
                "Top commenters":
                "SELECT from_name, count(id) FROM comment GROUP BY from_name "+
                "ORDER BY count(id) DESC",
                "Total posts":
                "SELECT count(*) from post",
                "Get comments of a particular post":
                'SELECT * FROM comment WHERE post_id="251125004903932_251125094903923"'+
                ' ORDER BY created_time',
                "Most commented posts":
                "SELECT count(*) AS Count, post.id, post.from_name, post.message "+
                "FROM comment JOIN post ON post.id=post_id GROUP BY post_id "+
                "ORDER BY COUNT DESC",
                "Full-text search":
                'SELECT * FROM post_fts WHERE post_fts MATCH "random"',
                "Total comments by month":
                'SELECT count(*), STRFTIME("%Y-%m", SUBSTR(created_time, 1, 19)) '+
                'AS Month FROM comment GROUP BY Month ORDER BY Month DESC'};


$(document).ready(function () {
    $("#query").click(search("/query", true));
    for (var e in examples) {
        (function (e) {
            var link = $("<li><a>" + e + "</a></li>");
            link.click(function () {
                $("#search-field").val(examples[e]);
                $("#query").click();
            });
            $("#example-dropdown").append(link);
        })(e);
    }
});
