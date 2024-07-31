$(document).ready(function () {
    // Toast functionality
    $('.toast').toast({autohide: false});
    $('.toast').toast('show');

    $('.toast .close').on('click', function (e) {
        e.preventDefault();
        var $toast = $(this).closest('.toast');
        $toast.removeClass('animate__fadeInRight').addClass('animate__fadeOutRight');
        setTimeout(function () {
            $toast.toast('hide');
            $toast.remove();
        }, 500);
    });

    $('.toast').on('show.bs.toast', function () {
        $(this).addClass('animate__animated animate__fadeInRight');
    });

    // Scroll to top functionality
    var scrollToTopBtn = $("#scroll-to-top");

    $(window).scroll(function() {
        if ($(window).scrollTop() > 300) {
            scrollToTopBtn.addClass('visible');
        } else {
            scrollToTopBtn.removeClass('visible');
        }
    });

    scrollToTopBtn.on('click', function(e) {
        e.preventDefault();
        $('html, body').animate({scrollTop:0}, '300');
    });
});
