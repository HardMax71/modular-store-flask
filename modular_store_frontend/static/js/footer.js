// Set the current year in the footer
document.getElementById('currentYear').textContent = new Date().getFullYear();

window.onscroll = function () {
    showScrollToTopButton();
};

function showScrollToTopButton() {
    var scrollToTopBtn = document.getElementById("scrollToTopBtn");
    if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
        scrollToTopBtn.style.display = "block";
    } else {
        scrollToTopBtn.style.display = "none";
    }
}

function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}
