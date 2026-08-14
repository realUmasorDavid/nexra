document.addEventListener("DOMContentLoaded", () => {
  const header = document.querySelector("[data-site-header]");

  // --- Cart count badge ---
  // Reads a simple localStorage cart so the header badge stays accurate
  // across pages without a server round-trip. Swap this for a session/DB-backed
  // count once the cart is server-rendered.
  const getCart = () => {
    const raw = localStorage.getItem("hoodranked_cart");
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
  };
  updateCartCount();
  window.hoodranked = window.hoodranked || {};
  window.hoodranked.updateCartCount = updateCartCount;

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
