document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Newsletter subscription simulation
    const newsletterBtn = document.querySelector('.input-group .btn-primary');
    if (newsletterBtn) {
        newsletterBtn.addEventListener('click', function() {
            const emailInput = this.previousElementSibling;
            if (emailInput.value && emailInput.value.includes('@')) {
                alert('Thank you for subscribing!');
                emailInput.value = '';
            } else {
                alert('Please enter a valid email.');
            }
        });
    }
});