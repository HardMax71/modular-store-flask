$(document).ready(function () {
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
});