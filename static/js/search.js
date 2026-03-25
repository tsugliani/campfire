(() => {
  let links = [];
  let searchInput, searchResults;
  let activeIndex = -1;

  async function loadIndex() {
    try {
      const resp = await fetch('/index.json');
      links = await resp.json();
    } catch (e) {
      console.error('Failed to load search index:', e);
    }
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function search(query) {
    if (!query) return [];
    const q = query.toLowerCase();
    return links.filter(link => {
      const fields = [
        link.title,
        link.description,
        link.url_link,
        String(link.year),
        'w' + link.week,
        'week ' + link.week,
        ...(link.tags || [])
      ];
      return fields.some(f => f && f.toLowerCase().includes(q));
    });
  }

  function getItems() {
    return searchResults.querySelectorAll('.search-result-item');
  }

  function setActive(index) {
    const items = getItems();
    items.forEach(el => el.classList.remove('active'));
    activeIndex = index;
    if (index >= 0 && index < items.length) {
      items[index].classList.add('active');
      items[index].scrollIntoView({ block: 'nearest' });
    }
  }

  function renderResults(results) {
    activeIndex = -1;
    if (!results.length) {
      searchResults.innerHTML = '<div class="search-no-results">No results found</div>';
      return;
    }
    searchResults.innerHTML = results.map(link => {
      return `
        <a href="${escapeHtml(link.permalink)}" class="search-result-item">
          <div class="search-result-title">${escapeHtml(link.title)}</div>
          <div class="search-result-meta">
            <span>${link.year}/w${link.week}</span>
          </div>
          ${link.description ? `<div class="search-result-desc">${escapeHtml(link.description.split('\n\n')[0].substring(0, 200))}</div>` : ''}
        </a>
      `;
    }).join('');
  }

  document.addEventListener('DOMContentLoaded', () => {
    searchInput = document.getElementById('search-input');
    searchResults = document.getElementById('search-results');
    if (!searchInput || !searchResults) return;

    loadIndex();

    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim();
      if (!q) {
        searchResults.innerHTML = '';
        searchResults.classList.remove('active');
        return;
      }
      const results = search(q);
      renderResults(results);
      searchResults.classList.add('active');
    });

    searchInput.addEventListener('keydown', (e) => {
      const items = getItems();
      if (!items.length) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActive(activeIndex < items.length - 1 ? activeIndex + 1 : 0);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActive(activeIndex > 0 ? activeIndex - 1 : items.length - 1);
      } else if (e.key === 'Enter' && activeIndex >= 0) {
        e.preventDefault();
        items[activeIndex].click();
      } else if (e.key === 'Escape') {
        searchResults.classList.remove('active');
        searchInput.blur();
      }
    });

    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.classList.remove('active');
      }
    });

    searchInput.addEventListener('focus', () => {
      if (searchInput.value.trim()) {
        searchResults.classList.add('active');
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'k' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
    });
  });
})();
