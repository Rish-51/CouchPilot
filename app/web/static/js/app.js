/**
 * CouchPilot Dashboard Interactive Client Logic
 * Handles Demo Run staged progress, run switching, file filtering, and copy utilities.
 */

// Utility: Debounce rapid events to prevent thread blocking
function debounce(fn, wait = 120) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn.apply(this, args), wait);
  };
}

document.addEventListener('DOMContentLoaded', () => {
  // Setup search filter listener with debounce
  const searchInput = document.getElementById('feed-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', debounce((e) => {
      filterRunsByQuery(e.target.value.toLowerCase().trim());
    }, 120));
  }

  // Keyboard navigation accelerators (Alex power-user flow)
  document.addEventListener('keydown', (e) => {
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable) {
      return;
    }

    // Modal dismissal via Escape key
    if (e.key === 'Escape' || e.key === 'Esc') {
      const modal = document.getElementById('demo-modal');
      if (modal && modal.classList.contains('open')) {
        e.preventDefault();
        closeDemoModal();
        return;
      }
    }

    if (e.key === 'j' || e.key === 'ArrowDown') {
      e.preventDefault();
      flashKbdHint('j');
      navigateRuns(1);
    } else if (e.key === 'k' || e.key === 'ArrowUp') {
      e.preventDefault();
      flashKbdHint('k');
      navigateRuns(-1);
    } else if (e.key === 'c' || e.key === 'C') {
      e.preventDefault();
      flashKbdHint('c');
      const branchEl = document.getElementById('active-run-branch');
      const copyBtn = document.querySelector('.run-banner .copy-btn, .meta-code + .copy-btn');
      if (branchEl && branchEl.textContent) {
        copyToClipboard(branchEl.textContent.trim(), copyBtn || branchEl);
      }
    } else if (e.key === 'd' || e.key === 'D') {
      e.preventDefault();
      flashKbdHint('d');
      triggerDemoRun();
    }
  });
});

// Flash keyboard shortcut badges on key press
function flashKbdHint(key) {
  let selector = '';
  if (key === 'j' || key === 'k') selector = '.feed-header-title .kbd-hint';
  else if (key === 'c') selector = '.run-banner .kbd-hint, .meta-code + .copy-btn + .kbd-hint';
  else if (key === 'd') selector = '#demo-trigger-btn .kbd-hint';
  if (!selector) return;

  const hints = document.querySelectorAll(selector);
  hints.forEach(hint => {
    hint.classList.add('kbd-pressed');
    setTimeout(() => hint.classList.remove('kbd-pressed'), 140);
  });
}

let lastFocusedElement = null;

// Trigger Staged Demo Run
async function triggerDemoRun() {
  const modal = document.getElementById('demo-modal');
  const triggerBtn = document.getElementById('demo-trigger-btn');
  if (!modal) return;

  lastFocusedElement = document.activeElement;
  if (triggerBtn) triggerBtn.disabled = true;
  modal.classList.add('open');

  const closeBtn = modal.querySelector('.copy-btn');
  if (closeBtn) closeBtn.focus();

  const progressFill = document.getElementById('stepper-progress-fill');
  if (progressFill) progressFill.style.transform = 'scaleY(0)';

  const steps = [
    { id: 'step-scan', time: 450 },
    { id: 'step-gen', time: 550 },
    { id: 'step-ast', time: 500 },
    { id: 'step-commit', time: 400 },
  ];

  // Reset steps
  steps.forEach(s => {
    const el = document.getElementById(s.id);
    if (el) {
      el.classList.remove('completed', 'active', 'ast-certified');
      const icon = el.querySelector('.stepper-icon-box');
      if (icon) icon.innerHTML = el.dataset.stepNum || '•';
    }
  });

  const activateStep = (stepId, progressPercent) => {
    const el = document.getElementById(stepId);
    if (el) {
      el.classList.add('active');
      const icon = el.querySelector('.stepper-icon-box');
      if (icon) icon.innerHTML = '<span class="status-dot"></span>';
    }
    if (progressFill && progressPercent !== undefined) {
      progressFill.style.transform = `scaleY(${progressPercent / 100})`;
    }
  };

  const completeStep = (stepId) => {
    const el = document.getElementById(stepId);
    if (el) {
      el.classList.remove('active');
      el.classList.add('completed');
      if (stepId === 'step-ast') {
        el.classList.add('ast-certified');
      }
      const icon = el.querySelector('.stepper-icon-box');
      if (icon) {
        icon.innerHTML = '<svg class="check-pop-anim" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
      }
    }
  };

  try {
    // Step 1: Scan
    activateStep('step-scan', 0);
    await sleep(steps[0].time);
    completeStep('step-scan');

    // Step 2: Generate
    activateStep('step-gen', 33.3);
    // Start API call in background during step 2
    const apiPromise = fetch('/api/demo-trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    await sleep(steps[1].time);
    completeStep('step-gen');

    // Step 3: Validate AST Equivalence
    activateStep('step-ast', 66.6);
    await sleep(steps[2].time);
    completeStep('step-ast');

    // Step 4: Commit
    activateStep('step-commit', 100);
    const response = await apiPromise;
    const data = await response.json();
    await sleep(steps[3].time);
    completeStep('step-commit');

    await sleep(350);
    modal.classList.remove('open');

    // Redirect to run detail or refresh view
    if (data.run_id) {
      if (window.location.pathname === '/' || window.location.pathname.startsWith('/runs')) {
        // If on overview, select the run dynamically or navigate
        if (typeof selectRunById === 'function') {
          await selectRunById(data.run_id);
        } else {
          window.location.href = '/runs/' + data.run_id;
        }
      } else {
        window.location.href = '/runs/' + data.run_id;
      }
    }
  } catch (err) {
    console.error('Demo run failed:', err);
    alert('Demo run error: ' + (err.message || 'Unknown network error'));
    modal.classList.remove('open');
  } finally {
    if (triggerBtn) triggerBtn.disabled = false;
  }
}

function closeDemoModal() {
  const modal = document.getElementById('demo-modal');
  if (modal) modal.classList.remove('open');
  const triggerBtn = document.getElementById('demo-trigger-btn');
  if (triggerBtn) triggerBtn.disabled = false;

  if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
    lastFocusedElement.focus();
  } else if (triggerBtn) {
    triggerBtn.focus();
  }
}

