/**
 * HEMONEXAS Patient Dashboard Client
 */

let currentMatchingRequestId = null;

async function initPatientDashboard() {
  await loadPatientRequests();
  setupEventListeners();
}

function setupEventListeners() {
  const form = document.getElementById('newRequestForm');
  if (form) {
    form.addEventListener('submit', handleCreateRequest);
  }
}

async function handleCreateRequest(e) {
  e.preventDefault();
  const btn = document.getElementById('createReqBtn');
  btn.disabled = true;
  btn.textContent = 'Publishing & Finding Matches...';

  const form = document.getElementById('newRequestForm');
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  try {
    const res = await fetch('/api/patient/blood-requests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const json = await res.json();

    if (res.ok && json.success) {
      showToast('Blood request published successfully!', 'success');
      form.reset();
      await loadPatientRequests();
      // Automatically trigger match drawer for the newly created request
      openMatchingModal(json.request.id, json.request.required_blood_group);
    } else {
      showToast(json.error || 'Failed to create blood request', 'danger');
    }
  } catch (err) {
    showToast('Network error publishing blood request', 'danger');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Publish Blood Request & Match Donors';
  }
}

async function loadPatientRequests() {
  const loading = document.getElementById('requestsLoading');
  const container = document.getElementById('requestsList');

  try {
    const res = await fetch('/api/patient/blood-requests');
    const json = await res.json();

    loading.style.display = 'none';
    container.style.display = 'block';

    if (res.ok && json.success) {
      const list = json.requests || [];
      if (list.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
            No blood requests found. Fill in the form on the left to request blood.
          </div>
        `;
        return;
      }

      container.innerHTML = list.map(r => `
        <div style="border: 1px solid var(--border-color); border-radius: var(--radius); padding: 1.1rem; margin-bottom: 0.9rem; background: #ffffff;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
            <div>
              <strong style="font-size: 1.1rem; color: var(--primary);">${r.required_blood_group} Blood Required (${r.required_units} Unit${r.required_units > 1 ? 's' : ''})</strong>
              <div style="font-size: 0.85rem; color: var(--text-muted);">
                Urgency: <span class="badge badge-open">${r.urgency}</span> &bull; Radius: ${r.preferred_max_distance} km
              </div>
            </div>
            <span class="badge badge-${r.request_status.toLowerCase()}">${r.request_status}</span>
          </div>

          <div style="font-size: 0.88rem; margin: 0.4rem 0;">
            &#127973; <strong>Hospital:</strong> ${r.hospital_name} (${r.location})
          </div>

          <div style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.8rem;">
            Dispatched Invitations: <strong>${r.total_sent || 0}</strong> | 
            Accepted: <strong style="color: var(--success);">${r.accepted_count || 0}</strong> | 
            Pending: <strong>${r.pending_count || 0}</strong>
          </div>

          <div style="display: flex; gap: 0.6rem; flex-wrap: wrap;">
            ${r.request_status !== 'CANCELLED' && r.request_status !== 'FULFILLED' ? `
              <button class="btn btn-primary btn-sm" onclick="openMatchingModal(${r.id}, '${r.required_blood_group}')">
                &#129517; Smart Match Donors
              </button>
              <button class="btn btn-success btn-sm" onclick="markFulfilled(${r.id})">
                &#10004; Mark Fulfilled
              </button>
              <button class="btn btn-outline btn-sm" onclick="cancelRequest(${r.id})">
                Cancel
              </button>
            ` : `
              <span style="font-size: 0.85rem; color: var(--text-muted);">Request is ${r.request_status.toLowerCase()}.</span>
            `}
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    loading.textContent = 'Failed to load blood requests.';
  }
}

async function markFulfilled(requestId) {
  if (!confirm('Are you sure you want to mark this blood request as fulfilled?')) return;
  try {
    const res = await fetch(`/api/patient/blood-requests/${requestId}/fulfill`, { method: 'POST' });
    const json = await res.json();
    if (res.ok && json.success) {
      showToast('Request marked as fulfilled!', 'success');
      await loadPatientRequests();
    }
  } catch (e) {
    showToast('Failed to mark request fulfilled', 'danger');
  }
}

async function cancelRequest(requestId) {
  if (!confirm('Are you sure you want to cancel this blood request?')) return;
  try {
    const res = await fetch(`/api/patient/blood-requests/${requestId}/cancel`, { method: 'POST' });
    const json = await res.json();
    if (res.ok && json.success) {
      showToast('Blood request cancelled.', 'success');
      await loadPatientRequests();
    }
  } catch (e) {
    showToast('Failed to cancel request', 'danger');
  }
}

async function openMatchingModal(requestId, bloodGroup) {
  currentMatchingRequestId = requestId;
  const modal = document.getElementById('matchingModal');
  const title = document.getElementById('matchingModalTitle');
  const summary = document.getElementById('matchSummaryText');
  const loading = document.getElementById('matchesLoading');
  const container = document.getElementById('matchesContainer');

  title.innerHTML = `&#129517; Smart Matching Engine: <strong>${bloodGroup}</strong> Donors`;
  summary.textContent = 'Searching candidate pool...';
  loading.style.display = 'block';
  container.style.display = 'none';
  modal.style.display = 'flex';

  try {
    const res = await fetch(`/api/patient/blood-requests/${requestId}/matches`);
    const json = await res.json();

    loading.style.display = 'none';
    container.style.display = 'block';

    if (res.ok && json.success) {
      const matches = json.matches || [];
      summary.innerHTML = `Found <strong>${matches.length}</strong> active, schedule-compatible donor(s) meeting mutual travel distance limits:`;

      if (matches.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 2rem;">
            No active donors found matching the blood group, schedule, and distance limits.<br>
            <small>Try broadening your preferred search radius or check back shortly.</small>
          </div>
        `;
        return;
      }

      container.innerHTML = matches.map((d, index) => `
        <div style="border: 1px solid var(--border-color); border-radius: var(--radius); padding: 1rem; margin-bottom: 0.8rem; background: ${index === 0 ? '#f0fdf4' : '#ffffff'};">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <div style="display: flex; align-items: center; gap: 0.6rem;">
                <strong style="font-size: 1.05rem;">${d.full_name}</strong>
                <span class="badge badge-active">${d.blood_group}</span>
                ${index === 0 ? '<span class="badge badge-open" style="background:#bbf7d0; color:#14532d;">★ Best Match</span>' : ''}
              </div>
              <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.2rem;">
                &#128205; ${d.location} &bull; <strong>${d.distance_km} km away</strong> (Max donor travel: ${d.maximum_travel_distance} km)
              </div>
            </div>

            <div style="text-align: right;">
              <div style="font-size: 1.3rem; font-weight: 800; color: var(--primary);">${d.match_score}%</div>
              <div style="font-size: 0.75rem; color: var(--text-muted);">Match Score</div>
            </div>
          </div>

          <div style="margin-top: 0.6rem; display: flex; gap: 1rem; font-size: 0.82rem; color: var(--text-muted); flex-wrap: wrap;">
            <span>&#128337; Availability: <strong>${d.availability.replace('_', ' ')}</strong></span>
            <span>&#10004; Verified: <strong>${d.last_verified_date.slice(0, 10)}</strong></span>
            <span>&#128222; Contact: <strong>${d.phone || 'Available upon dispatch'}</strong></span>
          </div>

          <div style="display: flex; justify-content: flex-end; margin-top: 0.8rem;">
            ${d.is_already_contacted ? `
              <span class="badge badge-${d.contact_status ? d.contact_status.toLowerCase() : 'pending'}">
                Request Sent (${d.contact_status || 'PENDING'})
              </span>
            ` : `
              <button class="btn btn-primary btn-sm" onclick="sendDonationInvitation(${requestId}, ${d.user_id}, this)">
                &#128227; Send Donation Request
              </button>
            `}
          </div>
        </div>
      `).join('');
    } else {
      container.innerHTML = `<div class="alert alert-danger">${json.error || 'Matching error'}</div>`;
    }
  } catch (err) {
    loading.textContent = 'Error executing matching engine.';
  }
}

async function sendDonationInvitation(requestId, donorUserId, btn) {
  btn.disabled = true;
  btn.textContent = 'Sending...';

  try {
    const res = await fetch(`/api/patient/blood-requests/${requestId}/send-request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ donor_id: donorUserId })
    });
    const json = await res.json();

    if (res.ok && json.success) {
      showToast('Donation request sent to donor!', 'success');
      btn.outerHTML = '<span class="badge badge-pending">Request Sent (PENDING)</span>';
      await loadPatientRequests();
    } else {
      showToast(json.error || 'Failed to dispatch request', 'danger');
      btn.disabled = false;
      btn.textContent = 'Send Donation Request';
    }
  } catch (e) {
    showToast('Network error dispatching request', 'danger');
    btn.disabled = false;
  }
}

function closeMatchingModal() {
  document.getElementById('matchingModal').style.display = 'none';
  currentMatchingRequestId = null;
}
