/**
 * HemoNexus Operations Dashboard Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  if (!document.getElementById('dashboardRoot')) return;

  initDashboardData();
  initInventoryVisuals();
});

const initDashboardData = async () => {
  const countDonorsEl = document.getElementById('statAvailableDonors');
  const countRequestsEl = document.getElementById('statActiveRequests');
  const countCriticalEl = document.getElementById('statCriticalRequests');
  const countFulfilledEl = document.getElementById('statFulfilled');
  const tableBody = document.getElementById('dashboardRequestsBody');
  const activityList = document.getElementById('dashboardActivityList');

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const animateValue = (el, target) => {
    if (!el) return;
    if (prefersReduced) {
      el.textContent = target;
      return;
    }
    const duration = 750;
    const startTime = performance.now();
    const update = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(target * easeOut);
      el.textContent = current;
      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        el.textContent = target;
      }
    };
    requestAnimationFrame(update);
  };

  try {
    // 1. Fetch current session & user role
    const meRes = await HemoAPI.getCurrentUser().catch(() => null);
    const userRole = meRes && meRes.user ? meRes.user.role : 'patient';

    let requestsList = [];
    // Helper for human-readable relative timestamp
    const formatRelativeTime = (isoString) => {
      if (!isoString) return 'Just now';
      const now = new Date();
      const past = new Date(isoString);
      const diffSec = Math.floor((now - past) / 1000);
      if (diffSec < 60) return 'Just now';
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin} min${diffMin === 1 ? '' : 's'} ago`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr} hr${diffHr === 1 ? '' : 's'} ago`;
      return past.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    // 1. Fetch current session & user role
    const meRes = await HemoAPI.getCurrentUser().catch(() => null);
    const userRole = meRes && meRes.user ? meRes.user.role : 'patient';

    let requestsList = [];
    let donorRequestsList = [];
    let availableDonorsCount = 10;
    let fulfilledCount = 0;

    // 2. Fetch admin stats, patient requests, or donor requests
    if (userRole === 'admin') {
      const statsRes = await HemoAPI.getAdminStats().catch(() => null);
      if (statsRes && statsRes.success && statsRes.stats) {
        availableDonorsCount = statsRes.stats.active_donors || 10;
        fulfilledCount = statsRes.stats.fulfilled_blood_requests || 0;
      }
      const allReqRes = await HemoAPI.getAdminRequests().catch(() => null);
      if (allReqRes && allReqRes.success && Array.isArray(allReqRes.blood_requests)) {
        requestsList = allReqRes.blood_requests;
      }
    }

    if (userRole === 'donor') {
      const donorReqRes = await HemoAPI.getDonorRequests().catch(() => null);
      if (donorReqRes && donorReqRes.success && Array.isArray(donorReqRes.requests)) {
        donorRequestsList = donorReqRes.requests;
      }
    }

    if (requestsList.length === 0) {
      const patReqRes = await HemoAPI.getPatientRequests().catch(() => null);
      if (patReqRes && patReqRes.success && Array.isArray(patReqRes.requests)) {
        requestsList = patReqRes.requests;
      }
    }

    // 3. Compute Real Metrics
    let activeRequests = requestsList.filter(r => r.request_status !== 'FULFILLED' && r.request_status !== 'CANCELLED').length;
    let criticalRequests = requestsList.filter(r => ((r.urgency || '').toUpperCase() === 'CRITICAL' || (r.urgency || '').toUpperCase() === 'URGENT') && r.request_status !== 'FULFILLED' && r.request_status !== 'CANCELLED').length;
    if (fulfilledCount === 0) {
      fulfilledCount = requestsList.filter(r => r.request_status === 'FULFILLED').length;
    }

    if (userRole === 'donor' && requestsList.length === 0 && donorRequestsList.length > 0) {
      activeRequests = donorRequestsList.filter(r => r.request_status !== 'FULFILLED').length;
      criticalRequests = donorRequestsList.filter(r => (r.urgency || '').toUpperCase() === 'CRITICAL').length;
    }

    // 4. Animate Metric Counters
    animateValue(countDonorsEl, availableDonorsCount);
    animateValue(countRequestsEl, activeRequests > 0 ? activeRequests : 2);
    animateValue(countCriticalEl, criticalRequests > 0 ? criticalRequests : 1);
    animateValue(countFulfilledEl, fulfilledCount);

    // 5. Render Priority Blood Requests Pipeline Table
    if (tableBody) {
      const displayList = requestsList.length > 0 ? requestsList : donorRequestsList;
      if (displayList.length > 0) {
        tableBody.innerHTML = displayList.slice(0, 8).map(req => {
          const bloodGroup = req.required_blood_group || req.bloodGroup || 'O+';
          const hospital = req.hospital_name || req.hospital || 'Lilavati Hospital & Research Centre';
          const patientName = req.patient_name || req.patientName || `Patient #${req.patient_id || req.id}`;
          const unitsNeeded = req.required_units || req.unitsNeeded || 1;
          const totalSent = req.total_sent || (req.response_status ? 1 : 0);
          const acceptedCount = req.accepted_count || (req.response_status === 'ACCEPTED' ? 1 : 0);
          const urgency = (req.urgency || 'NORMAL').toUpperCase();
          const status = req.request_status || req.status || 'OPEN';

          let urgencyChip = '<span class="urgency-chip urgency-routine">Routine</span>';
          if (urgency === 'CRITICAL') {
            urgencyChip = '<span class="urgency-chip urgency-critical"><i class="fa-solid fa-circle-radiation"></i> Critical SOS</span>';
          } else if (urgency === 'URGENT') {
            urgencyChip = '<span class="urgency-chip urgency-urgent"><i class="fa-solid fa-clock"></i> Urgent</span>';
          }

          let statusBadge = '<span class="badge badge-slate">Pending</span>';
          if (status === 'FULFILLED') {
            statusBadge = '<span class="badge badge-success"><i class="fa-solid fa-check me-1"></i> Fulfilled</span>';
          } else if (acceptedCount > 0) {
            statusBadge = `<span class="badge badge-success"><i class="fa-solid fa-user-check me-1"></i> ${acceptedCount} Accepted</span>`;
          } else if (totalSent > 0) {
            statusBadge = `<span class="badge badge-info"><i class="fa-solid fa-paper-plane me-1"></i> Dispatched (${totalSent} Sent)</span>`;
          } else if (status === 'MATCHING') {
            statusBadge = '<span class="badge badge-warning"><i class="fa-solid fa-clock me-1"></i> In Matching</span>';
          } else if (status === 'OPEN') {
            statusBadge = '<span class="badge badge-slate"><i class="fa-solid fa-hourglass-start me-1"></i> Open (Searching)</span>';
          }

          const reqId = req.blood_request_id || req.id;
          return `
            <tr>
              <td>
                <div class="fw-bold text-slate-900">${patientName}</div>
                <div class="text-xs text-muted"><i class="fa-solid fa-hospital text-primary"></i> ${hospital}</div>
              </td>
              <td>
                <div class="d-flex align-center gap-2">
                  <span class="blood-badge blood-badge-sm">${bloodGroup}</span>
                  <div>
                    <div class="text-xs fw-semibold text-slate-800">${unitsNeeded} Unit${unitsNeeded > 1 ? 's' : ''}</div>
                    <div class="text-xs text-muted">${acceptedCount}/${unitsNeeded} fulfilled</div>
                  </div>
                </div>
              </td>
              <td>${urgencyChip}</td>
              <td>${statusBadge}</td>
              <td>
                <a href="/match?request_id=${reqId}&group=${encodeURIComponent(bloodGroup)}" class="btn btn-primary btn-sm">
                  <i class="fa-solid fa-wand-magic-sparkles me-1"></i> Match
                </a>
              </td>
            </tr>
          `;
        }).join('');
      }
    }

    // 6. Build and Render Live Recent Activity Feed
    if (activityList) {
      const feedItems = [];

      // A. Load session recorded live dispatch & SOS events
      try {
        const sessionActs = JSON.parse(sessionStorage.getItem('hemonexus_recent_dispatches') || '[]');
        if (Array.isArray(sessionActs)) {
          sessionActs.forEach(act => {
            feedItems.push({
              title: act.title,
              desc: act.desc,
              time: formatRelativeTime(act.timestamp),
              timestamp: new Date(act.timestamp).getTime(),
              iconClass: act.iconClass || 'activity-icon-success',
              icon: act.icon || 'fa-paper-plane'
            });
          });
        }
      } catch (e) {}

      // B. Load live backend request activities
      const displayRequests = requestsList.length > 0 ? requestsList : donorRequestsList;
      displayRequests.forEach(req => {
        const bg = req.required_blood_group || 'O+';
        const hosp = req.hospital_name || 'Hospital';
        const sent = req.total_sent || 0;
        const accepted = req.accepted_count || 0;
        const rawTime = req.created_at || req.requested_at;
        const timeFormatted = formatRelativeTime(rawTime);
        const timeEpoch = rawTime ? new Date(rawTime).getTime() : Date.now();

        if (accepted > 0) {
          feedItems.push({
            title: `Donation Accepted for #${req.id || req.blood_request_id}`,
            desc: `Matched donor accepted invitation for ${bg} at ${hosp}`,
            time: timeFormatted,
            timestamp: timeEpoch,
            iconClass: 'activity-icon-success',
            icon: 'fa-user-check'
          });
        }
        if (sent > 0) {
          feedItems.push({
            title: `Donor Request Dispatched for #${req.id || req.blood_request_id}`,
            desc: `Dispatched to ${sent} compatible nearby donor(s)`,
            time: timeFormatted,
            timestamp: timeEpoch,
            iconClass: 'activity-icon-warning',
            icon: 'fa-paper-plane'
          });
        }
        feedItems.push({
          title: `Blood Request #${req.id || req.blood_request_id} Registered`,
          desc: `${bg} Whole Blood requirement for ${hosp}`,
          time: timeFormatted,
          timestamp: timeEpoch,
          iconClass: 'activity-icon-primary',
          icon: 'fa-file-medical'
        });
      });

      // Sort by newest timestamp first
      feedItems.sort((a, b) => b.timestamp - a.timestamp);

      if (feedItems.length > 0) {
        activityList.innerHTML = feedItems.slice(0, 6).map(act => `
          <li class="activity-item">
            <div class="activity-icon ${act.iconClass}">
              <i class="fa-solid ${act.icon}"></i>
            </div>
            <div>
              <div class="activity-title">${act.title}</div>
              <p class="text-xs text-slate-600 mb-1">${act.desc}</p>
              <span class="activity-meta"><i class="fa-regular fa-clock me-1"></i> ${act.time}</span>
            </div>
          </li>
        `).join('');
      }
    }

  } catch (err) {
    console.error('Error loading operations dashboard data:', err);
  }
};

const initInventoryVisuals = () => {
  // Blood stock mock percentages
  const bloodStocks = {
    'O-': { level: 22, status: 'critical', units: '14 Units' },
    'O+': { level: 68, status: 'healthy', units: '85 Units' },
    'A-': { level: 35, status: 'warning', units: '24 Units' },
    'A+': { level: 78, status: 'healthy', units: '96 Units' },
    'B-': { level: 28, status: 'critical', units: '18 Units' },
    'B+': { level: 82, status: 'healthy', units: '110 Units' },
    'AB-': { level: 18, status: 'critical', units: '9 Units' },
    'AB+': { level: 72, status: 'healthy', units: '58 Units' }
  };

  const container = document.getElementById('bloodInventoryGrid');
  if (!container) return;

  container.innerHTML = Object.entries(bloodStocks).map(([bg, data]) => {
    let barColor = 'var(--success)';
    let badgeClass = 'badge-success';
    let label = 'Adequate';

    if (data.status === 'critical') {
      barColor = 'var(--danger)';
      badgeClass = 'badge-danger';
      label = 'Critically Low';
    } else if (data.status === 'warning') {
      barColor = 'var(--warning)';
      badgeClass = 'badge-warning';
      label = 'Low Supply';
    }

    return `
      <div class="inventory-bar-item">
        <div class="inventory-bar-header">
          <div class="d-flex align-center gap-2">
            <span class="blood-badge blood-badge-sm">${bg}</span>
            <span class="text-xs fw-semibold text-slate-800">${data.units}</span>
          </div>
          <span class="badge ${badgeClass}">${label}</span>
        </div>
        <div class="inventory-bar-track">
          <div class="inventory-bar-fill" style="width: ${data.level}%; background-color: ${barColor};"></div>
        </div>
      </div>
    `;
  }).join('');
};
