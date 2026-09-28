/**
 * HemoNexus Code-Red Emergency Broadcast Engine
 * Integrates real-time SOS blood request registration, heuristic matching, and direct donor dispatching.
 */

document.addEventListener('DOMContentLoaded', () => {
  const broadcastBtn = document.getElementById('btnTriggerBroadcast');
  if (!broadcastBtn) return;

  broadcastBtn.addEventListener('click', () => {
    startEmergencyBroadcast();
  });
});

let broadcastInterval = null;
let secondsRemaining = 600; // 10 minutes emergency window

const startEmergencyBroadcast = async () => {
  const broadcastBtn = document.getElementById('btnTriggerBroadcast');
  const bloodGroup = document.getElementById('emergencyBloodGroup')?.value || 'O-';
  const radius = parseFloat(document.getElementById('emergencyRadius')?.value) || 10.0;
  const component = document.getElementById('emergencyComponent')?.value || 'Whole Blood';

  const broadcastStatus = document.getElementById('broadcastActiveState');
  const broadcastTrigger = document.getElementById('broadcastTriggerCard');
  const responseCountEl = document.getElementById('liveResponseCount');
  const responseFeed = document.getElementById('emergencyResponseList');

  const originalBtnHtml = broadcastBtn ? broadcastBtn.innerHTML : '';
  if (broadcastBtn) {
    broadcastBtn.disabled = true;
    broadcastBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Initializing Code-Red Network...';
  }

  try {
    // 1. Create Real Emergency Blood Request on Backend
    const reqPayload = {
      required_blood_group: bloodGroup,
      hospital_name: 'Lilavati Hospital & Research Centre, ICU Trauma',
      location: 'Lilavati Hospital ICU Bay #01',
      urgency: 'CRITICAL',
      required_units: 3,
      preferred_max_distance: radius
    };

    const createRes = await HemoAPI.createBloodRequest(reqPayload);
    if (!createRes || !createRes.success || !createRes.request) {
      throw new Error(createRes.error || 'Failed to create emergency blood request.');
    }

    const emergencyReqId = createRes.request.id;

    if (broadcastTrigger) broadcastTrigger.classList.add('d-none');
    if (broadcastStatus) broadcastStatus.classList.remove('d-none');

    HemoUI.showToast(
      '🚨 Code-Red Broadcast Dispatched!',
      `Emergency requirement #${emergencyReqId} for ${bloodGroup} (${component}) transmitted to verified donor network.`,
      'error'
    );

    // Start 10-min countdown timer
    const timerEl = document.getElementById('emergencyTimer');
    if (timerEl) {
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
    }

    // 2. Fetch Real Matching Candidates
    const matchRes = await HemoAPI.getRequestMatches(emergencyReqId);
    const matches = (matchRes && matchRes.success && Array.isArray(matchRes.matches)) ? matchRes.matches : [];

    if (responseFeed) responseFeed.innerHTML = '';

    if (matches.length === 0) {
      if (responseFeed) {
        responseFeed.innerHTML = `
          <div class="empty-state py-4 text-center">
            <div class="empty-state-icon mb-2"><i class="fa-solid fa-satellite-dish text-warning fa-2x animate-pulse-sos"></i></div>
            <h5 class="fw-bold text-slate-900">Broadcast Transmitted — Zero Immediate Donors</h5>
            <p class="text-xs text-muted">No donors currently within ${radius} km radius. Request #${emergencyReqId} remains active in matching pipeline for incoming availability.</p>
            <a href="/match?request_id=${emergencyReqId}" class="btn btn-outline-primary btn-sm mt-2">
              <i class="fa-solid fa-wand-magic-sparkles me-1"></i> Open Match Engine
            </a>
          </div>
        `;
      }
      return;
    }

    let dispatchedCount = 0;
    // Dispatch to top matching donors
    for (let i = 0; i < matches.length; i++) {
      const match = matches[i];
      const donorUserId = match.user_id || match.donor_id || match.id;
      const donorName = match.full_name || match.name || 'Verified Donor';

      try {
        await HemoAPI.sendDonorRequest(emergencyReqId, donorUserId);
        dispatchedCount++;
        if (responseCountEl) responseCountEl.textContent = dispatchedCount;

        const item = document.createElement('div');
        item.className = 'match-candidate-card animate-fade-in p-3 mb-2 border rounded-3 bg-white shadow-sm';
        item.innerHTML = `
          <div class="d-flex align-center justify-between flex-wrap gap-2">
            <div class="d-flex align-center gap-3">
              <div class="blood-badge blood-badge-solid">${match.blood_group || bloodGroup}</div>
              <div>
                <div class="d-flex align-center gap-2">
                  <span class="fw-bold text-slate-900">${donorName}</span>
                  <span class="badge badge-success"><i class="fa-solid fa-satellite-dish"></i> Dispatched (${match.match_score || 95}% Match)</span>
                </div>
                <div class="text-xs text-muted mt-1">
                  <i class="fa-solid fa-location-dot text-primary"></i> ${match.masked_location || 'Zone'} • ${match.distance_km || radius} km away
                </div>
              </div>
            </div>
            <div class="d-flex align-center gap-2">
              ${match.phone ? `<a href="tel:${match.phone}" class="btn btn-outline btn-sm"><i class="fa-solid fa-phone"></i> Call</a>` : ''}
              <span class="badge badge-teal"><i class="fa-solid fa-clock"></i> Alert Sent</span>
            </div>
          </div>
        `;
        if (responseFeed) responseFeed.prepend(item);

        HemoUI.showToast(
          'Emergency Alert Dispatched',
          `Direct notification sent to ${donorName} (${match.blood_group || bloodGroup}).`,
          'success'
        );
      } catch (dispatchErr) {
        console.warn(`Could not dispatch to donor ${donorUserId}:`, dispatchErr);
      }
    }
  } catch (err) {
    console.error('Error during emergency broadcast:', err);
    if (broadcastBtn) {
      broadcastBtn.disabled = false;
      broadcastBtn.innerHTML = originalBtnHtml;
    }
    HemoUI.showToast('Broadcast Failed', err.message || 'Could not initiate emergency broadcast.', 'error');
  }
};
