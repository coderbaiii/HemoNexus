/**
 * HEMONEXAS Donor Dashboard Client
 */

let activeResponseId = null;
let activeAction = null;

async function initDonorDashboard() {
  await loadDonorProfile();
  await loadDonorRequests();
  setupEventListeners();
}

function setupEventListeners() {
  const verifyBtn = document.getElementById('verifyBtn');
  if (verifyBtn) {
    verifyBtn.addEventListener('click', confirmVerification);
  }

  const profileForm = document.getElementById('profileForm');
  if (profileForm) {
    profileForm.addEventListener('submit', handleProfileUpdate);
  }

  const modalActionBtn = document.getElementById('modalActionBtn');
  if (modalActionBtn) {
    modalActionBtn.addEventListener('click', submitModalResponse);
  }
}

async function loadDonorProfile() {
  try {
    const res = await fetch('/api/donor/profile');
    const json = await res.json();

    if (res.ok && json.success) {
      const p = json.profile;
      const v = json.verification;

      // Populate form
      if (document.getElementById('p_blood')) document.getElementById('p_blood').value = p.blood_group || 'O+';
      if (document.getElementById('p_phone')) document.getElementById('p_phone').value = p.phone || '';
      if (document.getElementById('p_loc')) document.getElementById('p_loc').value = p.location || '';
      if (document.getElementById('p_avail')) document.getElementById('p_avail').value = p.availability || '24_HOURS';
      if (document.getElementById('p_max_dist')) document.getElementById('p_max_dist').value = p.maximum_travel_distance || 15;
      if (document.getElementById('p_lat')) document.getElementById('p_lat').value = p.latitude ?? '';
      if (document.getElementById('p_lon')) document.getElementById('p_lon').value = p.longitude ?? '';

      // Update Verification Card
      renderVerificationStatus(v);
    } else {
      showToast(json.error || 'Failed to load profile', 'danger');
    }
  } catch (err) {
    showToast('Failed to connect to donor service', 'danger');
  }
}

function renderVerificationStatus(v) {
  if (!v) return;

  const badge = document.getElementById('statusBadge');
  const statStatus = document.getElementById('statStatus');
  const statLast = document.getElementById('statLastVerified');
  const statNext = document.getElementById('statNextDue');
  const statDays = document.getElementById('statDaysRemaining');
  const alertBox = document.getElementById('statusAlertBox');

  const status = v.profile_status || 'ACTIVE';
  badge.className = `badge badge-${status.toLowerCase()}`;
  badge.textContent = status.replace('_', ' ');

  statStatus.textContent = status.replace('_', ' ');
  if (status === 'ACTIVE') statStatus.style.color = 'var(--success)';
  else if (status === 'VERIFICATION_DUE') statStatus.style.color = 'var(--warning)';
  else statStatus.style.color = 'var(--danger)';

  statLast.textContent = v.last_verified_date ? v.last_verified_date.slice(0, 10) : 'N/A';
  statNext.textContent = v.next_verification_date ? v.next_verification_date.slice(0, 10) : 'N/A';
  statDays.textContent = v.days_until_due !== undefined ? `${v.days_until_due} days` : 'N/A';

  alertBox.innerHTML = '';
  if (status === 'VERIFICATION_DUE') {
    alertBox.innerHTML = `
      <div class="alert alert-warning">
        &#9888; <strong>Verification Due:</strong> Your 6-month profile verification period has arrived. Please verify your contact and availability details now using the button above to maintain active donor priority!
      </div>
    `;
  } else if (status === 'INACTIVE') {
    alertBox.innerHTML = `
      <div class="alert alert-danger">
        &#9888; <strong>Profile Inactive:</strong> Your profile has lapsed beyond the grace period and is currently excluded from emergency blood searches. Click "Confirm Profile Freshness" to reactivate your donor status immediately.
      </div>
    `;
  }
}

async function confirmVerification() {
  const btn = document.getElementById('verifyBtn');
  btn.disabled = true;
  btn.textContent = 'Verifying...';

  try {
    const res = await fetch('/api/donor/profile/verify', { method: 'POST' });
    const json = await res.json();

    if (res.ok && json.success) {
      showToast('Profile confirmed! Status reset to ACTIVE for 6 months.', 'success');
      await loadDonorProfile();
    } else {
      showToast(json.error || 'Verification update failed', 'danger');
    }
  } catch (e) {
    showToast('Network error verifying profile', 'danger');
  } finally {
    btn.disabled = false;
    btn.textContent = '✓ Confirm Profile Freshness';
  }
}

