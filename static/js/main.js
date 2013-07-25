var paging = {offset: 0};
var LENGTH = 25;

function attach_handlers() {
    $("#search-posts").click(search("posts", true));
    $("#search-comments").click(search("comments", true));
}

function search(type, resetPaging, default_query, deltaPaging) {
    return function () {
        paging.offset += deltaPaging;
        var query = default_query || $("#search-field").val();
        $(".clickable").attr("disabled", "disabled");

        if (resetPaging) {
            paging = {offset: 0};
        }
        
        function onSubmitted() {
            $(".clickable").removeAttr("disabled");
        }
        
        send("get", "/search/" + type,
             {query:query, limit:LENGTH, offset:paging.offset},
             {}, function (err, res) {
            onSubmitted();
            if (! err) {
                $("#search-result").empty().append(res);
                if ($(".result").length < LENGTH) {
                    $(".btn-next").attr("disabled", "disabled");
                } else {
                    $(".btn-next").click(search(type, false, query, LENGTH));
                }
                if (paging.offset == 0) {
                    $(".btn-previous").attr("disabled", "disabled");
                } else {
                    $(".btn-previous").click(search(type, false, query, -LENGTH));
                }
            }
        });
    };
}

function send(method, url, params, data, callback) {
    var getParams = $.map(params, function(val, key) {
        return encodeURIComponent(key)+'='+encodeURIComponent(val);
    });

    if (getParams.length) {
	url += '?' + getParams.join('&');
    }

    var config = {type: method,
                  success: function(data) {
                      callback(null, data);
                  },
                  error: function(error) {
                      callback(error, null);
                  }};

    if (method == 'post') {
        config.data = JSON.stringify(data);
        config.contentType = "application/json; charset=UTF-8";
    }
    $.ajax(url, config);
}

$(document).ready(attach_handlers);
