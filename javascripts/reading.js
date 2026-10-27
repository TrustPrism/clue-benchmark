(() => {
  "use strict";
  const skip = document.querySelector(".skip-reading");
  if (skip) document.body.prepend(skip);
  const toc = document.querySelector(".page-toc details");
  if (toc && window.matchMedia("(max-width: 800px)").matches) toc.open = false;

  document.querySelectorAll("main pre").forEach((pre) => {
    const code = pre.querySelector("code");
    if (!code) return;
    const wrapper = document.createElement("div");
    wrapper.className = "code-block";
    const toolbar = document.createElement("div");
    toolbar.className = "code-toolbar";
    const label = document.createElement("span");
    label.textContent = code.className.includes("python") ? "Python" : code.className.includes("json") ? "JSON" : "Terminal";
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "copy-command";
    copy.textContent = "Copy";
    copy.setAttribute("aria-label", `Copy ${label.textContent.toLowerCase()} example`);
    const status = document.createElement("span");
    status.className = "copy-status";
    status.setAttribute("role", "status");
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(code.textContent.replace(/\n$/, ""));
        copy.textContent = "Copied";
        status.textContent = "Example copied to clipboard.";
        window.setTimeout(() => { copy.textContent = "Copy"; status.textContent = ""; }, 1800);
      } catch {
        copy.textContent = "Select text";
        status.textContent = "Clipboard unavailable. Select the example to copy it.";
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(code);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    });
    toolbar.append(label, copy, status);
    pre.before(wrapper);
    wrapper.append(toolbar, pre);
    pre.tabIndex = 0;
    pre.setAttribute("aria-label", `${label.textContent} example`);
  });

  document.querySelectorAll("main table").forEach((table) => {
    const wrapper = document.createElement("div");
    wrapper.className = "table-scroll";
    wrapper.tabIndex = 0;
    wrapper.setAttribute("role", "region");
    wrapper.setAttribute("aria-label", "Scrollable data table");
    table.before(wrapper);
    wrapper.append(table);
    table.querySelectorAll("thead th").forEach((cell) => { cell.scope = "col"; });
  });

  const reference = document.querySelector(".parameter-reference");
  if (!reference) return;
  const headings = [...reference.querySelectorAll("h2")].filter((heading) => heading.querySelector("code"));
  const cards = headings.map((heading) => {
    const card = document.createElement("details");
    card.className = "parameter-card";
    card.id = heading.id;
    const summary = document.createElement("summary");
    const name = document.createElement("code");
    name.textContent = heading.querySelector("code").textContent;
    summary.append(name);
    card.append(summary);
    let next = heading.nextElementSibling;
    heading.before(card);
    while (next && next.tagName !== "H2" && !next.classList.contains("reading-next")) {
      const following = next.nextElementSibling;
      card.append(next);
      next = following;
    }
    heading.remove();
    return card;
  });
  if (!cards.length) return;
  const search = document.createElement("div");
  search.className = "parameter-search";
  const label = document.createElement("label");
  label.htmlFor = "parameter-filter";
  label.textContent = "Find a setting";
  const input = document.createElement("input");
  input.id = "parameter-filter";
  input.type = "search";
  input.placeholder = "Try: false reports, seed, workers…";
  const count = document.createElement("p");
  count.className = "parameter-count";
  count.setAttribute("role", "status");
  const actions = document.createElement("div");
  actions.className = "reference-actions";
  [ ["Expand all", true], ["Collapse all", false] ].forEach(([text, open]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = text;
    button.addEventListener("click", () => { cards.filter((card) => !card.hidden).forEach((card) => { card.open = open; }); });
    actions.append(button);
  });
  const filter = () => {
    const words = input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    cards.forEach((card) => { card.hidden = !words.every((word) => card.textContent.toLowerCase().includes(word)); });
    count.textContent = `${cards.filter((card) => !card.hidden).length} of ${cards.length} settings`;
  };
  input.addEventListener("input", filter);
  search.append(label, input, count, actions);
  cards[0].before(search);
  const revealAnchor = () => {
    let id;
    try { id = decodeURIComponent(window.location.hash.slice(1)); } catch { return; }
    const card = cards.find((item) => item.id === id);
    if (card) { input.value = ""; filter(); card.open = true; card.scrollIntoView({block: "start"}); }
  };
  filter();
  if (window.scrollSpy) window.scrollSpy.refresh();
  revealAnchor();
  window.addEventListener("hashchange", revealAnchor);
})();
