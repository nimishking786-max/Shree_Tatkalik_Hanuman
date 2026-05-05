document.addEventListener('DOMContentLoaded', function() {
    const preloader = document.getElementById('preloader');
    if (!preloader) return;

    const hide = () => {
        preloader.classList.add('hidden');
        setTimeout(() => {
            preloader.style.display = 'none';
        }, 900);
    };

    // Hide when page is fully loaded, with minimum display time of 1.5s
    const startTime = Date.now();
    const MIN_TIME = 1500;

    window.addEventListener('load', function() {
        const elapsed = Date.now() - startTime;
        const delay = Math.max(0, MIN_TIME - elapsed);
        setTimeout(hide, delay);
    });

    // Fallback: force hide after 6s no matter what
    setTimeout(hide, 6000);
});