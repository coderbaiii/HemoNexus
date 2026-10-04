/**
 * HemoNexus Code-Red Emergency Broadcast Engine
 * Integrates real-time SOS blood request registration/reuse, searchable hospital auto-registration,
 * heuristic matching, direct donor dispatching, grouped multi-request response merging, and live polling.
 */

// City Coordinate Lookup Fallback for Geographic Telemetry
const CITY_COORDINATES = {
  'kolkata': { lat: 22.5726, lon: 88.3639 },
  'mumbai': { lat: 19.0760, lon: 72.8777 },
  'delhi': { lat: 28.7041, lon: 77.1025 },
  'bengaluru': { lat: 12.9716, lon: 77.5946 },
  'bangalore': { lat: 12.9716, lon: 77.5946 },
  'hyderabad': { lat: 17.3850, lon: 78.4867 },
  'chennai': { lat: 13.0827, lon: 80.2707 },
  'pune': { lat: 18.5204, lon: 73.8567 }
};

let broadcastInterval = null;
let pollInterval = null;
let secondsRemaining = 600; // 10 minutes emergency window
let activeEmergencyRequestId = null;
let broadcastSubmitted = false;
let hospitalSearchTimer = null;

document.addEventListener('DOMContentLoaded', () => {
  const broadcastBtn = document.getElementById('btnTriggerBroadcast');
  const bloodGroupSelect = document.getElementById('emergencyBloodGroup');
  const componentSelect = document.getElementById('emergencyComponent');
  const hospitalInput = document.getElementById('emergencyHospitalName');
  const citySelect = document.getElementById('emergencyCityLocation');

  // Input listeners for Transmit validation (Requirement 3: Transmit disabled until blood group, component and hospital filled)
  const validateForm = () => {
    const bg = bloodGroupSelect?.value || '';
    const comp = componentSelect?.value || '';
    const hosp = hospitalInput?.value?.trim() || '';
    if (broadcastBtn) {
      broadcastBtn.disabled = !(bg && comp && hosp);
    }
  };

  if (bloodGroupSelect) bloodGroupSelect.addEventListener('change', () => { validateForm(); if (broadcastSubmitted) fetchAndRenderMergedDispatches(); });
  if (componentSelect) componentSelect.addEventListener('change', validateForm);
  if (hospitalInput) hospitalInput.addEventListener('input', () => { validateForm(); handleHospitalSearch(hospitalInput.value); });
  if (citySelect) citySelect.addEventListener('change', validateForm);

  if (broadcastBtn) {
    broadcastBtn.addEventListener('click', () => {
      startEmergencyBroadcast();
    });
  }

  // Setup searchable hospital autocomplete (Requirement 4)
  initHospitalAutocomplete();

  // "Alerted Donors" starts empty (Requirement 3)
  const responseFeed = document.getElementById('emergencyResponseList');
  if (responseFeed) {
    responseFeed.innerHTML = `
      <div class="empty-state py-5 text-center">
        <div class="empty-state-icon mb-2"><i class="fa-solid fa-tower-broadcast text-muted fa-2x"></i></div>
        <h5 class="fw-bold text-slate-900">Awaiting Emergency Broadcast</h5>
        <p class="text-xs text-muted">Fill the requirement parameters and click "Transmit Code-Red Broadcast" to blast instant alerts to verified donors.</p>
      </div>
    `;
  }

  // Periodic polling only starts after broadcast or when viewing existing active dispatches
  clearInterval(pollInterval);
  pollInterval = setInterval(() => {
    if (broadcastSubmitted) {
      fetchAndRenderMergedDispatches();
    }
  }, 10000);
});

/**
 * Requirement 4: Searchable Destination Hospital Autocomplete with "Add '<name>' as new hospital"
 */
const initHospitalAutocomplete = () => {
  const input = document.getElementById('emergencyHospitalName');
  const dropdown = document.getElementById('emergencyHospitalDropdown');
  if (!input || !dropdown) return;

  input.addEventListener('focus', () => {
    handleHospitalSearch(input.value);
  });

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add('d-none');
    }
  });
};

