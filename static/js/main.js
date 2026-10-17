document.addEventListener("DOMContentLoaded", () => {
  const header = document.querySelector("[data-site-header]");

  // --- Cart count badge (single source of truth) ---
  // Every script on the site should call window.nexra.updateCartCount()
  // instead of writing to .cart-count directly. That keeps there from
  // being two competing pieces of logic that can disagree.
  const getCart = () => {
    const raw = localStorage.getItem("nexra_cart");
    try {
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  };

  const updateCartCount = () => {
    const count = getCart().reduce(
      (sum, item) => sum + (item.quantity || 0),
      0,
    );
    document
      .querySelectorAll(".cart-count")
      .forEach((el) => (el.textContent = count));
    return count;
  };

  updateCartCount();
  window.nexra = window.nexra || {};
  window.nexra.updateCartCount = updateCartCount;

  // Bfcache fix: when a page is restored from the back/forward cache
  // (common on browser back/forward, and sometimes regular nav too),
  // DOMContentLoaded does NOT fire again — the page is unfrozen from a
  // snapshot instead of actually reloading. Without this, the badge stays
  // stuck at whatever it said the last time this page's DOM was rendered,
  // even though localStorage has since changed on another page.
  window.addEventListener("pageshow", () => {
    updateCartCount();
  });

  // Any script can dispatch this instead of touching the DOM itself,
  // e.g. window.dispatchEvent(new Event("cart:updated"))
  window.addEventListener("cart:updated", updateCartCount);

  // --- Diagnostic safety net -------------------------------------------
  // Something outside header.js / product-detail.js is resetting the
  // badge to a stale value after we set it. Until that's tracked down,
  // watch the badge node(s) and (a) log who/when it changes so it shows
  // up in the console with a stack trace, and (b) correct it back to the
  // real localStorage-derived count so the UI stays right in the meantime.
  const observer = new MutationObserver((mutations) => {
    const expected = String(
      getCart().reduce((sum, item) => sum + (item.quantity || 0), 0),
    );
    mutations.forEach((m) => {
      const el = m.target.nodeType === 3 ? m.target.parentElement : m.target;
      if (!el || !el.classList || !el.classList.contains("cart-count")) return;
      if (el.textContent !== expected) {
        console.warn(
          `[cart-count] badge was overwritten to "${el.textContent}" ` +
            `(expected "${expected}"). Something else on the page is ` +
            `setting .cart-count directly — check base.html / other ` +
            `scripts for a second cart_count render.`,
        );
        el.textContent = expected;
      }
    });
  });
  document.querySelectorAll(".cart-count").forEach((el) => {
    observer.observe(el, {
      characterData: true,
      childList: true,
      subtree: true,
    });
  });
  // ------------------------------------------------------------------------

  if (!header) return;

  const drawer = document.querySelector("[data-mobile-menu]");
  const backdrop = document.querySelector("[data-mobile-menu-backdrop]");
  const toggles = document.querySelectorAll("[data-mobile-menu-toggle]");
  const iconOpen = document.querySelector("[data-menu-icon-open]");
  const iconClose = document.querySelector("[data-menu-icon-close]");
  const mainToggleBtn = document.querySelector(
    '[data-mobile-menu-toggle][aria-controls="mobile-nav-drawer"]',
  );

  if (!drawer || !backdrop) return;

  // 1. Smooth Header Shrink/Blur Scroll Effect
  const handleScroll = () => {
    if (window.scrollY > 30) {
      header.classList.add("bg-stark-white/90", "backdrop-blur-md", "py-1");
    } else {
      header.classList.remove("bg-stark-white/90", "backdrop-blur-md", "py-1");
    }
  };
  window.addEventListener("scroll", handleScroll, { passive: true });
  handleScroll(); // Initial pass check

  // 2. Clear State Navigation Actions
  const openDrawer = () => {
    drawer.classList.remove("translate-x-full");
    backdrop.classList.remove("opacity-0", "pointer-events-none");
    document.body.classList.add("overflow-hidden");

    if (iconOpen && iconClose) {
      iconOpen.classList.add("opacity-0", "scale-75");
      iconClose.classList.remove("opacity-0", "scale-75");
    }
    if (mainToggleBtn) mainToggleBtn.setAttribute("aria-expanded", "true");
  };

  const closeDrawer = () => {
    drawer.classList.add("translate-x-full");
    backdrop.classList.add("opacity-0", "pointer-events-none");
    document.body.classList.remove("overflow-hidden");

    if (iconOpen && iconClose) {
      iconOpen.classList.remove("opacity-0", "scale-75");
      iconClose.classList.add("opacity-0", "scale-75");
    }
    if (mainToggleBtn) mainToggleBtn.setAttribute("aria-expanded", "false");
  };

  const isDrawerOpen = () => !drawer.classList.contains("translate-x-full");

  // 3. Event Triggers
  toggles.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      isDrawerOpen() ? closeDrawer() : openDrawer();
    });
  });

  backdrop.addEventListener("click", closeDrawer);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && isDrawerOpen()) closeDrawer();
  });

  document.querySelectorAll("[data-mobile-link]").forEach((link) => {
    link.addEventListener("click", closeDrawer);
  });

  // Structural viewport safety check
  window.matchMedia("(min-width: 768px)").addEventListener("change", (e) => {
    if (e.matches && isDrawerOpen()) closeDrawer();
  });
});
