function check_for_updates() {
    show_update_section("checking");
    D.rpc("check_for_updates", {},
        function(args) {
            if (args.update_required) {
                show_update_section("need-update");
            } else {
                show_update_section("up-to-date");
            }
        },
        function(error) {
            if (error.message=="already checking") {
                //show_update_section("checking");
            }
        }
    );
}

function get_update_status() {
    D.rpc("get_update_status", {},
        function (args) {
            console.log("updating? " + args.status);
            if (args.status == "checking") {
                show_update_section("checking");
            } else if ((args.status == "downloading") || (args.status == "filechecking")) {
                show_update_section("need-update");
            } else {
                check_for_updates();
            }
        }
    );
}

function perform_update() {
    D.rpc("show_filetransfer_window");
    show_update_section("none");
}

var update_sections = ["checking", "up-to-date", "need-update"];

function show_update_section(which) {
    for (var i in update_sections) {
        var name = update_sections[i];
        var node = $("#update #" + name);
        if (name == which) {
            node.show();
        } else {
            node.hide();
        }
    }
}

show_update_section("none");
