/* Chess Federation — Client-side interactions */

(function () {
  const toggle = document.getElementById('navToggle');
  const links = document.getElementById('navLinks');

  if (toggle && links) {
    toggle.addEventListener('click', function () {
      toggle.classList.toggle('active');
      links.classList.toggle('open');
    });

    document.addEventListener('click', function (e) {
      if (!toggle.contains(e.target) && !links.contains(e.target)) {
        toggle.classList.remove('active');
        links.classList.remove('open');
      }
    });
  }

  // Hierarchy rank tiers — expand/collapse on mobile
  document.querySelectorAll('.rank-tier').forEach(function (tier) {
    tier.addEventListener('click', function () {
      if (window.innerWidth <= 768) {
        tier.classList.toggle('expanded');
      }
    });
  });

  // Auto-dismiss flash messages
  document.querySelectorAll('.flash').forEach(function (el) {
    setTimeout(function () {
      el.style.opacity = '0';
      el.style.transition = 'opacity .5s';
      setTimeout(function () { el.remove(); }, 500);
    }, 4000);
  });
})();
