document.addEventListener('DOMContentLoaded', function() {
  // ── Bootstrap Tooltips ──
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  tooltipTriggerList.forEach(function(el) { return new bootstrap.Tooltip(el); });

  // ── Navbar Scroll Effect ──
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    const onScroll = () => {
      navbar.classList.toggle('scrolled', window.scrollY > 40);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ── Scroll-to-Top Button ──
  const scrollBtn = document.getElementById('scrollTopBtn');
  if (scrollBtn) {
    window.addEventListener('scroll', () => {
      scrollBtn.classList.toggle('visible', window.scrollY > 300);
    }, { passive: true });
    scrollBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ── Newsletter Subscription ──
  const newsletterForm = document.getElementById('newsletterForm');
  if (newsletterForm) {
    newsletterForm.addEventListener('submit', function(e) {
      e.preventDefault();
      const emailInput = this.querySelector('input[type="email"]');
      if (emailInput && emailInput.value && emailInput.value.includes('@')) {
        showToast('🙏 Thank you for subscribing! Jai Hanuman!', 'success');
        emailInput.value = '';
      } else {
        showToast('Please enter a valid email address.', 'warning');
      }
    });
  }

  // ── Intersection Observer — Animate on scroll ──
  const animatedEls = document.querySelectorAll('.animate-on-scroll');
  if (animatedEls.length > 0) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-fadeInUp');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    animatedEls.forEach(el => observer.observe(el));
  }

  // ── Counter Animation ──
  const counters = document.querySelectorAll('[data-counter]');
  if (counters.length > 0) {
    const counterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const target = parseInt(el.dataset.counter, 10);
          let current = 0;
          const step = Math.ceil(target / 60);
          const timer = setInterval(() => {
            current = Math.min(current + step, target);
            el.textContent = current.toLocaleString() + (el.dataset.suffix || '');
            if (current >= target) clearInterval(timer);
          }, 25);
          counterObserver.unobserve(el);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(el => counterObserver.observe(el));
  }
});

// ── Toast Notification Helper ──
function showToast(message, type = 'success') {
  const icons = {
    success: 'fa-check-circle',
    warning: 'fa-exclamation-triangle',
    danger:  'fa-times-circle',
    info:    'fa-info-circle'
  };
  const toast = document.createElement('div');
  toast.innerHTML = `
    <div class="alert alert-${type} d-flex align-items-center gap-2 shadow" role="alert"
         style="position:fixed;top:80px;right:20px;z-index:9999;min-width:280px;max-width:380px;
                animation:slideDown 0.4s ease;border-radius:14px;">
      <i class="fas ${icons[type] || 'fa-info-circle'}"></i>
      <span>${message}</span>
      <button type="button" class="btn-close ms-auto" aria-label="Close"></button>
    </div>`;
  document.body.appendChild(toast);
  const closeBtn = toast.querySelector('.btn-close');
  if (closeBtn) closeBtn.addEventListener('click', () => toast.remove());
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.5s'; setTimeout(() => toast.remove(), 500); }, 4000);
}