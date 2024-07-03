$(function () {
    $('.nav-tabs a').on('shown.bs.tab', function (event) {
        var activeTab = $(event.target).data('tab');
        localStorage.setItem('activeTab', activeTab);
    });
});

$(function () {
    var activeTab = localStorage.getItem('activeTab');
    if (activeTab) {
        $('.nav-tabs a[data-tab="' + activeTab + '"]').tab('show');
    }
});