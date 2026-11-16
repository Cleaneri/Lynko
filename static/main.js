document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-copy]");
  if (!button) return;
  const value = button.getAttribute("data-copy");
  try {
    await navigator.clipboard.writeText(value);
    const oldText = button.textContent;
    button.textContent = "Kopyalandı ✓";
    setTimeout(() => button.textContent = oldText, 1500);
  } catch {
    window.prompt("Bağlantıyı kopyala:", value);
  }
});
