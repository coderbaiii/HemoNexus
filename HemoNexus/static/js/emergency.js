/**
 * HemoNexus Code-Red Emergency Broadcast Engine
 * Integrates real-time SOS blood request registration, heuristic matching, direct donor dispatching, and live status polling.
 */

document.addEventListener('DOMContentLoaded', () => {
  const broadcastBtn = document.getElementById('btnTriggerBroadcast');
  if (!broadcastBtn) return;

  broadcastBtn.addEventListener('click', () => {
    startEmergencyBroadcast();
  });
});

let broadcastInterval = null;
let pollInterval = null;
let secondsRemaining = 600; // 10 minutes emergency window
let activeEmergencyRequestId = null;

const startEmergencyBroadcast = async () => {
  const broadcastBtn = document.getElementById('btnTriggerBroadcast');
  const bloodGroup = document.getElementById('emergencyBloodGroup')?.value || 'O-';
  const radius = parseFloat(document.getElementById('emergencyRadius')?.value) || 10.0;
  const component = document.getElementById('emergencyComponent')?.value || 'Whole Blood';

  const broadcastStatus = document.getElementById('broadcastActiveState');
  const broadcastTrigger = document.getElementById('broadcastTriggerCard');
  const responseCountEl = document.getElementById('liveResponseCount');
  const responseFeed = document.getElementById('emergencyResponseList');

  const originalBtnHtml = broadcastBtn ? broadcastBtn.innerHTML : '<i class="fa-solid fa-satellite-dish"></i> Transmit Code-Red Broadcast Now';

  // 1. Role verification
  const me = await HemoAPI.getCurrentUser().catch(() => null);
  const userRole = me && me.user ? me.user.role : null;
  if (userRole && userRole !== 'patient' && userRole !== 'admin') {
    HemoUI.showToast('Authorization Notice', 'Emergency broadcast requires a patient account.', 'warning');
    return;
  }

  if (broadcastBtn) {
    broadcastBtn.disabled = true;
    broadcastBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Initializing Code-Red Network...';
  }

  try {
    // 2. Create Real Emergency Blood Request on Backend
    const reqPayload = {
      required_blood_group: bloodGroup,
      hospital_name: 'Lilavati Hospital & Research Centre, ICU Trauma',
      location: 'Lilavati Hospital ICU Bay #01',
      latitude: 22.5697,
      longitude: 88.4046,
      urgency: 'CRITICAL',
      required_units: 3,
      preferred_max_distance: radius
    };

    const createRes = await HemoAPI.createBloodRequest(reqPayload);
    if (!createRes || !createRes.success || !createRes.request) {
      throw new Error(createRes?.error || 'Failed to initialize emergency blood request on server.');
    }

    activeEmergencyRequestId = createRes.request.id;

    if (broadcastTrigger) broadcastTrigger.classList.add('d-none');
    if (broadcastStatus) broadcastStatus.classList.remove('d-none');

    HemoUI.showToast(
      '🚨 Code-Red Broadcast Transmitted',
      `Emergency requirement #${activeEmergencyRequestId} for ${bloodGroup} (${component}) broadcast across donor network.`,
      'error'
    );

    // 3. Start 10-min countdown timer
    const timerEl = document.getElementById('emergencyTimer');
    if (timerEl) {
      clearInterval(broadcastInterval);
      secondsRemaining = 600;
      broadcastInterval = setInterval(() => {
        secondsRemaining--;
        if (secondsRemaining <= 0) {
          clearInterval(broadcastInterval);
          clearInterval(pollInterval);
          timerEl.textContent = '00:00';
          return;
        }
        const m = String(Math.floor(secondsRemaining / 60)).padStart(2, '0');
        const s = String(secondsRemaining % 60).padStart(2, '0');
        timerEl.textContent = `${m}:${s}`;
      }, 1000);
    }

    // 4. Fetch Real Matching Candidates from Backend
    const matchRes = await HemoAPI.getRequestMatches(activeEmergencyRequestId);
    const matches = (matchRes && matchRes.success && Array.isArray(matchRes.matches)) ? matchRes.matches : [];

    if (responseFeed) responseFeed.innerHTML = '';

    if (matches.length === 0) {
      if (responseFeed) {
        responseFeed.innerHTML = `
          <div class="empty-state py-4 text-center">
            <div class="empty-state-icon mb-2"><i class="fa-solid fa-satellite-dish text-warning fa-2x animate-pulse-sos"></i></div>
            <h5 class="fw-bold text-slate-900">Broadcast Transmitted — Zero Immediate Donors</h5>
            <p class="text-xs text-muted">No registered donors within ${radius} km perimeter. Request #${activeEmergencyRequestId} remains active in matching pipeline.</p>
          </div>
        `;
      }
      return;
    }

    // 5. Render Real Match Cards and Dispatch
    matches.forEach(match => {
      const donorUserId = match.user_id || match.donor_id || match.id;
      const donorName = match.full_name || match.name || 'Verified Donor';
      const donorBg = match.blood_group || bloodGroup;
      const dist = match.distance_km != null ? match.distance_km : radius;
      const matchScore = match.match_score || 95;

      const card = document.createElement('div');
      card.id = `emergencyDonorCard-${donorUserId}`;
      card.className = 'match-candidate-card animate-fade-in p-3 mb-2 border rounded-3 bg-white shadow-sm';
      card.innerHTML = `
        <div class="d-flex align-center justify-between flex-wrap gap-2">
          <div class="d-flex align-center gap-3">
            <div class="blood-badge blood-badge-solid">${donorBg}</div>
            <div>
              <div class="d-flex align-center gap-2">
                <span class="fw-bold text-slate-900">${donorName}</span>
                <span class="badge badge-success"><i class="fa-solid fa-crosshairs"></i> ${matchScore}% Match</span>
              </div>
              <div class="text-xs text-muted mt-1">
                <i class="fa-solid fa-location-dot text-primary"></i> ${match.masked_location || 'Kolkata Region'} • ${dist} km away
              </div>
            </div>
          </div>
          <div class="d-flex align-center gap-2" id="emergencyActions-${donorUserId}">
            <button class="btn btn-emergency btn-sm" id="btnEmergencyDispatch-${donorUserId}" onclick="dispatchEmergencySingleDonor(${activeEmergencyRequestId}, ${donorUserId}, '${donorName.replace(/'/g, "\\'")}')">
              <i class="fa-solid fa-paper-plane me-1"></i> Dispatch Now
            </button>
          </div>
        </div>
      `;
      if (responseFeed) responseFeed.appendChild(card);
    });

    // Auto-dispatch all matching candidates for Code-Red SOS
    for (const match of matches) {
      const donorUserId = match.user_id || match.donor_id || match.id;
      const donorName = match.full_name || match.name || 'Verified Donor';
      await dispatchEmergencySingleDonor(activeEmergencyRequestId, donorUserId, donorName);
    }

    // 6. Start Real Live Response Polling
    startEmergencyResponsePolling(activeEmergencyRequestId);

  } catch (err) {
    console.error('Error during emergency broadcast:', err);
    if (broadcastBtn) {
      broadcastBtn.disabled = false;
      broadcastBtn.innerHTML = originalBtnHtml;
    }
    HemoUI.showToast('Broadcast Failed', err.message || 'Could not initiate emergency broadcast.', 'error');
  }
};

