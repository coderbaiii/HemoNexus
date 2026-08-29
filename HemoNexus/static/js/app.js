/**
 * HemoNexus Core Application Controller
 * Handles global UI behaviors: Modals, Toasts, Responsive Navigation,
 * Role-Based Login & Register Switcher, Interactive Blood Compatibility Visualizer,
 * Heartbeat Spinners, and Animated Statistics.
 */

// Authentication & Role Toggle Controller (Requirement 1 & 5)
const HemoAuth = (() => {
  const switchRole = (role) => {
    const isDonor = role === 'donor';
    const roleInput = document.getElementById('authRoleInput');
    if (roleInput) roleInput.value = role;

    // Toggle pill buttons
    const donorBtn = document.getElementById('toggleDonorBtn');
    const patientBtn = document.getElementById('togglePatientBtn');
    if (donorBtn && patientBtn) {
      donorBtn.classList.toggle('active', isDonor);
      donorBtn.setAttribute('aria-selected', isDonor ? 'true' : 'false');
      patientBtn.classList.toggle('active', !isDonor);
      patientBtn.setAttribute('aria-selected', !isDonor ? 'true' : 'false');
    }

    // Update Headings & Messages
    const titleEl = document.getElementById('loginHeaderTitle');
    const subtitleEl = document.getElementById('loginHeaderSubtitle');
    const contextText = document.getElementById('roleContextText');
    const regLink = document.getElementById('registerRoleLink');
    const donorFields = document.getElementById('donorFieldSub');
    const patientFields = document.getElementById('patientFieldSub');

    if (isDonor) {
      if (titleEl) titleEl.textContent = 'Donor Portal Sign In';
      if (subtitleEl) subtitleEl.textContent = 'Sign in to access your verified HemoNexus donor profile & cooldown tracker';
      if (contextText) {
        contextText.innerHTML = '<strong>Volunteer Donor Portal:</strong> Check donation cooldown, review emergency broadcasts, and manage your availability status.';
      }
      if (regLink) {
        regLink.href = '/register?role=donor';
        regLink.textContent = 'Register as a Volunteer Donor';
      }
      if (donorFields) donorFields.classList.remove('d-none');
      if (patientFields) patientFields.classList.add('d-none');
    } else {
      if (titleEl) titleEl.textContent = 'Patient & Hospital Sign In';
      if (subtitleEl) subtitleEl.textContent = 'Sign in to request urgent blood units & track live donor dispatches';
      if (contextText) {
        contextText.innerHTML = '<strong>Emergency Blood Seeker Portal:</strong> Broadcast critical blood requirements directly to compatible nearby donors.';
      }
      if (regLink) {
        regLink.href = '/register?role=patient';
        regLink.textContent = 'Register as a Patient or Hospital';
      }
      if (donorFields) donorFields.classList.add('d-none');
      if (patientFields) patientFields.classList.remove('d-none');
    }
  };

  const switchRegRole = (role) => {
    const isDonor = role === 'donor';
    const regRoleInput = document.getElementById('regRoleInput');
    if (regRoleInput) regRoleInput.value = role;

    const donorBtn = document.getElementById('regToggleDonorBtn');
    const patientBtn = document.getElementById('regTogglePatientBtn');
    if (donorBtn && patientBtn) {
      donorBtn.classList.toggle('active', isDonor);
      patientBtn.classList.toggle('active', !isDonor);
    }

    const titleEl = document.getElementById('registerHeaderTitle');
    const subtitleEl = document.getElementById('registerHeaderSubtitle');
    if (titleEl && subtitleEl) {
      if (isDonor) {
        titleEl.textContent = 'Register as a Volunteer Donor';
        subtitleEl.textContent = 'Join the verified donor directory to respond to urgent blood requirements.';
      } else {
        titleEl.textContent = 'Register as a Patient or Hospital';
        subtitleEl.textContent = 'Connect with regional blood banks and initiate rapid emergency dispatches.';
      }
    }
  };

  const togglePasswordVisibility = (inputId, triggerBtn) => {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    if (triggerBtn) {
      const icon = triggerBtn.querySelector('i');
      if (icon) {
        icon.className = isPassword ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye';
      }
    }
  };

  const handleLoginSubmit = (event) => {
    const btn = document.getElementById('loginSubmitBtn');
    if (btn) {
      // Heartbeat spinner state (Requirement 5)
      btn.disabled = true;
      btn.innerHTML = `
        <span class="heartbeat-spinner me-2"><i class="fa-solid fa-heart-pulse"></i></span>
        <span>Authenticating Security Credentials...</span>
      `;
    }
  };

  const handleRegSubmit = (event) => {
    const btn = document.getElementById('registerSubmitBtn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <span class="heartbeat-spinner me-2"><i class="fa-solid fa-heart-pulse"></i></span>
        <span>Registering Verified Profile...</span>
      `;
    }
  };

  return {
    switchRole,
    switchRegRole,
    togglePasswordVisibility,
    handleLoginSubmit,
    handleRegSubmit
  };
})();

// UI & Platform Controller
const HemoUI = (() => {
  // Initialize on DOM Ready
  document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initModals();
    initTabs();
    initQuickSearch();
    initCompatibilityVisualizer();
    initAnimatedStats();
    initHeroBloodTiles();
  });

  /**
   * Hero Blood Selection Tile Helper
   */
  const initHeroBloodTiles = () => {
    const tiles = document.querySelectorAll('.hero-blood-tile');
    tiles.forEach(tile => {
      tile.addEventListener('click', () => {
        tiles.forEach(t => t.classList.remove('selected'));
        tile.classList.add('selected');
        const radio = tile.querySelector('input[type="radio"]');
        if (radio) {
          radio.checked = true;
          const input = document.getElementById('heroBloodGroupInput');
          if (input) input.value = radio.value;
        }
      });
    });
  };

  /**
   * Sidebar Drawer Toggle for Mobile / Tablets
   */
  const initSidebar = () => {
    const toggleBtn = document.getElementById('sidebarToggleBtn');
    const sidebar = document.getElementById('appSidebar');

    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        sidebar.classList.toggle('show-drawer');
      });

      document.addEventListener('click', (e) => {
        if (sidebar.classList.contains('show-drawer') && !sidebar.contains(e.target) && e.target !== toggleBtn) {
          sidebar.classList.remove('show-drawer');
        }
      });
    }
  };

  /**
   * Modal Manager
   */
  const initModals = () => {
    document.querySelectorAll('[data-modal-target]').forEach(trigger => {
      trigger.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = trigger.getAttribute('data-modal-target');
        openModal(targetId);
      });
    });

    document.querySelectorAll('[data-modal-close]').forEach(closeBtn => {
      closeBtn.addEventListener('click', () => {
        const modal = closeBtn.closest('.modal-backdrop');
        if (modal) closeModal(modal.id);
      });
    });

    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) {
          closeModal(backdrop.id);
        }
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const activeModal = document.querySelector('.modal-backdrop.show');
        if (activeModal) closeModal(activeModal.id);
      }
    });
  };

  const openModal = (modalId) => {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('show');
      document.body.style.overflow = 'hidden';
    }
  };

  const closeModal = (modalId) => {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('show');
      document.body.style.overflow = '';
    }
  };

  /**
   * Toast Notification Dispatcher
   */
  const showToast = (title, message, type = 'info') => {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'fa-circle-info';
    if (type === 'success') iconClass = 'fa-circle-check';
    if (type === 'error') iconClass = 'fa-circle-exclamation';
    if (type === 'warning') iconClass = 'fa-triangle-exclamation';

    toast.innerHTML = `
      <i class="fa-solid ${iconClass} toast-icon"></i>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message}</div>
      </div>
      <button class="modal-close" style="font-size: 0.9rem;" onclick="this.parentElement.remove()" aria-label="Close notification">
        <i class="fa-solid fa-xmark"></i>
      </button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  };

  /**
   * Tabs Switcher
   */
  const initTabs = () => {
    document.querySelectorAll('.nav-tab-item').forEach(tab => {
      tab.addEventListener('click', () => {
        const parent = tab.closest('.nav-tabs');
        if (!parent) return;

        parent.querySelectorAll('.nav-tab-item').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        const targetPaneId = tab.getAttribute('data-tab-target');
        if (targetPaneId) {
          const tabContainer = parent.parentElement;
          tabContainer.querySelectorAll('.tab-pane').forEach(p => p.classList.add('d-none'));
          const targetPane = document.getElementById(targetPaneId);
          if (targetPane) targetPane.classList.remove('d-none');
        }
      });
    });
  };

  /**
   * Global Shortcut (Ctrl+K to search)
   */
  const initQuickSearch = () => {
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.header-search input') || document.getElementById('globalSearchInput');
        if (searchInput) searchInput.focus();
      }
    });
  };

  /**
   * REQUIREMENT 4: Interactive Blood Compatibility Visualizer
   * Vanilla JS clinical lookup table with teal donate-to & crimson receive-from highlights.
   */
  const BLOOD_COMPATIBILITY_DATA = {
    'O-': {
      title: 'O Negative (Universal Red Cell Donor)',
      summary: 'O- can donate red blood cells to all 8 blood groups (Universal Donor), but can only safely receive red blood cells from O-.',
      facts: 'O- red blood cells lack A, B, and Rh antigens. It is the gold standard for trauma emergencies before laboratory cross-matching is complete.',
      canReceiveFrom: ['O-'],
      canDonateTo: ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+']
    },
    'O+': {
      title: 'O Positive (High Demand Population Group)',
      summary: 'O+ can donate red blood cells to all Rh-positive groups (O+, A+, B+, AB+) and can receive red cells from O+ and O-.',
      facts: 'O+ is one of the most common blood types, making it vital for maintaining healthy regional hospital inventory stocks.',
      canReceiveFrom: ['O+', 'O-'],
      canDonateTo: ['O+', 'A+', 'B+', 'AB+']
    },
    'A-': {
      title: 'A Negative (Universal A Donor)',
      summary: 'A- can donate red blood cells to A-, A+, AB-, and AB+, and can safely receive red blood cells from A- and O-.',
      facts: 'A- red blood cells carry the A antigen without the Rh factor, compatible with all A and AB recipients.',
      canReceiveFrom: ['A-', 'O-'],
      canDonateTo: ['A-', 'A+', 'AB-', 'AB+']
    },
    'A+': {
      title: 'A Positive (Major Group)',
      summary: 'A+ can donate red blood cells to A+ and AB+, and can safely receive red cells from A+, A-, O+, and O-.',
      facts: 'A+ is widely distributed. Platelets and whole blood from A+ donors are in continuous clinical demand.',
      canReceiveFrom: ['A+', 'A-', 'O+', 'O-'],
      canDonateTo: ['A+', 'AB+']
    },
    'B-': {
      title: 'B Negative (Rare Blood Group)',
      summary: 'B- can donate red blood cells to B-, B+, AB-, and AB+, and can receive red blood cells from B- and O-.',
      facts: 'B- is a rare blood type in most populations. Maintaining active registered B- donors is critical for regional resilience.',
      canReceiveFrom: ['B-', 'O-'],
      canDonateTo: ['B-', 'B+', 'AB-', 'AB+']
    },
    'B+': {
      title: 'B Positive (Critical Regional Supply)',
      summary: 'B+ can donate red blood cells to B+ and AB+, and can safely receive red blood cells from B+, B-, O+, and O-.',
      facts: 'B+ individuals can provide life-saving whole blood and platelet transfusions across many clinical wards.',
      canReceiveFrom: ['B+', 'B-', 'O+', 'O-'],
      canDonateTo: ['B+', 'AB+']
    },
    'AB-': {
      title: 'AB Negative (Rarest Blood Group)',
      summary: 'AB- can donate red blood cells to AB- and AB+, and can receive red blood cells from all Rh-negative types (AB-, A-, B-, O-).',
      facts: 'AB- is one of the rarest blood groups on earth, making rapid requirement-based matching essential.',
      canReceiveFrom: ['AB-', 'A-', 'B-', 'O-'],
      canDonateTo: ['AB-', 'AB+']
    },
    'AB+': {
      title: 'AB Positive (Universal Red Cell Recipient)',
      summary: 'AB+ is the Universal Recipient and can safely receive red blood cells from all 8 blood groups, but can only donate red cells to AB+.',
      facts: 'AB+ patients carry both A and B antigens and Rh factor, meaning their plasma contains no antibodies against donor red cells.',
      canReceiveFrom: ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'],
      canDonateTo: ['AB+']
    }
  };

  const ALL_BLOOD_GROUPS = ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'];

  const initCompatibilityVisualizer = () => {
    const selectorButtons = document.querySelectorAll('.compat-selector-btn');
    if (!selectorButtons.length) return;

    selectorButtons.forEach(btn => {
      // Click handler
      btn.addEventListener('click', () => {
        const group = btn.getAttribute('data-group');
        selectBloodGroupVisualizer(group);
      });

      // Keyboard Accessibility (Enter or Space) (Requirement 7)
      btn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          const group = btn.getAttribute('data-group');
          selectBloodGroupVisualizer(group);
        }
      });
    });

    // Initialize with default O-
    selectBloodGroupVisualizer('O-');
  };

  const selectBloodGroupVisualizer = (selectedGroup) => {
    const data = BLOOD_COMPATIBILITY_DATA[selectedGroup];
    if (!data) return;

    // Update active state and aria-pressed on selector buttons
    document.querySelectorAll('.compat-selector-btn').forEach(btn => {
      const isSelected = btn.getAttribute('data-group') === selectedGroup;
      btn.classList.toggle('active', isSelected);
      btn.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
    });

    // Update selected title badge
    const activeLabelEl = document.getElementById('compatSelectedGroupLabel');
    if (activeLabelEl) {
      activeLabelEl.textContent = `Selected Group: ${selectedGroup}`;
    }

    // Render "Can Receive From" (Crimson Outline & Glow for Inbound Transfusion)
    const receiveGrid = document.getElementById('compatReceiveGrid');
    const receiveBadge = document.getElementById('compatReceiveCountBadge');
    if (receiveGrid) {
      const receiveCount = data.canReceiveFrom.length;
      if (receiveBadge) {
        receiveBadge.textContent = `${receiveCount} of 8 Compatible`;
      }

      receiveGrid.innerHTML = ALL_BLOOD_GROUPS.map(bg => {
        const isComp = data.canReceiveFrom.includes(bg);
        return `
          <div class="compat-tile ${isComp ? 'is-compatible is-receive-target' : 'is-incompatible'}" role="status" aria-label="${bg}: ${isComp ? 'Can receive from this group' : 'Incompatible donor'}">
            <span class="tile-blood">${bg}</span>
            <span class="tile-status">
              ${isComp ? '<i class="fa-solid fa-circle-check"></i> Compatible Donor' : '<i class="fa-solid fa-circle-xmark"></i> Incompatible'}
            </span>
          </div>
        `;
      }).join('');
    }

    // Render "Can Donate To" (Teal Outline & Glow for Outbound Donation)
    const donateGrid = document.getElementById('compatDonateGrid');
    const donateBadge = document.getElementById('compatDonateCountBadge');
    if (donateGrid) {
      const donateCount = data.canDonateTo.length;
      if (donateBadge) {
        donateBadge.textContent = `${donateCount} of 8 Compatible`;
      }

      donateGrid.innerHTML = ALL_BLOOD_GROUPS.map(bg => {
        const isComp = data.canDonateTo.includes(bg);
        return `
          <div class="compat-tile ${isComp ? 'is-compatible is-donate-target' : 'is-incompatible'}" role="status" aria-label="${bg}: ${isComp ? 'Can safely donate to this group' : 'Incompatible recipient'}">
            <span class="tile-blood">${bg}</span>
            <span class="tile-status">
              ${isComp ? '<i class="fa-solid fa-circle-arrow-up"></i> Can Donate To' : '<i class="fa-solid fa-circle-xmark"></i> Incompatible'}
            </span>
          </div>
        `;
      }).join('');
    }

    // Update One-line summary and Clinical Details Box (Requirement 4)
    const summaryEl = document.getElementById('compatSelectionSummary');
    const titleEl = document.getElementById('compatNoteTitle');
    const textEl = document.getElementById('compatNoteText');
    if (summaryEl) summaryEl.textContent = data.summary;
    if (titleEl) titleEl.textContent = data.title;
    if (textEl) textEl.textContent = data.facts;
  };

  /**
   * REQUIREMENT 2: Animated Statistics with IntersectionObserver (~800ms)
   */
  const initAnimatedStats = () => {
    const counterElements = document.querySelectorAll('[data-counter]');
    if (!counterElements.length) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReducedMotion) {
      counterElements.forEach(el => {
        const target = parseFloat(el.getAttribute('data-counter'));
        const suffix = el.getAttribute('data-suffix') || '';
        const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
        el.textContent = formatCounterValue(target, decimals, suffix);
      });
      return;
    }

    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          obs.unobserve(entry.target);
          animateCounterElement(entry.target);
        }
      });
    }, { threshold: 0.3 });

    counterElements.forEach(el => observer.observe(el));
  };

  const formatCounterValue = (val, decimals, suffix) => {
    if (decimals > 0) {
      return val.toFixed(decimals) + suffix;
    }
    return Math.round(val).toLocaleString() + suffix;
  };

  const animateCounterElement = (el) => {
    const target = parseFloat(el.getAttribute('data-counter'));
    const suffix = el.getAttribute('data-suffix') || '';
    const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
    const duration = 800; // ~800ms
    const startTime = performance.now();

    const updateCount = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const currentVal = target * easeOut;

      el.textContent = formatCounterValue(currentVal, decimals, suffix);

      if (progress < 1) {
        requestAnimationFrame(updateCount);
      } else {
        el.textContent = formatCounterValue(target, decimals, suffix);
      }
    };

    requestAnimationFrame(updateCount);
  };

  return {
    openModal,
    closeModal,
    showToast,
    selectBloodGroupVisualizer
  };
})();
