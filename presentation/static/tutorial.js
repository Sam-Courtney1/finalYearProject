(function () {
  'use strict';

  // Per-user localStorage key so each new account gets the tutorial
  var storageKey = 'tutorialComplete_' + (typeof TUTORIAL_USER !== 'undefined' ? TUTORIAL_USER : 'default');

  if (!FIRST_LOGIN || localStorage.getItem(storageKey) === 'true') {
    return;
  }

  var STEPS = [
    {
      target: '#homepage-greeting',
      title: 'Welcome to Your Dashboard!',
      text: 'This is your GDPR compliance hub. From here you can manage all your personal data, exercise your rights, and control how your information is used. Let\'s take a quick tour.',
      buttonText: 'Next',
      placement: 'below'
    },
    {
      target: '.navbar-nav',
      title: 'Navigation Bar',
      text: 'Use these links to quickly navigate between pages. You can access your Dashboard, fill out Questionnaires, manage your Consent, or Logout at any time.',
      buttonText: 'Next',
      placement: 'below'
    },
    {
      target: '#card-access',
      title: 'Right to Access',
      text: 'View all your stored personal data. Encrypted fields are decrypted on demand so you can see exactly what information is held about you. You can also export everything as a CSV file.',
      buttonText: 'Next',
      placement: 'right'
    },
    {
      target: '#card-edit',
      title: 'Right to Rectification',
      text: 'Edit any answers you\'ve previously submitted to questionnaires. All changes are recorded in the audit trail so there\'s a full history of modifications.',
      buttonText: 'Next',
      placement: 'left'
    },
    {
      target: '#card-consent',
      title: 'Consent Management',
      text: 'Withdraw or reinstate your consent for any submission. When consent is withdrawn, organisations can no longer see your data. You can reinstate it at any time.',
      buttonText: 'Next',
      placement: 'right'
    },
    {
      target: '#card-delete',
      title: 'Right to Erasure',
      text: 'Delete your account and all associated data permanently, or remove individual submissions while keeping your account. This is your right to be forgotten.',
      buttonText: 'Next',
      placement: 'left'
    },
    {
      target: 'a.nav-link[href*="questionnaire"]',
      title: 'Fill Out Questionnaires',
      text: 'Click Questionnaire in the navigation bar to view available questionnaires from registered organisations. This is where you submit your donor data.',
      buttonText: 'Next',
      placement: 'below'
    },
    {
      target: 'a.nav-link[href*="dashboard"]',
      title: 'Your Dashboard',
      text: 'The Dashboard shows your submission statistics, data subject request history, and an overview of your account activity.',
      buttonText: 'Next',
      placement: 'below'
    },
    {
      target: null,
      title: 'You\'re All Set!',
      text: 'Your data is encrypted with AES-256 and every action is logged in a tamper-evident audit trail. You\'re in full control of your personal information.',
      buttonText: 'Get Started',
      placement: 'center'
    }
  ];

  var currentStep = 0;
  var overlay = document.getElementById('tutorial-overlay');
  var spotlight = document.getElementById('tutorial-spotlight');
  var tooltip = document.getElementById('tutorial-tooltip');
  var titleEl = document.getElementById('tutorial-title');
  var textEl = document.getElementById('tutorial-text');
  var indicatorEl = document.getElementById('tutorial-step-indicator');
  var dotsEl = document.getElementById('tutorial-dots');
  var progressBar = document.getElementById('tutorial-progress-bar');
  var nextBtn = document.getElementById('tutorial-next');
  var skipBtn = document.getElementById('tutorial-skip');

  var elevatedElement = null;
  var TOOLTIP_W = 360;
  var GAP = 20;
  var VIEWPORT_PAD = 16;

  function getTooltipWidth() {
    return Math.min(TOOLTIP_W, window.innerWidth - VIEWPORT_PAD * 2);
  }

  function clampToViewport() {
    var tooltipH = tooltip.offsetHeight;
    var tooltipW = tooltip.offsetWidth;
    var currentTop = parseFloat(tooltip.style.top) || 0;
    var currentLeft = parseFloat(tooltip.style.left) || 0;
    var maxTop = window.innerHeight - tooltipH - VIEWPORT_PAD;
    var maxLeft = window.innerWidth - tooltipW - VIEWPORT_PAD;
    tooltip.style.top = Math.max(VIEWPORT_PAD, Math.min(currentTop, maxTop)) + 'px';
    tooltip.style.left = Math.max(VIEWPORT_PAD, Math.min(currentLeft, maxLeft)) + 'px';
  }

  function buildDots(activeIndex) {
    dotsEl.innerHTML = '';
    for (var i = 0; i < STEPS.length; i++) {
      var dot = document.createElement('span');
      dot.className = 'tutorial-dot';
      if (i === activeIndex) {
        dot.classList.add('active');
      } else if (i < activeIndex) {
        dot.classList.add('completed');
      }
      dotsEl.appendChild(dot);
    }
  }

  function triggerAnimation() {
    // Make tooltip visible and animate in
    tooltip.style.opacity = '1';
    tooltip.style.visibility = 'visible';
    tooltip.classList.remove('tutorial-animate');
    void tooltip.offsetWidth;
    tooltip.classList.add('tutorial-animate');
  }

  function hideTooltipInstantly() {
    // Hide tooltip instantly so it doesn't visibly fly across the screen
    tooltip.style.opacity = '0';
    tooltip.style.visibility = 'hidden';
    tooltip.classList.remove('tutorial-animate');
  }

  function positionTooltip(rect, placement) {
    tooltip.style.transform = '';
    var tooltipW = getTooltipWidth();
    tooltip.style.width = tooltipW + 'px';

    var pad = 12;

    // On narrow viewports there isn't room beside a target, force below/above
    var narrowViewport = window.innerWidth < 768;
    var effectivePlacement = (narrowViewport && (placement === 'right' || placement === 'left'))
      ? 'below'
      : placement;

    if (effectivePlacement === 'right') {
      // To the right of the target
      var leftPos = rect.right + pad + GAP;
      // If it overflows the right edge, fall back to left
      if (leftPos + tooltipW > window.innerWidth - VIEWPORT_PAD) {
        leftPos = rect.left - pad - GAP - tooltipW;
      }
      tooltip.style.left = leftPos + 'px';
      // Vertically center on target
      tooltip.style.top = Math.max(VIEWPORT_PAD, rect.top + rect.height / 2 - 140) + 'px';

    } else if (effectivePlacement === 'left') {
      // To the left of the target
      var leftPos2 = rect.left - pad - GAP - tooltipW;
      // If it overflows the left edge, fall back to right
      if (leftPos2 < VIEWPORT_PAD) {
        leftPos2 = rect.right + pad + GAP;
      }
      tooltip.style.left = leftPos2 + 'px';
      tooltip.style.top = Math.max(VIEWPORT_PAD, rect.top + rect.height / 2 - 140) + 'px';

    } else {
      // Below or above (for navbar, greeting, etc.)
      var tooltipLeft = rect.left + rect.width / 2 - tooltipW / 2;
      tooltipLeft = Math.max(VIEWPORT_PAD, Math.min(tooltipLeft, window.innerWidth - tooltipW - VIEWPORT_PAD));
      tooltip.style.left = tooltipLeft + 'px';

      var spaceBelow = window.innerHeight - rect.bottom;
      if (spaceBelow > 300) {
        tooltip.style.top = (rect.bottom + pad + GAP) + 'px';
      } else {
        tooltip.style.top = Math.max(VIEWPORT_PAD, rect.top - pad - GAP - 280) + 'px';
      }
    }

    // Final viewport clamp, guarantees Skip/Next stay visible
    requestAnimationFrame(clampToViewport);
  }

  function showStep(index) {
    var step = STEPS[index];
    currentStep = index;

    // Reset previously elevated element
    if (elevatedElement) {
      elevatedElement.style.position = '';
      elevatedElement.style.zIndex = '';
      elevatedElement.style.pointerEvents = '';
      elevatedElement = null;
    }

    // Hide tooltip instantly before repositioning
    hideTooltipInstantly();

    // Update content while hidden
    titleEl.textContent = step.title;
    textEl.textContent = step.text;
    indicatorEl.textContent = 'Step ' + (index + 1) + ' of ' + STEPS.length;
    nextBtn.textContent = step.buttonText;
    skipBtn.style.display = index === STEPS.length - 1 ? 'none' : '';

    buildDots(index);
    progressBar.style.width = (((index + 1) / STEPS.length) * 100) + '%';

    if (step.target === null) {
      spotlight.style.display = 'none';
      tooltip.style.top = '50%';
      tooltip.style.left = '50%';
      tooltip.style.transform = 'translate(-50%, -50%)';
      tooltip.style.width = getTooltipWidth() + 'px';
      triggerAnimation();
      return;
    }

    var target = document.querySelector(step.target);
    if (!target) {
      if (index < STEPS.length - 1) showStep(index + 1);
      return;
    }

    // Check if target is already fully visible in the viewport
    var checkRect = target.getBoundingClientRect();
    var isVisible = checkRect.top >= 0 && checkRect.bottom <= window.innerHeight;

    if (!isVisible) {
      // Needs scrolling, scroll then wait for it to finish
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(function () { positionOnTarget(target, step); }, 600);
    } else {
      // Already visible, position immediately, no scroll needed
      positionOnTarget(target, step);
    }
  }

  function positionOnTarget(target, step) {
    var rect = target.getBoundingClientRect();
    var pad = 12;

    // Spotlight (fixed positioning)
    spotlight.style.display = 'block';
    spotlight.style.top = (rect.top - pad) + 'px';
    spotlight.style.left = (rect.left - pad) + 'px';
    spotlight.style.width = (rect.width + pad * 2) + 'px';
    spotlight.style.height = (rect.height + pad * 2) + 'px';

    // Elevate target
    elevatedElement = target;
    var computedPos = window.getComputedStyle(target).position;
    if (computedPos === 'static') {
      target.style.position = 'relative';
    }
    target.style.zIndex = '10001';
    target.style.pointerEvents = 'none';

    // Position tooltip with explicit placement, then animate in
    positionTooltip(rect, step.placement);
    triggerAnimation();
  }

  function endTutorial() {
    if (elevatedElement) {
      elevatedElement.style.position = '';
      elevatedElement.style.zIndex = '';
      elevatedElement.style.pointerEvents = '';
      elevatedElement = null;
    }
    overlay.style.display = 'none';
    overlay.setAttribute('aria-hidden', 'true');
    localStorage.setItem(storageKey, 'true');
  }

  function nextStep() {
    if (currentStep >= STEPS.length - 1) {
      endTutorial();
    } else {
      showStep(currentStep + 1);
    }
  }

  nextBtn.addEventListener('click', nextStep);
  skipBtn.addEventListener('click', endTutorial);

  document.addEventListener('keydown', function (e) {
    if (overlay.style.display === 'none') return;
    if (e.key === 'ArrowRight' || e.key === 'Enter') {
      e.preventDefault();
      nextStep();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      endTutorial();
    }
  });

  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      if (overlay.style.display !== 'none') {
        showStep(currentStep);
      }
    }, 200);
  });

  setTimeout(function () {
    overlay.style.display = 'block';
    overlay.setAttribute('aria-hidden', 'false');
    showStep(0);
  }, 1000);
})();
