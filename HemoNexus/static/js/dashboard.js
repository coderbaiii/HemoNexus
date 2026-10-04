/**
 * HemoNexus Operations Dashboard Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  if (!document.getElementById('dashboardRoot')) return;

  initDashboardData();
  initInventoryVisuals();
});

window.addEventListener('pageshow', (e) => {
  if (document.getElementById('dashboardRoot')) {
    initDashboardData();
  }
});

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && document.getElementById('dashboardRoot')) {
    initDashboardData();
  }
});

const initDashboardData = async () => {
  const countDonorsEl = document.getElementById('statAvailableDonors');
  const countRequestsEl = document.getElementById('statActiveRequests');
  const countCriticalEl = document.getElementById('statCriticalRequests');
  const countFulfilledEl = document.getElementById('statFulfilled');
  const tableBody = document.getElementById('dashboardRequestsBody');
  const dispatchesBody = document.getElementById('dashboardDispatchesBody');
  const dispatchesBadge = document.getElementById('liveDispatchesBadge');
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

  // Helper for human-readable relative timestamp (Requirement 8: "10h ago")
  const formatRelativeTime = (isoString) => {
    if (window.HemoUI && typeof window.HemoUI.formatTimeAgo === 'function') {
      return window.HemoUI.formatTimeAgo(isoString);
    }
    if (!isoString) return 'Just now';
    try {
      const past = new Date(isoString).getTime();
      if (isNaN(past)) return 'Just now';
      const now = Date.now();
      const diffSec = Math.max(0, Math.floor((now - past) / 1000));
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

  try {
    // 1. Fetch current session & user role
    const meRes = await HemoAPI.getCurrentUser().catch(() => null);
    const userRole = meRes && meRes.user ? meRes.user.role : null;

    let requestsList = [];
    let dispatchResponses = [];
    let availableDonorsCount = 12;
    let fulfilledCount = 0;

    // 2. Fetch available verified donors from database
    const donorsRes = await HemoAPI.getDonors().catch(() => null);
    if (donorsRes && donorsRes.success && Array.isArray(donorsRes.donors)) {
      availableDonorsCount = donorsRes.donors.length;
    }

    // 3. Fetch real dispatches from backend /api/dispatches
    const dispatchesRes = await HemoAPI.getDispatches().catch(() => null);
    if (dispatchesRes && dispatchesRes.success && Array.isArray(dispatchesRes.dispatches)) {
      dispatchResponses = dispatchesRes.dispatches;
    }

    // 4. Fetch blood requests (admin gets all, patient/donor gets relevant or active)
    if (userRole === 'admin') {
      const statsRes = await HemoAPI.getAdminStats().catch(() => null);
      if (statsRes && statsRes.success && statsRes.stats) {
        availableDonorsCount = statsRes.stats.active_donors || availableDonorsCount;
        fulfilledCount = statsRes.stats.fulfilled_blood_requests || 0;
      }
      const allReqRes = await HemoAPI.getAdminRequests().catch(() => null);
      if (allReqRes && allReqRes.success && Array.isArray(allReqRes.requests)) {
        requestsList = allReqRes.requests;
      }
    } else {
      const patReqRes = await HemoAPI.getPatientRequests().catch(() => null);
      if (patReqRes && patReqRes.success && Array.isArray(patReqRes.requests)) {
        requestsList = patReqRes.requests;
      }
    }

    // Fallback if requestsList is still empty
    if (requestsList.length === 0) {
      const allReqRes = await HemoAPI.getAdminRequests().catch(() => null);
      if (allReqRes && allReqRes.success && Array.isArray(allReqRes.requests)) {
        requestsList = allReqRes.requests;
      }
    }

    // 5. Merge any recent dispatches stored in session storage (immediate dispatch feedback)
    try {
      const sessionDispatches = JSON.parse(sessionStorage.getItem('hemonexus_recent_dispatches') || '[]');
      sessionDispatches.forEach(s => {
        const alreadyExists = dispatchResponses.some(r =>
          (r.id && s.id && r.id == s.id) ||
          (r.blood_request_id == s.request_id && (r.donor_name === s.donor_name || r.donor_id == s.donor_id))
        );
        if (!alreadyExists && s.type === 'DISPATCH') {
          dispatchResponses.unshift({
            id: s.id || ('local_' + Date.now()),
            blood_request_id: s.request_id,
            donor_name: s.donor_name,
            donor_blood_group: s.blood_group || 'O+',
            hospital_name: s.hospital_name || 'Regional Medical Center',
            status: s.status || 'PENDING',
            created_at: s.timestamp || new Date().toISOString()
          });
        }
      });
    } catch (e) {}

    // 6. Compute Real Metrics
    let activeRequests = requestsList.filter(r => r.request_status !== 'FULFILLED' && r.request_status !== 'CANCELLED').length;
    let criticalRequests = requestsList.filter(r => ((r.urgency || '').toUpperCase() === 'CRITICAL' || (r.urgency || '').toUpperCase() === 'URGENT') && r.request_status !== 'FULFILLED' && r.request_status !== 'CANCELLED').length;
    if (fulfilledCount === 0) {
      fulfilledCount = requestsList.filter(r => r.request_status === 'FULFILLED').length;
    }

    // Animate Metric Counters
    animateValue(countDonorsEl, availableDonorsCount);
    animateValue(countRequestsEl, activeRequests > 0 ? activeRequests : requestsList.length);
    animateValue(countCriticalEl, criticalRequests);
    animateValue(countFulfilledEl, fulfilledCount);

    if (dispatchesBadge) {
      dispatchesBadge.innerHTML = `<i class="fa-solid fa-paper-plane me-1"></i> ${dispatchResponses.length} Live Dispatches`;
    }

    // 7. Render Live Dispatched Donors Radar Table
    if (dispatchesBody) {
      if (dispatchResponses.length > 0) {
        dispatchesBody.innerHTML = dispatchResponses.slice(0, 10).map(d => {
          const donorName = d.donor_name || 'Verified Donor';
          const bloodGroup = d.donor_blood_group || d.required_blood_group || 'O+';
          const hospital = d.hospital_name || 'Regional Hospital';
          const reqId = d.blood_request_id || d.request_id || '';
          const status = (d.status || 'PENDING').toUpperCase();
          const rawTime = d.created_at || d.response_time;

          let statusBadge = '<span class="badge badge-info"><i class="fa-solid fa-paper-plane me-1"></i> Pending</span>';
          if (status === 'ACCEPTED') {
            statusBadge = '<span class="badge badge-success"><i class="fa-solid fa-check me-1"></i> Accepted</span>';
          } else if (status === 'REJECTED') {
            statusBadge = '<span class="badge badge-secondary"><i class="fa-solid fa-xmark me-1"></i> Rejected</span>';
          }

          return `
            <tr>
              <td>
                <div class="d-flex align-center gap-2">
                  <span class="blood-badge blood-badge-sm">${bloodGroup}</span>
                  <div>
                    <div class="fw-bold text-slate-900">${donorName}</div>
                    <div class="text-xs text-muted"><i class="fa-solid fa-user-tag text-teal"></i> Verified Donor</div>
                  </div>
                </div>
              </td>
              <td>
                <div class="fw-bold text-slate-800">#REQ-${reqId}</div>
                <div class="text-xs text-muted"><i class="fa-solid fa-hospital text-primary"></i> ${hospital}</div>
              </td>
              <td>${statusBadge}</td>
              <td>
                <span class="text-xs text-muted"><i class="fa-regular fa-clock me-1"></i> ${formatRelativeTime(rawTime)}</span>
              </td>
              <td>
                <a href="/match?request_id=${reqId}&group=${encodeURIComponent(bloodGroup)}" class="btn btn-outline btn-sm">
                  <i class="fa-solid fa-crosshairs me-1"></i> Details
                </a>
              </td>
            </tr>
          `;
        }).join('');
      } else {
        dispatchesBody.innerHTML = `
          <tr id="dispatchesEmptyRow">
            <td colspan="5" class="py-4 text-center text-muted">
              <i class="fa-solid fa-paper-plane text-muted me-2"></i> No active dispatches found. Use <a href="/match" class="text-primary fw-bold">Smart Matcher</a> to dispatch donors.
            </td>
          </tr>
        `;
      }
    }

    // 8. Render Priority Blood Requests Pipeline Table
    if (tableBody && requestsList.length > 0) {
      tableBody.innerHTML = requestsList.slice(0, 8).map(req => {
        const bloodGroup = req.required_blood_group || req.bloodGroup || 'O+';
        const hospital = req.hospital_name || req.hospital || 'Hospital';
        const patientName = req.patient_name || req.patientName || `Requirement #${req.id}`;
        const unitsNeeded = req.required_units || req.unitsNeeded || 1;
        
        // Count dispatches for this request
        const matchingDispatches = dispatchResponses.filter(d => (d.blood_request_id || d.request_id) == req.id);
        const totalSent = Math.max(req.total_sent || 0, matchingDispatches.length);
        const acceptedCount = Math.max(req.accepted_count || 0, matchingDispatches.filter(d => (d.status || '').toUpperCase() === 'ACCEPTED').length);
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
          statusBadge = '<span class="badge badge-success"><i class="fa-solid fa-check me-1"></i> Accepted</span>';
        } else if (totalSent > 0) {
          statusBadge = '<span class="badge badge-info"><i class="fa-solid fa-paper-plane me-1"></i> Pending</span>';
        } else if (status === 'CANCELLED') {
          statusBadge = '<span class="badge badge-secondary"><i class="fa-solid fa-xmark me-1"></i> Rejected</span>';
        } else {
          statusBadge = '<span class="badge badge-slate">Pending</span>';
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

    // 9. Build and Render Live Recent Activity Feed
    if (activityList) {
      const feedItems = [];

      // A. Dispatches & Responses
      dispatchResponses.forEach(r => {
        const reqId = r.blood_request_id || r.request_id || '';
        const donorName = r.donor_name || 'Verified Donor';
        const bloodGroup = r.donor_blood_group || r.required_blood_group || 'O+';
        const hospital = r.hospital_name || 'Regional Hospital';
        const status = (r.status || 'PENDING').toUpperCase();
        const rawTime = r.created_at || r.response_time;
        const timeEpoch = rawTime ? new Date(rawTime).getTime() : Date.now();

        if (status === 'ACCEPTED') {
          feedItems.push({
            title: 'Donor Dispatch Confirmed',
            desc: `${donorName} accepted emergency request #REQ-${reqId} for ${hospital}.`,
            time: formatRelativeTime(rawTime),
            timestamp: timeEpoch,
            iconClass: 'activity-icon-success',
            icon: 'fa-circle-check'
          });
        } else if (status === 'REJECTED') {
          feedItems.push({
            title: 'Donor Response Recorded',
            desc: `${donorName} unavailable for request #REQ-${reqId}`,
            time: formatRelativeTime(rawTime),
            timestamp: timeEpoch,
            iconClass: 'activity-icon-warning',
            icon: 'fa-circle-xmark'
          });
        } else {
          feedItems.push({
            title: 'Donor Request Dispatched',
            desc: `${donorName} — ${bloodGroup} donor request dispatched for #REQ-${reqId} (${hospital})`,
            time: formatRelativeTime(rawTime),
            timestamp: timeEpoch,
            iconClass: 'activity-icon-primary',
            icon: 'fa-paper-plane'
          });
        }
      });

      // B. Requests from database
      requestsList.forEach(req => {
        const reqId = req.id || req.blood_request_id || '';
        const bloodGroup = req.required_blood_group || 'O+';
        const hospital = req.hospital_name || 'Hospital';
        const rawTime = req.created_at;
        const timeEpoch = rawTime ? new Date(rawTime).getTime() : Date.now();
        const urgency = (req.urgency || '').toUpperCase();
        const status = (req.request_status || req.status || 'OPEN').toUpperCase();

        feedItems.push({
          title: 'New Blood Request Registered',
          desc: `${urgency === 'CRITICAL' ? 'Emergency ' : ''}${bloodGroup} requirement #REQ-${reqId} registered for ${hospital}.`,
          time: formatRelativeTime(rawTime),
          timestamp: timeEpoch,
          iconClass: urgency === 'CRITICAL' ? 'activity-icon-danger' : 'activity-icon-primary',
          icon: 'fa-droplet'
        });

        if (status === 'FULFILLED') {
          const fulfilledTime = req.updated_at || req.created_at;
          feedItems.push({
            title: 'Donation Completed & Verified',
            desc: `Request #REQ-${reqId} fulfilled for ${hospital} with ${req.required_units || 1} unit(s) of ${bloodGroup}.`,
            time: formatRelativeTime(fulfilledTime),
            timestamp: fulfilledTime ? new Date(fulfilledTime).getTime() : timeEpoch,
            iconClass: 'activity-icon-teal',
            icon: 'fa-heart-circle-check'
          });
        }
      });

      // Sort newest first
      feedItems.sort((a, b) => b.timestamp - a.timestamp);

      if (feedItems.length > 0) {
        activityList.innerHTML = feedItems.slice(0, 10).map(act => `
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
      } else {
        activityList.innerHTML = `
          <li class="empty-state py-4 text-center">
            <div class="empty-state-icon mb-2"><i class="fa-solid fa-clock-rotate-left text-muted fa-2x"></i></div>
            <h5 class="fw-bold text-slate-900 mb-1">No Recent Activity</h5>
            <p class="text-xs text-muted mb-0">Dispatches and donation updates will appear here in real time.</p>
          </li>
        `;
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
