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
      if (titleEl) titleEl.textContent = 'Portal Sign In';
      if (subtitleEl) subtitleEl.textContent = 'Access your HemoNexus clinical network profile';
      if (contextText) {
        contextText.innerHTML = '<strong>Volunteer Donor Portal:</strong> Check donation cooldown, review emergency broadcasts, and manage your availability status.';
      }
      const previewEl = document.getElementById('rolePreviewText');
      if (previewEl) previewEl.textContent = 'View donation cooldown, availability status, and nearby blood requests.';
      if (regLink) {
        regLink.href = '/register?role=donor';
        regLink.textContent = 'Register as a Volunteer Donor';
      }
      if (donorFields) donorFields.classList.remove('d-none');
      if (patientFields) patientFields.classList.add('d-none');
    } else {
      if (titleEl) titleEl.textContent = 'Portal Sign In';
      if (subtitleEl) subtitleEl.textContent = 'Access your HemoNexus clinical network profile';
      if (contextText) {
        contextText.innerHTML = '<strong>Emergency Blood Seeker Portal:</strong> Broadcast critical blood requirements directly to compatible nearby donors.';
      }
      const previewEl = document.getElementById('rolePreviewText');
      if (previewEl) previewEl.textContent = 'Find compatible donors and create blood requests based on your requirements.';
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

  const handleLoginSubmit = async (event) => {
    if (event) event.preventDefault();
    const emailInput = document.getElementById('loginEmail');
    const passInput = document.getElementById('loginPassword');
    const email = emailInput ? emailInput.value.trim().toLowerCase() : '';
    const password = passInput ? passInput.value : '';

    if (!email || !password) {
      HemoUI.showToast('Validation Error', 'Email and password are required.', 'warning');
      return;
    }

    const btn = document.getElementById('loginSubmitBtn');
    const origHtml = btn ? btn.innerHTML : 'Sign In to Portal';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <span class="heartbeat-spinner me-2"><i class="fa-solid fa-heart-pulse"></i></span>
        <span>Signing in...</span>
      `;
    }

    try {
      const res = await HemoAPI.login(email, password);
      if (res && res.success) {
        HemoUI.showToast('Welcome Back', res.message || 'Signed in successfully.', 'success');
        const urlParams = new URLSearchParams(window.location.search);
        const nextUrl = urlParams.get('next') || '/dashboard';
        window.location.href = nextUrl;
      } else {
        throw new Error(res.error || 'Login failed.');
      }
    } catch (err) {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = origHtml;
      }
      let errBox = document.getElementById('loginAlertBox');
      if (!errBox) {
        errBox = document.createElement('div');
        errBox.id = 'loginAlertBox';
        errBox.className = 'alert alert-danger d-flex align-items-center mb-3 py-2 px-3 rounded-3';
        const formEl = document.getElementById('authLoginForm');
        if (formEl) formEl.prepend(errBox);
      }
      errBox.innerHTML = `
        <i class="fa-solid fa-circle-exclamation me-2 fs-5 flex-shrink-0 text-danger"></i>
        <div><strong>Authentication Failed:</strong> ${err.message || 'Invalid email or password.'}</div>
      `;
      HemoUI.showToast('Login Failed', err.message || 'Invalid email or password.', 'error');
    }
  };

  const handleRegSubmit = (event) => {
    const form = document.getElementById('authRegisterForm');
    if (form && !form.checkValidity()) return;

    const btn = document.getElementById('registerSubmitBtn');
    if (btn) {
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
    initScrollReveals();
    initLiveNetworkTelemetry();
  });

  /**
   * REQUIREMENT 10: Scroll-Triggered Staggered Animations
   */
  const initScrollReveals = () => {
    const revealElements = document.querySelectorAll('.reveal-on-scroll');
    if (!revealElements.length) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      revealElements.forEach(el => el.classList.add('is-revealed'));
      return;
    }

    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          obs.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.12,
      rootMargin: '0px 0px -40px 0px'
    });

    revealElements.forEach(el => observer.observe(el));
  };

  /**
   * REQUIREMENT 3: Live Donor Network Pipeline Telemetry
   * Concept: DONOR → MATCHING ENGINE → HOSPITAL
   */
  const initLiveNetworkTelemetry = () => {
    const donorText = document.getElementById('networkDonorText');
    const engineText = document.getElementById('networkEngineText');
    const hospitalText = document.getElementById('networkHospitalText');
    if (!donorText || !engineText || !hospitalText) return;

    const streamCases = [
      { donor: 'Rahul S. (O- Universal)', engine: 'ABO/Rh Validated (100% Match)', hospital: 'Lilavati Trauma Bay #3' },
      { donor: 'Priya M. (A+ Platelets)', engine: 'Proximity Heuristic (2.4 km, 96%)', hospital: 'Hinduja ICU Bed #12' },
      { donor: 'Vikram N. (B+ Whole Blood)', engine: 'Emergency Cooldown Clear (94%)', hospital: 'Nanavati Emergency Intake' },
      { donor: 'Ananya D. (AB- Rare Donor)', engine: 'Cross-Match Validated (99%)', hospital: 'Tata Memorial Oncology' }
    ];

    let currentCaseIdx = 0;
    setInterval(() => {
      currentCaseIdx = (currentCaseIdx + 1) % streamCases.length;
      const c = streamCases[currentCaseIdx];

      [donorText, engineText, hospitalText].forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(-4px)';
        el.style.transition = 'all 0.25s ease';
      });

      setTimeout(() => {
        donorText.textContent = c.donor;
        engineText.textContent = c.engine;
        hospitalText.textContent = c.hospital;

        [donorText, engineText, hospitalText].forEach(el => {
          el.style.opacity = '1';
          el.style.transform = 'translateY(0)';
        });
      }, 250);
    }, 4500);
  };

  /**
   * REQUIREMENT 5: Search Compatible Donors Animation
   * Professional multi-step ECG and heuristic matching sequence
   */
  const triggerMatchingSearchAnimation = (bloodGroup = 'O-', component = 'Whole Blood', cityOrUrl = null) => {
    let target = `/match?group=${encodeURIComponent(bloodGroup)}&component=${encodeURIComponent(component)}`;
    if (cityOrUrl && cityOrUrl.startsWith('/')) {
      target = cityOrUrl;
    } else if (cityOrUrl) {
      target += `&city=${encodeURIComponent(cityOrUrl)}`;
    }
    window.location.href = target;
  };

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
      const btnGroup = btn.getAttribute('data-group');
      const isSelected = btnGroup === selectedGroup;
      const isCompatibleRecipient = data.canDonateTo.includes(btnGroup);

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
   * REQUIREMENT 6: Animated Statistics with IntersectionObserver (~800ms)
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
    }, { threshold: 0.25 });

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
    const duration = 850; // ~850ms
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
    selectBloodGroupVisualizer,
    triggerMatchingSearchAnimation
  };
})();

/**
 * HemoNexus Unified Backend REST API Client
 * Connects frontend flows to real Flask endpoints with credentials: 'same-origin'
 */
const HemoAPI = (() => {
  const apiFetch = async (url, options = {}) => {
    const config = {
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        ...(options.headers || {})
      },
      ...options
    };

    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json';
      config.body = JSON.stringify(options.body);
    }

    try {
      const res = await fetch(url, config);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const errorMsg = data.error || data.message || `Request failed with status ${res.status}`;
        const error = new Error(errorMsg);
        error.status = res.status;
        error.data = data;
        throw error;
      }
      return data;
    } catch (err) {
      console.error(`[HemoAPI] Error requesting ${url}:`, err);
      throw err;
    }
  };

  return {
    // 0. Authentication
    login: (email, password) => apiFetch('/api/login', { method: 'POST', body: { email, password } }),
    logout: () => apiFetch('/api/logout', { method: 'POST' }),

    // 1. Patient Blood Requests
    createBloodRequest: (payload) => apiFetch('/api/patient/blood-requests', { method: 'POST', body: payload }),
    getPatientRequests: () => apiFetch('/api/patient/blood-requests', { method: 'GET' }),
    getRequestDetails: (requestId) => apiFetch(`/api/patient/blood-requests/${requestId}`, { method: 'GET' }),
    cancelBloodRequest: (requestId) => apiFetch(`/api/patient/blood-requests/${requestId}/cancel`, { method: 'POST' }),
    fulfillBloodRequest: (requestId) => apiFetch(`/api/patient/blood-requests/${requestId}/fulfill`, { method: 'POST' }),

    // 2. Smart Matching Candidates (Real Backend Heuristic Engine)
    getRequestMatches: (requestId) => apiFetch(`/api/patient/blood-requests/${requestId}/matches`, { method: 'GET' }),

    // 3. Donor Dispatch / Send Request (Priority Endpoint - uses user_id)
    sendDonorRequest: (requestId, donorUserId) => apiFetch(`/api/patient/blood-requests/${requestId}/send-request`, {
      method: 'POST',
      body: { donor_id: donorUserId }
    }),

    // 4. Donor Inbox & Action Responses
    getDonorRequests: () => apiFetch('/api/donor/requests', { method: 'GET' }),
    acceptDonorRequest: (responseId, message) => apiFetch(`/api/donor/requests/${responseId}/accept`, {
      method: 'POST',
      body: { message }
    }),
    rejectDonorRequest: (responseId, message) => apiFetch(`/api/donor/requests/${responseId}/reject`, {
      method: 'POST',
      body: { message }
    }),

    // 5. User / Identity & Directory
    getCurrentUser: () => apiFetch('/api/me', { method: 'GET' }),
    getPatientProfile: () => apiFetch('/api/patient/profile', { method: 'GET' }),
    getDonorProfile: () => apiFetch('/api/donor/profile', { method: 'GET' }),
    getDonors: () => apiFetch('/api/donors', { method: 'GET' }),
    getActivities: () => apiFetch('/api/activities', { method: 'GET' }),
    getDispatches: () => apiFetch('/api/dispatches', { method: 'GET' }),

    // 6. Admin Endpoints
    getAdminStats: () => apiFetch('/api/admin/stats', { method: 'GET' }),
    getAdminRequests: () => apiFetch('/api/admin/blood-requests', { method: 'GET' }),
    getAdminResponses: () => apiFetch('/api/admin/responses', { method: 'GET' })
  };
})();