const handleHospitalSearch = (query) => {
  const dropdown = document.getElementById('emergencyHospitalDropdown');
  const input = document.getElementById('emergencyHospitalName');
  const citySelect = document.getElementById('emergencyCityLocation');
  if (!dropdown || !input) return;

  clearTimeout(hospitalSearchTimer);
  hospitalSearchTimer = setTimeout(async () => {
    const q = (query || '').trim();
    try {
      const res = await HemoAPI.getHospitals(q).catch(() => null);
      const hospitals = (res && res.success && Array.isArray(res.hospitals)) ? res.hospitals : [];

      let html = '';
      if (hospitals.length > 0) {
        html += hospitals.map(h => `
          <div class="hospital-autocomplete-item p-2 border-bottom cursor-pointer hover-bg-light text-start" data-name="${escapeHtml(h.name)}" data-city="${escapeHtml(h.city || '')}">
            <div class="fw-semibold text-slate-900 text-xs"><i class="fa-solid fa-hospital text-primary me-1"></i> ${escapeHtml(h.name)}</div>
            ${h.city ? `<div class="text-muted" style="font-size: 0.7rem;"><i class="fa-solid fa-location-dot me-1"></i> ${escapeHtml(h.city)}</div>` : ''}
          </div>
        `).join('');
      }

      if (q.length > 1) {
        const exactMatch = hospitals.some(h => h.name.toLowerCase() === q.toLowerCase());
        if (!exactMatch) {
          html += `
            <div class="hospital-autocomplete-item p-2 cursor-pointer bg-primary-50 text-primary fw-semibold text-xs text-start" data-add-new="true" data-name="${escapeHtml(q)}">
              <i class="fa-solid fa-plus-circle me-1"></i> Add "<strong>${escapeHtml(q)}</strong>" as new hospital
            </div>
          `;
        }
      }

      if (html) {
        dropdown.innerHTML = html;
        dropdown.classList.remove('d-none');

        // Attach item click handlers
        dropdown.querySelectorAll('.hospital-autocomplete-item').forEach(item => {
          item.addEventListener('click', async () => {
            const name = item.getAttribute('data-name');
            const isAdd = item.getAttribute('data-add-new') === 'true';
            const city = item.getAttribute('data-city') || citySelect?.value || 'Kolkata';

            if (isAdd) {
              try {
                await HemoAPI.createHospital(name, city);
              } catch (err) {
                console.warn('Could not auto-register hospital:', err);
              }
            } else if (item.getAttribute('data-city') && citySelect) {
              citySelect.value = item.getAttribute('data-city');
            }

            input.value = name;
            dropdown.classList.add('d-none');
            const broadcastBtn = document.getElementById('btnTriggerBroadcast');
            const bg = document.getElementById('emergencyBloodGroup')?.value || '';
            const comp = document.getElementById('emergencyComponent')?.value || '';
            if (broadcastBtn) broadcastBtn.disabled = !(bg && comp && name);
          });
        });
      } else {
        dropdown.classList.add('d-none');
      }
    } catch (e) {
      console.warn('Hospital search error:', e);
    }
  }, 200);
};

const escapeHtml = (str) => {
  if (!str) return '';
  return str.replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }[m]));
};

/**
 * Resolves GPS coordinates for blood request creation.
 */
const resolveCoordinates = async (locationStr) => {
  try {
    const profRes = await HemoAPI.getPatientProfile().catch(() => null);
    if (profRes && profRes.success && profRes.profile) {
      if (profRes.profile.latitude != null && profRes.profile.longitude != null) {
        const lat = parseFloat(profRes.profile.latitude);
        const lon = parseFloat(profRes.profile.longitude);
        if (!isNaN(lat) && !isNaN(lon)) {
          return { lat, lon };
        }
      }
    }
  } catch (e) {
    console.warn('Could not read patient profile coordinates:', e);
  }

  const locLower = (locationStr || '').toLowerCase();
  for (const [city, coords] of Object.entries(CITY_COORDINATES)) {
    if (locLower.includes(city)) {
      return coords;
    }
  }

  return { lat: 22.5726, lon: 88.3639 };
};

