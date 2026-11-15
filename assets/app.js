(() => {
  // The address is shipped base64-encoded so scrapers don't find it in the HTML.
  const contact = document.querySelector("[data-e]");
  if (contact) {
    contact.href = "mailto:" + atob(contact.dataset.e);
    contact.hidden = false;
  }

  if (!document.querySelector(".grid")) return; // e.g. the About page: nothing to filter

  const works = [...document.querySelectorAll(".work")];
  const chips = [...document.querySelectorAll("[data-filter-location] button")];
  const sizeSel = document.getElementById("size-filter");
  const count = document.getElementById("count");
  const empty = document.getElementById("empty");
  const state = { location: "all", size: "all" };

  const params = new URLSearchParams(location.search);
  if (chips.some((c) => c.dataset.value === params.get("location"))) state.location = params.get("location");
  if ([...sizeSel.options].some((o) => o.value === params.get("size"))) state.size = params.get("size");
  sizeSel.value = state.size;

  function matches(w) {
    if (state.location !== "all" && w.dataset.location !== state.location) return false;
    const opt = sizeSel.selectedOptions[0];
    const size = parseFloat(w.dataset.size);
    if (opt.dataset.min !== undefined && !(size > parseFloat(opt.dataset.min))) return false;
    if (opt.dataset.max !== undefined && !(size <= parseFloat(opt.dataset.max))) return false;
    return true;
  }

  function apply() {
    let shown = 0;
    for (const w of works) {
      w.hidden = !matches(w);
      if (!w.hidden) shown++;
    }
    for (const c of chips) c.setAttribute("aria-pressed", String(c.dataset.value === state.location));
    count.textContent = shown === works.length ? `${works.length} works` : `${shown} of ${works.length} works`;
    empty.hidden = shown > 0;

    const q = new URLSearchParams();
    if (state.location !== "all") q.set("location", state.location);
    if (state.size !== "all") q.set("size", state.size);
    history.replaceState(null, "", q.toString() ? `?${q}` : location.pathname);
  }

  for (const c of chips) c.addEventListener("click", () => { state.location = c.dataset.value; apply(); });
  sizeSel.addEventListener("change", () => { state.size = sizeSel.value; apply(); });
  apply();

  // Lightbox: plain links still work without JS; with JS they open an enlarged view.
  const box = document.getElementById("lightbox");
  if (!box || typeof box.showModal !== "function") return;
  const img = box.querySelector("img");
  const caption = box.querySelector("figcaption");
  let visible = [];
  let index = 0;

  function show(i) {
    index = (i + visible.length) % visible.length;
    const w = visible[index];
    img.src = w.querySelector("a").href;
    img.alt = w.dataset.alt;
    caption.replaceChildren(...w.querySelector(".caption").cloneNode(true).childNodes);
  }

  for (const w of works) {
    w.querySelector("a").addEventListener("click", (e) => {
      e.preventDefault();
      visible = works.filter((x) => !x.hidden);
      show(visible.indexOf(w));
      if (!box.open) box.showModal();
    });
  }
  box.querySelector(".lb-prev").addEventListener("click", () => show(index - 1));
  box.querySelector(".lb-next").addEventListener("click", () => show(index + 1));
  box.querySelector(".lb-close").addEventListener("click", () => box.close());
  box.addEventListener("click", (e) => { if (e.target === box || e.target.tagName === "FIGURE") box.close(); });
  box.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") show(index - 1);
    if (e.key === "ArrowRight") show(index + 1);
  });
})();
