const menuToggle = document.getElementById('menuToggle');
const navLinks = document.getElementById('navLinks');

menuToggle.addEventListener('click', () => {
  const isOpen = navLinks.classList.toggle('open');
  menuToggle.setAttribute('aria-expanded', String(isOpen));
});

navLinks.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    navLinks.classList.remove('open');
    menuToggle.setAttribute('aria-expanded', 'false');
  });
});

// Front-end-only sample data. This does not query the project's Python database.
const sampleBooks = {
  BOOK001: { title: 'Physics', available: true },
  BOOK002: { title: 'Chemistry', available: false },
  BOOK003: { title: 'Mathematics', available: true },
  BOOK004: { title: 'Biology', available: true },
  BOOK005: { title: 'Social Science', available: false }
};

const bookSelect = document.getElementById('bookSelect');
const lookupBtn = document.getElementById('lookupBtn');
const lookupResult = document.getElementById('lookupResult');

lookupBtn.addEventListener('click', () => {
  const id = bookSelect.value;
  const book = sampleBooks[id];
  const state = book.available ? 'Available in demo' : 'Currently issued in demo';
  const color = book.available ? '#71e5bd' : '#f4c66b';
  const icon = book.available ? '✓' : '↗';
  lookupResult.innerHTML = `
    <span class="result-icon" style="color:${color};background:${color}20">${icon}</span>
    <div><strong>${book.title} · ${state}</strong>
    <small>${id} · Illustrative status only, not a live database result.</small></div>`;
});