/**
 * Requirement 1: Reuse existing OPEN/MATCHING request for same patient and blood group. Create new only if none exists.
 * Transmit: POST /api/patient/blood-requests, GET /matches, POST /send-request for each match using match.user_id.
 */
const startEmergencyBroadcast = async () => {
  const broadcastBtn = document.getElementById('btnTriggerBroadcast');
  const bloodGroup = document.getElementById('emergencyBloodGroup')?.value || '';
  const component = document.getElementById('emergencyComponent')?.value || '';
  const hospitalName = document.getElementById('emergencyHospitalName')?.value?.trim() || '';
  const cityVal = document.getElementById('emergencyCityLocation')?.value?.trim() || 'Kolkata';
  const radius = parseFloat(document.getElementById('emergencyRadius')?.value) || 10.0;

  if (!bloodGroup || !component || !hospitalName) {
    HemoUI.showToast('Incomplete Parameters', 'Please fill Critical Blood Group, Component, and Destination Hospital.', 'warning');
    return;
  }

  const broadcastStatus = document.getElementById('broadcastActiveState');
  const broadcastTrigger = document.getElementById('broadcastTriggerCard');
  const originalBtnHtml = broadcastBtn ? broadcastBtn.innerHTML : '<i class="fa-solid fa-satellite-dish"></i> Transmit Code-Red Broadcast Now';

  // 1. Role verification
  const me = await HemoAPI.getCurrentUser().catch(() => null);
  const user = me && me.user ? me.user : null;

  if (!user) {
    HemoUI.showToast('Login Required', 'Please sign in to send emergency broadcasts.', 'warning');
    setTimeout(() => { window.location.href = '/login?next=/emergency'; }, 1500);
    return;
  }

  if (broadcastBtn) {
    broadcastBtn.disabled = true;
    broadcastBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Initializing Code-Red Network...';
  }

  try {
    // 2. Check for existing OPEN or MATCHING request for this blood group (Requirement 1 & 7)
    const reqListRes = await HemoAPI.getPatientRequests().catch(() => null);
    const allRequests = (reqListRes && reqListRes.success && Array.isArray(reqListRes.requests)) ? reqListRes.requests : [];
    const existingReq = allRequests.find(r => {
      const st = (r.request_status || r.status || '').toUpperCase();
      const bg = (r.required_blood_group || r.blood_group || '').toUpperCase();
      return (st === 'OPEN' || st === 'MATCHING') && bg === bloodGroup.toUpperCase();
    });

    if (existingReq) {
      activeEmergencyRequestId = existingReq.id;
    } else {
      const { lat, lon } = await resolveCoordinates(cityVal + ' ' + hospitalName);

      // Create new hospital entry if not exists
      try {
        await HemoAPI.createHospital(hospitalName, cityVal);
      } catch (e) {}

      const reqPayload = {
        required_blood_group: bloodGroup,
        hospital_name: hospitalName,
        location: cityVal,
        latitude: lat,
        longitude: lon,
        urgency: 'CRITICAL',
        required_units: 3,
        preferred_max_distance: radius
      };

      const createRes = await HemoAPI.createBloodRequest(reqPayload);
      if (!createRes || !createRes.success || !createRes.request) {
        throw new Error(createRes?.error || 'Failed to initialize emergency blood request on server.');
      }

      activeEmergencyRequestId = createRes.request.id;
    }

    broadcastSubmitted = true;

    if (broadcastTrigger) broadcastTrigger.classList.add('d-none');
    if (broadcastStatus) broadcastStatus.classList.remove('d-none');

    HemoUI.showToast(
      '🚨 Code-Red Broadcast Transmitted',
      `Emergency requirement #${activeEmergencyRequestId} for ${bloodGroup} (${component}) broadcast across donor network.`,
      'error'
    );

    // Start 10-min countdown timer
    startCountdownTimer();

    // 3. GET /api/patient/blood-requests/<id>/matches
    let matches = [];
    try {
      const matchRes = await HemoAPI.getRequestMatches(activeEmergencyRequestId);
      if (matchRes && matchRes.success && Array.isArray(matchRes.matches)) {
        matches = matchRes.matches;
      }
    } catch (mErr) {
      console.warn('Could not fetch matches:', mErr);
    }

    // 4. POST /send-request for each match using match.user_id
    if (matches.length > 0) {
      await Promise.allSettled(matches.map(async (match) => {
        const donorUserId = match.user_id || match.donor_id || match.id;
        try {
          await HemoAPI.sendDonorRequest(activeEmergencyRequestId, donorUserId);
        } catch (sendErr) {
          if (sendErr && sendErr.status !== 409) {
            console.warn(`Dispatch error for donor ${donorUserId}:`, sendErr);
          }
        }
      }));
    }

    // 5. Render grouped dispatches (Requirement 2 & 3)
    const emptyReason = matches.length === 0
      ? `No compatible verified donors found within ${radius} km radius for ${bloodGroup}. Try expanding search radius.`
      : null;
    await fetchAndRenderMergedDispatches(emptyReason);

  } catch (err) {
    console.error('Error during emergency broadcast:', err);
    if (err && err.status === 401) {
      HemoUI.showToast('Login Required', 'Please sign in as a patient to send emergency broadcasts.', 'warning');
      setTimeout(() => { window.location.href = '/login?next=/emergency'; }, 1500);
      return;
    }
    if (broadcastBtn) {
      broadcastBtn.disabled = false;
      broadcastBtn.innerHTML = originalBtnHtml;
    }
    HemoUI.showToast('Broadcast Failed', err.message || 'Could not initiate emergency broadcast.', 'error');
  }
};