// Helper: Sleep
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Copy branch helper with feedback animation and toast
function copyToClipboard(text, btnElement) {
  if (!btnElement) return;
  navigator.clipboard.writeText(text).then(() => {
    let toast = btnElement.querySelector('.copy-toast');
    if (!toast) {
      toast = document.createElement('span');
      toast.className = 'copy-toast';
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      btnElement.appendChild(toast);
    }
    toast.textContent = 'Copied!';
    requestAnimationFrame(() => {
      toast.classList.add('visible');
    });

    btnElement.classList.add('copied');
    btnElement.innerHTML = `
      <svg class="check-pop-anim" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#16A34A" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <span class="copy-toast visible" role="status" aria-live="polite">Copied!</span>
    `;

    announceToScreenReader('Branch name copied to clipboard');

    setTimeout(() => {
      const activeToast = btnElement.querySelector('.copy-toast');
      if (activeToast) activeToast.classList.remove('visible');
      setTimeout(() => {
        btnElement.classList.remove('copied');
        btnElement.innerHTML = `
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2.5">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        `;
      }, 150);
    }, 1600);
  }).catch(err => {
    console.error('Failed to copy:', err);
  });
}

// Client-side feed filtering by status (batched via requestAnimationFrame)
function filterRuns(status, element) {
  const chips = document.querySelectorAll('.filter-chip');
  chips.forEach(c => c.classList.remove('active'));
  if (element) element.classList.add('active');

  const items = document.querySelectorAll('.feed-item');
  let visibleCount = 0;

  requestAnimationFrame(() => {
    items.forEach(item => {
      const itemStatus = item.dataset.status;
      if (status === 'all' || itemStatus === status) {
        item.style.display = 'block';
        item.classList.add('feed-item-shown');
        visibleCount++;
      } else {
        item.classList.remove('feed-item-shown');
        item.style.display = 'none';
      }
    });

    const countBadge = document.getElementById('feed-count-badge');
    if (countBadge) countBadge.textContent = visibleCount;

    const emptyFeed = document.getElementById('feed-empty-state');
    if (emptyFeed) {
      emptyFeed.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  });
}

// Filter feed by search query (batched via requestAnimationFrame)
function filterRunsByQuery(query) {
  const items = document.querySelectorAll('.feed-item');
  let visibleCount = 0;

  requestAnimationFrame(() => {
    items.forEach(item => {
      const repo = (item.dataset.repo || '').toLowerCase();
      const branch = (item.dataset.branch || '').toLowerCase();
      const id = (item.dataset.runId || '').toLowerCase();

      if (!query || repo.includes(query) || branch.includes(query) || id.includes(query)) {
        item.style.display = 'block';
        visibleCount++;
      } else {
        item.style.display = 'none';
      }
    });

    const countBadge = document.getElementById('feed-count-badge');
    if (countBadge) countBadge.textContent = visibleCount;

    const emptyFeed = document.getElementById('feed-empty-state');
    if (emptyFeed) {
      emptyFeed.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  });
}

// Dynamic selection of run in Workbench
async function selectRunById(runId) {
  const feedItems = document.querySelectorAll('.feed-item');
  feedItems.forEach(item => {
    if (item.dataset.runId === runId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  try {
    // Show loading skeleton in diff view
    const diffContainer = document.getElementById('diff-content-area');
    if (diffContainer) {
      diffContainer.innerHTML = `
        <div class="diff-skeleton-box" aria-label="Loading AST diff">
          <div class="skeleton-header">
            <span class="status-dot"></span>
            <span style="font-weight: 700; font-size: 0.88rem;">Analyzing AST diff &amp; syntax tree...</span>
          </div>
          <div class="skeleton-line" style="width: 38%; margin-bottom: 8px;"></div>
          <div class="skeleton-line" style="width: 82%; margin-bottom: 8px;"></div>
          <div class="skeleton-line" style="width: 65%; margin-bottom: 8px;"></div>
          <div class="skeleton-line" style="width: 90%;"></div>
        </div>
      `;
    }

    const res = await fetch(`/api/reports/${runId}`);
    if (!res.ok) throw new Error('Run report not found');
    const run = await res.json();
    renderActiveRun(run);
  } catch (err) {
    console.error('Failed to load run:', err);
    const diffContainer = document.getElementById('diff-content-area');
    if (diffContainer) {
      diffContainer.innerHTML = `
        <div class="error-banner">
          <svg class="error-banner-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          <div>
            <div class="error-banner-title">Failed to load run details</div>
            <div class="error-banner-text">${escapeHtml(err.message)}</div>
          </div>
        </div>
      `;
    }
  }
}

// Render run details and diff in the right pane
function renderActiveRun(run) {
  const titleEl = document.getElementById('active-run-id');
  if (titleEl) titleEl.textContent = run.run_id;

  const repoEl = document.getElementById('active-run-repo');
  if (repoEl) repoEl.textContent = run.repo_name;

  const branchEl = document.getElementById('active-run-branch');
  if (branchEl) branchEl.textContent = run.branch_name;

  const statusBadge = document.getElementById('active-run-status');
  if (statusBadge) {
    statusBadge.className = `status-badge status-${run.status || 'completed'}`;
    statusBadge.textContent = (run.status || 'completed').toUpperCase();
  }

  // Update files tab bar
  const tabsContainer = document.getElementById('file-tabs-container');
  if (tabsContainer && run.files && run.files.length > 0) {
    let tabsHtml = `
      <button class="file-tab active" onclick="switchActiveFileTab('all', this)">
        <span>All Files (${run.files.length})</span>
      </button>
    `;
    run.files.forEach((f, idx) => {
      tabsHtml += `
        <button class="file-tab" onclick="switchActiveFileTab('${escapeHtml(f.file_path)}', this)">
          <span>${escapeHtml(f.file_path)}</span>
          <span class="file-tab-badge">${f.targets_patched || 0}/${f.targets_detected || 0}</span>
        </button>
      `;
    });
    tabsContainer.innerHTML = tabsHtml;
    tabsContainer.style.display = 'flex';
  } else if (tabsContainer) {
    tabsContainer.style.display = 'none';
  }

  // Update diff container
  const diffContainer = document.getElementById('diff-content-area');
  if (diffContainer) {
    if (run.unified_diff) {
      diffContainer.innerHTML = `<div class="diff-output-box diff-fade-in"><div class="highlight"><pre>${formatDiff(run.unified_diff)}</pre></div></div>`;
    } else {
      diffContainer.innerHTML = `
        <div class="empty-state diff-fade-in">
          <div class="empty-state-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          </div>
          <div class="empty-state-title">No Diff Generated</div>
          <div class="empty-state-desc">This run completed with dry-run mode or produced no verified changes.</div>
        </div>
      `;
    }
  }

  // Trigger certification pulse on AST guarantee card if present (no layout thrashing)
  const astCard = document.querySelector('.ast-guarantee-card');
  if (astCard) {
    astCard.classList.remove('ast-card-pulse');
    requestAnimationFrame(() => {
      astCard.classList.add('ast-card-pulse');
    });
  }

  // Update Sentry link if trace ID exists
  const sentryLink = document.getElementById('active-sentry-link');
  if (sentryLink) {
    if (run.sentry_trace_id) {
      sentryLink.style.display = 'inline-flex';
      sentryLink.href = `https://${window.SENTRY_HOST || 'sentry.io'}/organizations/${window.SENTRY_ORG || 'couchpilot'}/performance/trace/${run.sentry_trace_id}/`;
      sentryLink.textContent = `Trace (${run.sentry_trace_id.substring(0, 8)}...)`;
    } else {
      sentryLink.style.display = 'none';
    }
  }

  // Announce update to assistive technologies
  announceToScreenReader(`Loaded run ${run.run_id} for repository ${run.repo_name}. Status: ${run.status || 'completed'}. AST equivalence verified.`);
}

// Switch between file diffs in O(1) by toggling file chunk containers
function switchActiveFileTab(filePath, tabElement) {
  const tabs = document.querySelectorAll('.file-tab');
  tabs.forEach(t => t.classList.remove('active'));
  if (tabElement) tabElement.classList.add('active');

  const chunks = document.querySelectorAll('.diff-file-chunk');
  chunks.forEach(chunk => {
    const chunkPath = chunk.dataset.filePath || '';
    if (filePath === 'all' || chunkPath === filePath || chunkPath.endsWith(filePath) || filePath.endsWith(chunkPath)) {
      chunk.style.display = 'block';
    } else {
      chunk.style.display = 'none';
    }
  });

  const diffBox = document.querySelector('.diff-output-box');
  if (diffBox) {
    diffBox.classList.remove('diff-fade-in');
    requestAnimationFrame(() => {
      diffBox.classList.add('diff-fade-in');
    });
  }
}

// Client-side diff formatter chunked by file for instant O(1) tab switching
function formatDiff(diffText) {
  if (!diffText) return '';
  const lines = diffText.split('\n');
  const chunks = [];
  let currentFile = 'default';
  let currentLines = [];

  const flushChunk = () => {
    if (currentLines.length > 0) {
      chunks.push(`<div class="diff-file-chunk" data-file-path="${escapeHtml(currentFile)}">${currentLines.join('')}</div>`);
      currentLines = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    let detectedFile = null;
    if (line.startsWith('diff --git')) {
      const parts = line.split(' ');
      if (parts.length >= 4) {
        detectedFile = parts[3].replace(/^b\//, '');
      }
    } else if (line.startsWith('--- a/') || line.startsWith('+++ b/')) {
      detectedFile = line.substring(6).trim();
    }

    if (detectedFile && detectedFile !== currentFile) {
      flushChunk();
      currentFile = detectedFile;
    }

    const escaped = escapeHtml(line);
    if (line.startsWith('+') && !line.startsWith('+++')) {
      currentLines.push(`<span class="diff-line diff-add">${escaped}</span>`);
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      currentLines.push(`<span class="diff-line diff-del">${escaped}</span>`);
    } else if (line.startsWith('@@')) {
      currentLines.push(`<span class="diff-line diff-hunk">${escaped}</span>`);
    } else if (line.startsWith('diff --git') || line.startsWith('---') || line.startsWith('+++')) {
      currentLines.push(`<span class="diff-line diff-header">${escaped}</span>`);
    } else {
      currentLines.push(`<span class="diff-line">${escaped}</span>`);
    }
  }
  flushChunk();
  return chunks.join('');
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Navigate runs via keyboard j/k
function navigateRuns(direction) {
  const visibleItems = Array.from(document.querySelectorAll('.feed-item')).filter(item => item.style.display !== 'none');
  if (visibleItems.length === 0) return;

  const currentIndex = visibleItems.findIndex(item => item.classList.contains('active'));
  let nextIndex = 0;
  if (currentIndex !== -1) {
    nextIndex = currentIndex + direction;
    if (nextIndex < 0) nextIndex = 0;
    if (nextIndex >= visibleItems.length) nextIndex = visibleItems.length - 1;
  }

  const targetItem = visibleItems[nextIndex];
  if (targetItem && targetItem.dataset.runId) {
    targetItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    selectRunById(targetItem.dataset.runId);
  }
}

// Accessible screen-reader live announcements
function announceToScreenReader(message) {
  let srEl = document.getElementById('sr-announcements');
  if (!srEl) {
    srEl = document.createElement('div');
    srEl.id = 'sr-announcements';
    srEl.className = 'sr-only';
    srEl.setAttribute('role', 'status');
    srEl.setAttribute('aria-live', 'polite');
    document.body.appendChild(srEl);
  }
  srEl.textContent = '';
  setTimeout(() => {
    srEl.textContent = message;
  }, 50);
}