const dispatchEmergencySingleDonor = async (requestId, donorUserId, donorName) => {
  const btn = document.getElementById(`btnEmergencyDispatch-${donorUserId}`);
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Sending...';
  }

  try {
    const res = await HemoAPI.sendDonorRequest(requestId, donorUserId);
    if (res && res.success) {
      if (btn) {
        btn.className = 'btn btn-success btn-sm';
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-check me-1"></i> ✓ Request Dispatched';
      }
      const actions = document.getElementById(`emergencyActions-${donorUserId}`);
      if (actions && !document.getElementById(`statusBadge-${donorUserId}`)) {
        const statusSpan = document.createElement('span');
        statusSpan.id = `statusBadge-${donorUserId}`;
        statusSpan.className = 'badge badge-teal ms-1';
        statusSpan.innerHTML = '<i class="fa-solid fa-clock me-1"></i> PENDING';
        actions.appendChild(statusSpan);
      }
    }
  } catch (err) {
    if (err && err.status === 409) {
      if (btn) {
        btn.className = 'btn btn-secondary btn-sm';
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-clock-rotate-left me-1"></i> Already Dispatched';
      }
    } else {
      if (btn) {
        btn.disabled = false;
        btn.className = 'btn btn-emergency btn-sm';
        btn.innerHTML = '<i class="fa-solid fa-paper-plane me-1"></i> Dispatch Now';
      }
      console.warn(`Could not dispatch to donor ${donorUserId}:`, err);
    }
  }
};

const startEmergencyResponsePolling = (requestId) => {
  clearInterval(pollInterval);
  const responseCountEl = document.getElementById('liveResponseCount');

  pollInterval = setInterval(async () => {
    try {
      const details = await HemoAPI.getRequestDetails(requestId).catch(() => null);
      if (!details || !details.success || !Array.isArray(details.responses)) return;

      let acceptedCount = 0;
      details.responses.forEach(resp => {
        const donorId = resp.donor_id || resp.user_id;
        const statusBadge = document.getElementById(`statusBadge-${donorId}`);
        const status = (resp.status || 'PENDING').toUpperCase();

        if (status === 'ACCEPTED') {
          acceptedCount++;
          if (statusBadge) {
            statusBadge.className = 'badge badge-success ms-1';
            statusBadge.innerHTML = '<i class="fa-solid fa-circle-check me-1"></i> ACCEPTED';
          }
        } else if (status === 'REJECTED') {
          if (statusBadge) {
            statusBadge.className = 'badge badge-danger ms-1';
            statusBadge.innerHTML = '<i class="fa-solid fa-circle-xmark me-1"></i> DECLINED';
          }
        }
      });

      if (responseCountEl) {
        responseCountEl.textContent = acceptedCount;
      }
    } catch (e) {
      console.warn('Emergency polling error:', e);
    }
  }, 3500);
};

window.addEventListener('beforeunload', () => {
  clearInterval(broadcastInterval);
  clearInterval(pollInterval);
});
