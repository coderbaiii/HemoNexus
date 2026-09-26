/**
 * HemoNexus Code-Red Emergency Broadcast Engine
 * Simulates real-time multi-channel SOS alert broadcast, donor response polling, and rapid dispatch.
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

const startEmergencyBroadcast = () => {
  const bloodGroup = document.getElementById('emergencyBloodGroup')?.value || 'O-';
  const radius = document.getElementById('emergencyRadius')?.value || '10';
  const component = document.getElementById('emergencyComponent')?.value || 'Whole Blood';

  const broadcastStatus = document.getElementById('broadcastActiveState');
  const broadcastTrigger = document.getElementById('broadcastTriggerCard');
  const responseCountEl = document.getElementById('liveResponseCount');
  const responseFeed = document.getElementById('emergencyResponseList');

  if (broadcastTrigger) broadcastTrigger.classList.add('d-none');
  if (broadcastStatus) broadcastStatus.classList.remove('d-none');

  HemoUI.showToast(
    '🚨 Code-Red Broadcast Transmitted!',
    `Broadcasting emergency request for ${bloodGroup} ${component} within ${radius} km radius to all verified donors.`,
    'error'
  );

  // Find compatible donors
  const matches = HemoMatcher.findMatches({
    recipientGroup: bloodGroup,
    component: component,
    maxDistanceKm: parseInt(radius)
  });

  let respondedCount = 0;
  if (responseFeed) responseFeed.innerHTML = '';

  // Simulate donors accepting in real time
  matches.slice(0, 4).forEach((match, index) => {
    setTimeout(() => {
      respondedCount++;
      if (responseCountEl) responseCountEl.textContent = respondedCount;

      const item = document.createElement('div');
      item.className = 'match-candidate-card animate-fade-in';
      item.innerHTML = `
        <div class="d-flex align-center gap-3">
          <div class="blood-badge blood-badge-solid">${match.donor.bloodGroup}</div>
          <div>
            <div class="d-flex align-center gap-2">
              <span class="fw-bold text-slate-900">${match.donor.name}</span>
              <span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> Accepted (${match.matchScore}% Match)</span>
            </div>
            <div class="text-xs text-muted mt-1">
              <i class="fa-solid fa-location-dot text-primary"></i> ${match.donor.area} • ${match.donor.distanceKm} km away • ETA ~12 mins
            </div>
          </div>
        </div>
        <div class="d-flex align-center gap-2">
          <a href="tel:${match.donor.phone}" class="btn btn-outline btn-sm">
            <i class="fa-solid fa-phone"></i> Call
          </a>
          <button class="btn btn-primary btn-sm" onclick="dispatchEmergencyDonor('${match.donor.name}')">
            <i class="fa-solid fa-truck-medical"></i> Dispatch Now
          </button>
        </div>
      `;
      if (responseFeed) responseFeed.prepend(item);

      HemoUI.showToast(
        'Donor Accepted Alert',
        `${match.donor.name} (${match.donor.bloodGroup}) accepted the emergency request.`,
        'success'
      );
    }, (index + 1) * 2200);
  });
};

const dispatchEmergencyDonor = (donorName) => {
  HemoUI.showToast(
    'Ambulance & Hospital Alerted',
    `${donorName} is dispatched. Hospital ICU bed & intake desk notified.`,
    'success'
  );
};
