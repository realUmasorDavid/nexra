// NEXRA product detail page – updated for Size + Color variants
document.addEventListener("DOMContentLoaded", () => {
  const product = window.NEXRA_PRODUCT || {};
  const variants = window.NEXRA_VARIANTS || [];

  // --- Size guide accordion ---
  const guideToggle = document.getElementById("guide-toggle");
  const guideContent = document.getElementById("size-guide-content");
  const guideIcon = document.getElementById("guide-icon");
  guideToggle?.addEventListener("click", () => {
    guideContent.classList.toggle("hidden");
    const isHidden = guideContent.classList.contains("hidden");
    guideToggle.setAttribute("aria-expanded", String(!isHidden));
    guideIcon.textContent = isHidden
      ? "expand_more"
      : "expand_less";
  });

  // --- Thumbnail gallery ---
  document.querySelectorAll("[data-full]").forEach((thumb) => {
    thumb.addEventListener("click", function () {
      const main = document.getElementById("mainImage");
      if (main) main.src = this.dataset.full;
      document
        .querySelectorAll(".thumbnail")
        .forEach((t) => t.classList.remove("active"));
      this.classList.add("active");
    });
  });

  // --- Quantity stepper ---
  const qtyInput = document.getElementById("quantity");
  document.getElementById("qty-decrement")?.addEventListener("click", () => {
    qtyInput.value = Math.max(1, parseInt(qtyInput.value || "1", 10) - 1);
  });
  document.getElementById("qty-increment")?.addEventListener("click", () => {
    qtyInput.value = Math.min(10, parseInt(qtyInput.value || "1", 10) + 1);
  });

  // --- Cart helpers ---
  function getCart() {
    try {
      return JSON.parse(localStorage.getItem("nexra_cart")) || [];
    } catch {
      return [];
    }
  }

  // Single source of truth for the badge lives in header.js. Fall back to
  // updating .cart-count directly only if header.js somehow didn't load,
  // so the page still works, but log it since that shouldn't happen.
  function refreshCartBadge() {
    if (window.nexra?.updateCartCount) {
      window.nexra.updateCartCount();
    } else {
      console.warn(
        "[cart] window.nexra.updateCartCount not found — is header.js loaded before this script?",
      );
      const count = getCart().reduce(
        (sum, item) => sum + (item.quantity || 0),
        0,
      );
      document
        .querySelectorAll(".cart-count")
        .forEach((el) => (el.textContent = count));
    }
    // Let any other listener (analytics, header, etc.) know the cart changed.
    window.dispatchEvent(new Event("cart:updated"));
  }

  function saveCart(cart) {
    // Update the UI first — this must not be blocked by a storage failure.
    refreshCartBadge_fromCart(cart);

    try {
      localStorage.setItem("nexra_cart", JSON.stringify(cart));
    } catch (err) {
      console.error("[cart] Could not persist cart to localStorage:", err);
      showToast("Cart couldn't be saved — check browser storage settings");
      return;
    }

    // Re-sync from storage (belt & suspenders — confirms what actually
    // got persisted rather than trusting the in-memory value).
    refreshCartBadge();
  }

  // Update the badge immediately from the in-memory cart array, before we
  // even know if localStorage.setItem will succeed.
  function refreshCartBadge_fromCart(cart) {
    const count = cart.reduce((sum, item) => sum + (item.quantity || 0), 0);
    document
      .querySelectorAll(".cart-count")
      .forEach((el) => (el.textContent = count));
  }

  function showToast(msg = "Added to cart!") {
    const toast = document.getElementById("cart-toast");
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 2500);
  }

  // --- Selection state ---
  let selectedColor = null;
  let selectedSize = null;
  let selectedVariant = null;

  const addToCartBtn = document.getElementById("add-to-cart-btn");
  const stockStatus = document.getElementById("stock-status");
  const priceDisplay = document.getElementById("productPriceDisplay");
  const colorLabel = document.getElementById("selected-color-label");
  const sizeLabel = document.getElementById("selected-size-label");

  // Color clicks
  document.querySelectorAll(".color-swatch").forEach((btn) => {
    btn.addEventListener("click", function () {
      document
        .querySelectorAll(".color-swatch")
        .forEach((b) => b.classList.remove("active"));
      this.classList.add("active");
      selectedColor = this.dataset.color;
      if (colorLabel) colorLabel.textContent = this.dataset.name;
      updateSelection();
    });
  });

  // Size clicks
  document.querySelectorAll(".size-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".size-btn").forEach((b) => {
        b.classList.remove("bg-stark-white", "text-pitch-black");
        b.classList.add("text-stark-white");
      });
      this.classList.add("bg-stark-white", "text-pitch-black");
      this.classList.remove("text-stark-white");
      selectedSize = this.dataset.size;
      if (sizeLabel) sizeLabel.textContent = this.textContent.trim();
      updateSelection();
    });
  });

  // Auto-select when there's only one color / size option, so a shopper
  // who never clicks a swatch still ends up with a valid selectedVariant.
  const colorButtons = document.querySelectorAll(".color-swatch");
  if (colorButtons.length === 1) colorButtons[0].click();

  const sizeButtons = document.querySelectorAll(".size-btn");
  if (sizeButtons.length === 1) sizeButtons[0].click();

  function updateSelection() {
    // Need both color and size (if they exist)
    const needsColor = document.querySelectorAll(".color-swatch").length > 0;
    const needsSize = document.querySelectorAll(".size-btn").length > 0;

    if ((needsColor && !selectedColor) || (needsSize && !selectedSize)) {
      selectedVariant = null;
      addToCartBtn.disabled = true;
      if (stockStatus) stockStatus.textContent = "Select color & size";
      return;
    }

    selectedVariant = variants.find(
      (v) =>
        (!needsColor || v.color === selectedColor) &&
        (!needsSize || v.size === selectedSize),
    );

    if (!selectedVariant) {
      addToCartBtn.disabled = true;
      if (stockStatus) stockStatus.textContent = "Unavailable";
      return;
    }

    // Update price display if variant has different price
    if (priceDisplay) {
      priceDisplay.textContent = `₦${Number(selectedVariant.price).toLocaleString()}`;
      priceDisplay.dataset.ngnPrice = selectedVariant.price;
    }

    if (selectedVariant.stock <= 0) {
      addToCartBtn.disabled = true;
      if (stockStatus) stockStatus.textContent = "Out of stock";
    } else {
      addToCartBtn.disabled = false;
      if (stockStatus) {
        stockStatus.textContent =
          selectedVariant.stock <= 5
            ? `Only ${selectedVariant.stock} left`
            : "In stock";
      }
    }
  }

  // Add to cart
  addToCartBtn?.addEventListener("click", () => {
    if (!selectedVariant) {
      showToast("Please select options first");
      return;
    }

    const quantity = parseInt(qtyInput.value, 10) || 1;

    if (quantity > selectedVariant.stock) {
      showToast(`Only ${selectedVariant.stock} left!`);
      return;
    }

    let cart = getCart();
    const idx = cart.findIndex((i) => i.variant_id === selectedVariant.id);

    if (idx !== -1) {
      const newQty = cart[idx].quantity + quantity;
      if (newQty > selectedVariant.stock) {
        showToast(`Only ${selectedVariant.stock} left!`);
        return;
      }
      cart[idx].quantity = newQty;
      showToast(`Cart updated (${newQty})`);
    } else {
      cart.push({
        variant_id: selectedVariant.id,
        product_id: product.id,
        name: product.name,
        size: selectedVariant.sizeName,
        color: selectedVariant.colorName,
        price: selectedVariant.price,
        quantity: quantity,
        image: product.image,
        slug: product.slug,
        sku: selectedVariant.sku,
      });
      showToast();
    }

    saveCart(cart);
  });

  // Initial badge sync on load (single source of truth — no more dead
  // nested DOMContentLoaded listeners, which never fired anyway since
  // DOMContentLoaded had already happened by the time they were registered).
  refreshCartBadge();
});
