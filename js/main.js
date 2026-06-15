/* ============================================================
   ide Chraft — JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  // ── Navigation ─────────────────────────────────────────
  const nav = document.querySelector('.nav');
  const burger = document.querySelector('.nav__burger');
  const mobileNav = document.querySelector('.nav__mobile');
  const mobileClose = document.querySelector('.nav__mobile-close');
  const navIsFixed = nav && nav.classList.contains('scrolled');

  if (nav && !navIsFixed) {
    window.addEventListener('scroll', () => {
      nav.classList.toggle('scrolled', window.scrollY > 60);
    });
  }

  function openMobileNav() {
    mobileNav?.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeMobileNav() {
    mobileNav?.classList.remove('open');
    document.body.style.overflow = '';
  }

  // Sonne togglet das Menü (öffnen UND schliessen)
  burger?.addEventListener('click', () => {
    if (mobileNav?.classList.contains('open')) {
      closeMobileNav();
    } else {
      openMobileNav();
    }
  });

  mobileClose?.addEventListener('click', closeMobileNav);
  mobileNav?.querySelectorAll('a').forEach(a => a.addEventListener('click', closeMobileNav));

  // ESC-Taste schliesst das Menü
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeMobileNav();
  });

  // Klick auf den leeren Bereich des Menüs schliesst es
  mobileNav?.addEventListener('click', (e) => {
    if (e.target === mobileNav) closeMobileNav();
  });

  // ── Slot-Machine Headline ────────────────────────────────
  const reel = document.querySelector('.js-slot-reel');
  if (reel) {
    const baseWords = Array.from(reel.children).map(el => el.textContent);
    const n = baseWords.length;
    const LINE = 1.3; // muss mit CSS line-height der Reel-Spans übereinstimmen (em)

    // Wörter verdreifachen, damit die Walze durch einen ganzen
    // Zyklus "drehen" kann, bevor sie auf dem nächsten Wort landet
    reel.innerHTML = '';
    for (let i = 0; i < 3; i++) {
      baseWords.forEach(w => {
        const span = document.createElement('span');
        span.textContent = w;
        reel.appendChild(span);
      });
    }

    let pos = 0;

    const spin = () => {
      // Eine volle Runde + 1 vorwärts → landet auf dem nächsten Wort
      pos += n + 1;
      reel.classList.add('spinning');
      reel.style.transform = `translateY(-${pos * LINE}em)`;

      setTimeout(() => reel.classList.remove('spinning'), 650);

      // Unsichtbar zurücksetzen, sobald wir tief in der Duplikat-Liste sind
      if (pos >= n * 2) {
        setTimeout(() => {
          reel.style.transition = 'none';
          pos = pos % n;
          reel.style.transform = `translateY(-${pos * LINE}em)`;
          void reel.offsetHeight; // Reflow erzwingen
          reel.style.transition = '';
        }, 950);
      }
    };

    setInterval(spin, 3200);
  }

  // ── Scroll-Animationen ───────────────────────────────────
  const fadeEls = document.querySelectorAll('.fade-up');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  fadeEls.forEach(el => observer.observe(el));

  // ── Kontaktformular ──────────────────────────────────────
  const form = document.querySelector('.js-contact-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      const success = form.querySelector('.form__success');

      btn.disabled = true;
      btn.textContent = 'Wird gesendet…';

      // Versand-Simulation – hier später echten Endpoint anbinden (z.B. Formspree)
      setTimeout(() => {
        form.querySelectorAll('.form-row, .form-group, .form__privacy, [type="submit"]')
          .forEach(el => el.style.display = 'none');
        if (success) success.style.display = 'block';
      }, 1200);
    });
  }

});
