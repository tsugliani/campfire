document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-href]').forEach(card => {
    card.style.cursor = 'pointer';
    card.addEventListener('click', (e) => {
      // Don't navigate if the user clicked an inner link
      if (e.target.closest('a')) return;
      window.location.href = card.dataset.href;
    });
  });
});