/**
 * Requirement 8: Single unified time format ("10h ago")
 */
const formatTimeDisplay = (isoString) => {
  if (window.HemoUI && typeof window.HemoUI.formatTimeAgo === 'function') {
    return window.HemoUI.formatTimeAgo(isoString);
  }
  if (!isoString) return 'Just now';
  try {
    const d = new Date(isoString).getTime();
    if (isNaN(d)) return 'Just now';
    const diffSec = Math.max(0, Math.floor((Date.now() - d) / 1000));
    if (diffSec < 60) return 'Just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDay = Math.floor(diffHr / 24);
    return `${diffDay}d ago`;
  } catch (e) {
    return 'Just now';
  }
};

/**
 * Requirement 2 & 3:
 * Show all dispatches for the selected blood group from any request (including Matcher ones),
 * grouped by donor, refreshed every 10s.
 */
const fetchAndRenderMergedDispatches = async (customEmptyReason = null) => {
  const bloodGroup = document.getElementById('emergencyBloodGroup')?.value || 'O-';
  const responseFeed = document.getElementById('emergencyResponseList');
  const alertedCountEl = document.getElementById('liveAlertedCount');
  const responseCountEl = document.getElementById('liveResponseCount');
  const streamBadge = document.getElementById('streamAlertedBadge');

  try {
    const me = await HemoAPI.getCurrentUser().catch(() => null);
    const user = me && me.user ? me.user : null;

    if (!user) {
      if (responseFeed) {
        responseFeed.innerHTML = `
          <div class="empty-state py-4 text-center">
            <div class="empty-state-icon mb-2"><i class="fa-solid fa-user-lock text-muted fa-2x"></i></div>
            <h5 class="fw-bold text-slate-900">Sign In Required</h5>
            <p class="text-xs text-muted">Please sign in as a patient or hospital to view active emergency dispatches.</p>
            <a href="/login?next=/emergency" class="btn btn-outline-primary btn-sm mt-2">
              <i class="fa-solid fa-right-to-bracket me-1"></i> Sign In
            </a>
          </div>
        `;
      }
      if (alertedCountEl) alertedCountEl.textContent = '0 Donors';
      if (responseCountEl) responseCountEl.textContent = '0';
      if (streamBadge) streamBadge.textContent = '0 Alerted';
      return;
    }

    // 1. GET /api/patient/blood-requests
    const reqListRes = await HemoAPI.getPatientRequests().catch(() => null);
    const allRequests = (reqListRes && reqListRes.success && Array.isArray(reqListRes.requests)) ? reqListRes.requests : [];

    // 2. Filter requests with matching blood group
    const targetRequests = allRequests.filter(r => {
      const bg = (r.required_blood_group || r.blood_group || '').toUpperCase();
      return bg === bloodGroup.toUpperCase();
    });

    if (targetRequests.length === 0) {
      if (alertedCountEl) alertedCountEl.textContent = '0 Donors';
      if (responseCountEl) responseCountEl.textContent = '0';
      if (streamBadge) streamBadge.textContent = '0 Alerted';

      if (responseFeed) {
        const reasonText = customEmptyReason || `No blood requests found for blood group ${bloodGroup}.`;
        responseFeed.innerHTML = `
          <div class="empty-state py-4 text-center">
            <div class="empty-state-icon mb-2"><i class="fa-solid fa-circle-exclamation text-warning fa-2x"></i></div>
            <h5 class="fw-bold text-slate-900">No Active Dispatches</h5>
            <p class="text-xs text-muted">${reasonText}</p>
            <p class="text-xs text-slate-400 mt-1">Transmit a Code-Red Broadcast above or create a request in the Requirement Matcher.</p>
          </div>
        `;
      }
      return;
    }

    // 3. GET /api/patient/blood-requests/<id> for each matching request
    const detailsResults = await Promise.all(
      targetRequests.map(req => HemoAPI.getRequestDetails(req.id).catch(() => null))
    );

    // 4. Group all responses by donor
    const donorsMap = new Map();

    detailsResults.forEach(detail => {
      if (!detail || !detail.success) return;
      const reqInfo = detail.request || {};
      const responses = Array.isArray(detail.responses) ? detail.responses : [];

      responses.forEach(resp => {
        const donorKey = resp.donor_id || resp.user_id || resp.donor_name;
        const respTime = resp.response_time || resp.created_at;
        const status = (resp.status || 'PENDING').toUpperCase();
        const reqId = resp.blood_request_id || reqInfo.id;

        if (!donorsMap.has(donorKey)) {
          donorsMap.set(donorKey, {
            donor_id: resp.donor_id || resp.user_id,
            donor_name: resp.donor_name || 'Verified Donor',
            donor_blood_group: resp.donor_blood_group || reqInfo.required_blood_group || bloodGroup,
            donor_phone: resp.donor_phone || '',
            status: status,
            latest_time: respTime,
            request_ids: reqId ? [reqId] : [],
            hospital_name: reqInfo.hospital_name || 'Destination Hospital'
          });
        } else {
          const existing = donorsMap.get(donorKey);
          if (reqId && !existing.request_ids.includes(reqId)) {
            existing.request_ids.push(reqId);
          }
          if (status === 'ACCEPTED') {
            existing.status = 'ACCEPTED';
            existing.latest_time = respTime;
          } else if (existing.status !== 'ACCEPTED') {
            if (new Date(respTime) > new Date(existing.latest_time)) {
              existing.status = status;
              existing.latest_time = respTime;
            }
          }
        }
      });
    });

    const groupedDonors = Array.from(donorsMap.values());

    // Sort by latest activity descending
    groupedDonors.sort((a, b) => {
      const timeA = new Date(a.latest_time || 0).getTime();
      const timeB = new Date(b.latest_time || 0).getTime();
      return timeB - timeA;
    });

    const donorsAlertedCount = groupedDonors.length;
    const acceptedCount = groupedDonors.filter(r => r.status === 'ACCEPTED').length;

    if (alertedCountEl) {
      alertedCountEl.textContent = `${donorsAlertedCount} Donor${donorsAlertedCount === 1 ? '' : 's'}`;
    }
    if (responseCountEl) {
      responseCountEl.textContent = acceptedCount;
    }
    if (streamBadge) {
      streamBadge.textContent = `${donorsAlertedCount} Alerted • ${acceptedCount} Accepted`;
    }

    if (!responseFeed) return;

    if (groupedDonors.length === 0) {
      const reqIds = targetRequests.map(r => `#REQ-${r.id}`).join(', ');
      const reasonText = customEmptyReason || `Requirement(s) (${reqIds}) exist for ${bloodGroup}, but no donor dispatches have been transmitted yet.`;
      responseFeed.innerHTML = `
        <div class="empty-state py-4 text-center">
          <div class="empty-state-icon mb-2"><i class="fa-solid fa-satellite-dish text-warning fa-2x animate-pulse-sos"></i></div>
          <h5 class="fw-bold text-slate-900">0 Donors Dispatched</h5>
          <p class="text-xs text-muted">${reasonText}</p>
          <a href="/match?group=${encodeURIComponent(bloodGroup)}" class="btn btn-outline-primary btn-sm mt-2">
            <i class="fa-solid fa-wand-magic-sparkles me-1"></i> Open Requirement Matcher
          </a>
        </div>
      `;
      return;
    }

    // Render grouped donor cards
    responseFeed.innerHTML = '';
    groupedDonors.forEach(item => {
      const timeLabel = formatTimeDisplay(item.latest_time);
      let statusBadgeHtml = '';

      if (item.status === 'ACCEPTED') {
        statusBadgeHtml = '<span class="badge badge-success"><i class="fa-solid fa-circle-check me-1"></i> ACCEPTED</span>';
      } else if (item.status === 'REJECTED' || item.status === 'DECLINED') {
        statusBadgeHtml = '<span class="badge badge-danger"><i class="fa-solid fa-circle-xmark me-1"></i> DECLINED</span>';
      } else {
        statusBadgeHtml = '<span class="badge badge-teal"><i class="fa-solid fa-paper-plane me-1"></i> DISPATCHED (PENDING)</span>';
      }

      const reqLabels = item.request_ids.map(id => `#REQ-${id}`).join(', ');

      const card = document.createElement('div');
      card.id = `emergencyDonorCard-${item.donor_id}`;
      card.className = 'match-candidate-card animate-fade-in p-3 mb-2 border rounded-3 bg-white shadow-sm';
      card.innerHTML = `
        <div class="d-flex align-center justify-between flex-wrap gap-2">
          <div class="d-flex align-center gap-3">
            <div class="blood-badge blood-badge-solid">${item.donor_blood_group}</div>
            <div>
              <div class="d-flex align-center gap-2">
                <span class="fw-bold text-slate-900">${item.donor_name}</span>
                ${reqLabels ? `<span class="badge badge-outline-secondary" style="font-size: 0.7rem;">${reqLabels}</span>` : ''}
              </div>
              <div class="text-xs text-muted mt-1">
                <i class="fa-solid fa-hospital text-primary me-1"></i> ${item.hospital_name}
                <span class="mx-1">•</span>
                <i class="fa-regular fa-clock me-1"></i> ${timeLabel}
                ${item.donor_phone ? `<span class="mx-1">•</span><i class="fa-solid fa-phone me-1"></i> ${item.donor_phone}` : ''}
              </div>
            </div>
          </div>
          <div class="d-flex align-center gap-2">
            ${statusBadgeHtml}
          </div>
        </div>
      `;
      responseFeed.appendChild(card);
    });

  } catch (err) {
    console.error('Error fetching grouped dispatches:', err);
  }
};

const startCountdownTimer = () => {
  const timerEl = document.getElementById('emergencyTimer');
  if (!timerEl) return;

  clearInterval(broadcastInterval);
  secondsRemaining = 600;
  broadcastInterval = setInterval(() => {
    secondsRemaining--;
    if (secondsRemaining <= 0) {
      clearInterval(broadcastInterval);
      timerEl.textContent = '00:00';
      return;
    }
    const m = String(Math.floor(secondsRemaining / 60)).padStart(2, '0');
    const s = String(secondsRemaining % 60).padStart(2, '0');
    timerEl.textContent = `${m}:${s}`;
  }, 1000);
};

window.addEventListener('beforeunload', () => {
  clearInterval(broadcastInterval);
  clearInterval(pollInterval);
});
