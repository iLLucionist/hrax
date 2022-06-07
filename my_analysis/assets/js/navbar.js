slide_count = 0
current_slide = 0

function docReady(fn) {
    if (document.readyState === "complete" || document.readyState === "interactive") {
        setTimeout(fn, 1);
    } else {
        document.addEventListener("DOMContentLoaded", fn)
    }
}

function slide_id(no) { return "slide-" + no; }

function slide_el(no) { return document.getElementById(slide_id(no)) }

function hide_slide(no) { if (current_slide > 0) slide_el(current_slide).className = "slide" }

function show_slide(no) { if (current_slide > 0) slide_el(current_slide).className = "visible slide" }

function update_slide_counter() { document.getElementById("slide-counter").innerHTML = current_slide + " / " + slide_count }

function next_slide() {
    if (current_slide < slide_count)
        set_current_slide(current_slide + 1)
}

function previous_slide() {
    if (current_slide > 1)
        set_current_slide(current_slide - 1)
}

function set_current_slide(no) {
    hide_slide(current_slide)
    current_slide = no
    show_slide(current_slide)
    update_slide_counter()
}


docReady(function() {
    slide_count = document.getElementById("slides").childElementCount;
    console.log(slide_count)
    set_current_slide(1)

    document.getElementById("previous-slide").addEventListener("click", function(e) { previous_slide() })
    document.getElementById("next-slide").addEventListener("click", function(e) { next_slide() })
})