async function handleProfileUpdate(e) {
  e.preventDefault();
  const btn = document.getElementById('saveProfileBtn');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  const form = document.getElementById('profileForm');
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  try {
    const res = await fetch('/api/donor/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const json = await res.json();

    if (res.ok && json.success) {
      showToast('Profile and availability settings updated!', 'success');
      await loadDonorProfile();
    } else {
      showToast(json.error || 'Update failed', 'danger');
    }
  } catch (err) {
    showToast('Network error updating profile', 'danger');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Profile Updates';
  }
}

async function loadDonorRequests() {
  const loading = document.getElementById('requestsLoading');
  const container = document.getElementById('requestsList');

  try {
    const res = await fetch('/api/donor/requests');
    const json = await res.json();

    loading.style.display = 'none';
    container.style.display = 'block';

    if (res.ok && json.success) {
      const requests = json.requests || [];
      if (requests.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
            No incoming blood donation requests at this time.
          </div>
        `;
        return;
      }

      container.innerHTML = requests.map(r => `
        <div style="border: 1px solid var(--border-color); border-radius: var(--radius); padding: 1rem; margin-bottom: 0.8rem; background: #ffffff;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.4rem;">
            <div>
              <strong style="font-size: 1rem; color: var(--primary);">${r.required_blood_group} Blood Required (${r.required_units} Unit${r.required_units > 1 ? 's' : ''})</strong>
              <div style="font-size: 0.85rem; color: var(--text-muted);">
                Patient: <strong>${r.patient_name}</strong> &bull; Urgency: <span class="badge badge-open">${r.urgency}</span>
              </div>
            </div>
            <span class="badge badge-${r.response_status.toLowerCase()}">${r.response_status}</span>
          </div>

          <div style="font-size: 0.88rem; margin: 0.4rem 0;">
            &#127973; <strong>Hospital:</strong> ${r.hospital_name} (${r.hospital_location})
          </div>

          ${r.response_message ? `
            <div style="font-size: 0.82rem; background: #f7fafc; padding: 0.4rem 0.6rem; border-radius: 4px; margin-top: 0.3rem;">
              <em>Note:</em> "${r.response_message}"
            </div>
          ` : ''}

          ${r.response_status === 'PENDING' ? `
            <div style="display: flex; gap: 0.6rem; margin-top: 0.8rem;">
              <button class="btn btn-success btn-sm" onclick="openResponseModal(${r.response_id}, 'accept', '${r.hospital_name}')">
                &#10004; Accept Request
              </button>
              <button class="btn btn-danger btn-sm" onclick="openResponseModal(${r.response_id}, 'reject', '${r.hospital_name}')">
                &#10006; Decline
              </button>
            </div>
          ` : ''}
        </div>
      `).join('');
    }
  } catch (e) {
    loading.textContent = 'Failed to load requests.';
  }
}

function openResponseModal(responseId, action, hospital) {
  activeResponseId = responseId;
  activeAction = action;

  const modal = document.getElementById('responseModal');
  const title = document.getElementById('modalTitle');
  const sub = document.getElementById('modalSub');
  const actionBtn = document.getElementById('modalActionBtn');
  const msgInput = document.getElementById('modalMessage');

  msgInput.value = '';
  if (action === 'accept') {
    title.textContent = 'Accept Blood Donation Request';
    sub.textContent = `You are accepting to donate blood at ${hospital}. Authorized medical staff will perform final cross-matching.`;
    actionBtn.className = 'btn btn-success';
    actionBtn.textContent = 'Confirm Acceptance';
  } else {
    title.textContent = 'Decline Donation Request';
    sub.textContent = `You are declining this request at ${hospital}. Patient will be able to contact other matching donors.`;
    actionBtn.className = 'btn btn-danger';
    actionBtn.textContent = 'Confirm Decline';
  }

  modal.style.display = 'flex';
}

function closeModal() {
  document.getElementById('responseModal').style.display = 'none';
  activeResponseId = null;
  activeAction = null;
}

async function submitModalResponse() {
  if (!activeResponseId || !activeAction) return;

  const msg = document.getElementById('modalMessage').value;
  const btn = document.getElementById('modalActionBtn');
  btn.disabled = true;

  try {
    const endpoint = `/api/donor/requests/${activeResponseId}/${activeAction}`;
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const json = await res.json();

    if (res.ok && json.success) {
      showToast(json.message || 'Response recorded!', 'success');
      closeModal();
      await loadDonorRequests();
    } else {
      showToast(json.error || 'Failed to submit response', 'danger');
    }
  } catch (err) {
    showToast('Network error submitting response', 'danger');
  } finally {
    btn.disabled = false;
  }
}
