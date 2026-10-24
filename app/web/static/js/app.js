/**
 * CouchPilot Dashboard Interactive Client Logic
 * Handles Demo Run staged progress, run switching, file filtering, and copy utilities.
 */

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // Setup search filter listener if present
  const searchInput = document.getElementById('feed-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      filterRunsByQuery(e.target.value.toLowerCase().trim());
    });
  }
});

// Trigger Staged Demo Run
async function triggerDemoRun() {
  const modal = document.getElementById('demo-modal');
  const triggerBtn = document.getElementById('demo-trigger-btn');
  if (!modal) return;

  if (triggerBtn) triggerBtn.disabled = true;
  modal.classList.add('open');

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
      el.classList.remove('completed', 'active');
      const icon = el.querySelector('.stepper-icon-box');
      if (icon) icon.innerHTML = el.dataset.stepNum || '•';
    }
  });

  const activateStep = (stepId) => {
    const el = document.getElementById(stepId);
    if (el) {
      el.classList.add('active');
      const icon = el.querySelector('.stepper-icon-box');
      if (icon) icon.innerHTML = '<span class="status-dot"></span>';
    }
  };

  const completeStep = (stepId) => {
    const el = document.getElementById(stepId);
    if (el) {
      el.classList.remove('active');
      el.classList.add('completed');
      const icon = el.querySelector('.stepper-icon-box');
      if (icon) icon.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    }
  };

  try {
    // Step 1: Scan
    activateStep('step-scan');
    await sleep(steps[0].time);
    completeStep('step-scan');

    // Step 2: Generate
    activateStep('step-gen');
    // Start API call in background during step 2
    const apiPromise = fetch('/api/demo-trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    await sleep(steps[1].time);
    completeStep('step-gen');

    // Step 3: Validate AST Equivalence
    activateStep('step-ast');
    await sleep(steps[2].time);
    completeStep('step-ast');

    // Step 4: Commit
    activateStep('step-commit');
    const response = await apiPromise;
    const data = await response.json();
    await sleep(steps[3].time);
    completeStep('step-commit');

    await sleep(300);
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
}

// Helper: Sleep
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Copy branch helper
function copyToClipboard(text, btnElement) {
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btnElement.getAttribute('title') || 'Copy';
    btnElement.setAttribute('title', 'Copied!');
    btnElement.style.color = 'var(--diff-add)';
    setTimeout(() => {
      btnElement.setAttribute('title', originalText);
      btnElement.style.color = '';
    }, 2000);
  }).catch(err => {
    console.error('Failed to copy:', err);
  });
}

// Client-side feed filtering by status
function filterRuns(status, element) {
  const chips = document.querySelectorAll('.filter-chip');
  chips.forEach(c => c.classList.remove('active'));
  if (element) element.classList.add('active');

  const items = document.querySelectorAll('.feed-item');
  let visibleCount = 0;

  items.forEach(item => {
    const itemStatus = item.dataset.status;
    if (status === 'all' || itemStatus === status) {
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
}

// Filter feed by search query
function filterRunsByQuery(query) {
  const items = document.querySelectorAll('.feed-item');
  let visibleCount = 0;

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
        <div style="padding: 32px; text-align: center; color: var(--slate-muted);">
          <div class="status-dot" style="display: inline-block; margin-bottom: 8px;"></div>
          <p>Loading run details and syntax-highlighted diff...</p>
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
      diffContainer.innerHTML = `<div class="diff-output-box"><div class="highlight"><pre>${formatDiff(run.unified_diff)}</pre></div></div>`;
    } else {
      diffContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          </div>
          <div class="empty-state-title">No Diff Generated</div>
          <div class="empty-state-desc">This run completed with dry-run mode or produced no verified changes.</div>
        </div>
      `;
    }
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

  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// Switch between file diffs
function switchActiveFileTab(filePath, tabElement) {
  const tabs = document.querySelectorAll('.file-tab');
  tabs.forEach(t => t.classList.remove('active'));
  if (tabElement) tabElement.classList.add('active');

  const diffLines = document.querySelectorAll('.diff-line');
  if (!diffLines || diffLines.length === 0) return;

  if (filePath === 'all') {
    diffLines.forEach(l => l.style.display = 'block');
  } else {
    // Filter lines belonging to this file or show matching hunks
    let inFile = false;
    diffLines.forEach(l => {
      const text = l.textContent || '';
      if (text.startsWith('--- a/') || text.startsWith('+++ b/') || text.startsWith('diff --git')) {
        inFile = text.includes(filePath);
      }
      l.style.display = inFile ? 'block' : 'none';
    });
  }
}

// Client-side diff formatter mapping directly to CouchPilot tokens
function formatDiff(diffText) {
  if (!diffText) return '';
  const lines = diffText.split('\n');
  return lines.map(line => {
    const escaped = escapeHtml(line);
    if (line.startsWith('+') && !line.startsWith('+++')) {
      return `<span class="diff-line diff-add">${escaped}</span>`;
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      return `<span class="diff-line diff-del">${escaped}</span>`;
    } else if (line.startsWith('@@')) {
      return `<span class="diff-line diff-hunk">${escaped}</span>`;
    } else if (line.startsWith('diff --git') || line.startsWith('---') || line.startsWith('+++')) {
      return `<span class="diff-line diff-header">${escaped}</span>`;
    }
    return `<span class="diff-line">${escaped}</span>`;
  }).join('');
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
