(function () {
    const index = window.DOCS_SEARCH_INDEX || [];
    const searchInput = document.getElementById('docs-search');
    const resultsEl = document.getElementById('docs-search-results');
    const contentEl = document.querySelector('.doc-content');
    let focusedIndex = -1;
    let currentMatches = [];

    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function highlightText(text, query) {
        if (!query || query.length < 2) return escapeHtml(text);
        const re = new RegExp('(' + escapeRegex(query) + ')', 'gi');
        return escapeHtml(text).replace(re, '<mark>$1</mark>');
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function snippet(text, query, maxLen) {
        const lower = text.toLowerCase();
        const q = query.toLowerCase();
        const pos = lower.indexOf(q);
        if (pos === -1) return text.slice(0, maxLen) + (text.length > maxLen ? '…' : '');
        const start = Math.max(0, pos - 40);
        const end = Math.min(text.length, pos + query.length + 80);
        let slice = text.slice(start, end);
        if (start > 0) slice = '…' + slice;
        if (end < text.length) slice = slice + '…';
        return slice;
    }

    function search(query) {
        if (!query || query.trim().length < 2) {
            resultsEl.classList.remove('open');
            resultsEl.innerHTML = '';
            currentMatches = [];
            focusedIndex = -1;
            return;
        }

        const q = query.trim();
        const qLower = q.toLowerCase();
        const grouped = {};

        index.forEach(page => {
            const pageHits = [];

            if (page.title.toLowerCase().includes(qLower)) {
                pageHits.push({
                    heading: page.title,
                    anchor: '',
                    snippet: snippet(page.full_text, q, 120),
                    url: page.url,
                });
            }

            page.sections.forEach(section => {
                const hay = (section.heading + ' ' + section.text).toLowerCase();
                if (hay.includes(qLower)) {
                    pageHits.push({
                        heading: section.heading || page.title,
                        anchor: section.anchor,
                        snippet: snippet(section.text || section.heading, q, 120),
                        url: page.url + (section.anchor ? '#' + section.anchor : ''),
                    });
                }
            });

            if (pageHits.length) {
                grouped[page.title] = { url: page.url, hits: pageHits };
            }
        });

        currentMatches = [];
        let html = '';

        const groups = Object.entries(grouped);
        if (!groups.length) {
            html = '<div class="search-no-results">No results for "' + escapeHtml(q) + '"</div>';
        } else {
            groups.forEach(([title, data]) => {
                html += '<div class="search-result-group">';
                html += '<div class="search-result-page">' + escapeHtml(title) + '</div>';
                data.hits.forEach(hit => {
                    const idx = currentMatches.length;
                    currentMatches.push({ url: hit.url, query: q });
                    html += '<a class="search-result-item" href="' + hit.url + '?q=' + encodeURIComponent(q) + '" data-idx="' + idx + '">';
                    html += '<div class="search-result-heading">' + highlightText(hit.heading, q) + '</div>';
                    html += '<div class="search-result-snippet">' + highlightText(hit.snippet, q) + '</div>';
                    html += '</a>';
                });
                html += '</div>';
            });
        }

        resultsEl.innerHTML = html;
        resultsEl.classList.add('open');
        focusedIndex = -1;
    }

    function applyPageHighlight() {
        if (!contentEl) return;
        const params = new URLSearchParams(window.location.search);
        const q = params.get('q');
        if (!q || q.length < 2) return;

        const walk = (node) => {
            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.textContent;
                const re = new RegExp('(' + escapeRegex(q) + ')', 'gi');
                if (!re.test(text)) return;
                re.lastIndex = 0;
                const span = document.createElement('span');
                span.innerHTML = escapeHtml(text).replace(re, '<mark class="search-highlight">$1</mark>');
                node.parentNode.replaceChild(span, node);
            } else if (node.nodeType === Node.ELEMENT_NODE && node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE' && !node.classList.contains('doc-mock')) {
                Array.from(node.childNodes).forEach(walk);
            }
        };

        walk(contentEl);

        const first = contentEl.querySelector('mark.search-highlight');
        if (first) {
            first.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', () => search(searchInput.value));
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim().length >= 2) search(searchInput.value);
        });

        searchInput.addEventListener('keydown', (e) => {
            const items = resultsEl.querySelectorAll('.search-result-item');
            if (!items.length) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                focusedIndex = Math.min(focusedIndex + 1, items.length - 1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                focusedIndex = Math.max(focusedIndex - 1, 0);
            } else if (e.key === 'Enter' && focusedIndex >= 0) {
                e.preventDefault();
                items[focusedIndex].click();
                return;
            } else if (e.key === 'Escape') {
                resultsEl.classList.remove('open');
                searchInput.blur();
                return;
            } else {
                return;
            }

            items.forEach((el, i) => el.classList.toggle('focused', i === focusedIndex));
            if (focusedIndex >= 0) items[focusedIndex].scrollIntoView({ block: 'nearest' });
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('#docs-search-wrap')) {
                resultsEl.classList.remove('open');
            }
        });
    }

    applyPageHighlight();
})();
