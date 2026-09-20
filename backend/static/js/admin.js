/**
 * HEMONEXAS Admin Dashboard Client
 */

async function initAdminDashboard() {
  await loadAdminStats();
  await loadAdminDonors();
}

async function loadAdminStats() {
  try {
    const res = await fetch('/api/admin/stats');
    const json = await res.json();
    if (res.ok && json.success) {
      const s = json.stats;
      document.getElementById('statTotalDonors').textContent = s.total_donors;
      document.getElementById('statActiveDonors').textContent = s.active_donors;
      document.getElementById('statDueDonors').textContent = s.verification_due_donors;
      document.getElementById('statInactiveDonors').textContent = s.inactive_donors;
    }
  } catch (e) {
    console.error('Failed to load admin stats', e);
  }
}

function switchTab(tabName) {
  document.querySelectorAll('.admin-tab').forEach(b => b.classList.remove('active'));
  ['tabDonors', 'tabRequests', 'tabResponses', 'tabUsers'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });

  if (tabName === 'donors') {
    document.getElementById('tabDonors').style.display = 'block';
    loadAdminDonors();
  } else if (tabName === 'requests') {
    document.getElementById('tabRequests').style.display = 'block';
    loadAdminRequests();
  } else if (tabName === 'responses') {
    document.getElementById('tabResponses').style.display = 'block';
    loadAdminResponses();
  } else if (tabName === 'users') {
    document.getElementById('tabUsers').style.display = 'block';
    loadAdminUsers();
  }
}

async function runVerificationSweep() {
  const btn = document.getElementById('runSweepBtn');
  btn.disabled = true;
  btn.textContent = 'Running Sweep...';

  try {
    const res = await fetch('/api/admin/verify-check', { method: 'POST' });
    const json = await res.json();

    if (res.ok && json.success) {
      showToast(json.message, 'success');
      await loadAdminStats();
      await loadAdminDonors();
    } else {
      showToast(json.error || 'Sweep failed', 'danger');
    }
  } catch (e) {
    showToast('Network error during verification sweep', 'danger');
  } finally {
    btn.disabled = false;
    btn.textContent = '⏱ Run 6-Month Verification Sweep';
  }
}

async function loadAdminDonors() {
  const filter = document.getElementById('donorStatusFilter').value;
  const tbody = document.getElementById('donorsTableBody');

  try {
    let url = '/api/admin/donors';
    if (filter) url += `?status=${filter}`;

    const res = await fetch(url);
    const json = await res.json();

    if (res.ok && json.success) {
      const donors = json.donors || [];
      if (donors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:var(--text-muted);">No donors found.</td></tr>';
        return;
      }

      tbody.innerHTML = donors.map(d => `
        <tr>
          <td><strong>#${d.id}</strong></td>
          <td>
            <strong>${d.full_name}</strong><br>
            <small style="color:var(--text-muted);">${d.email}</small>
          </td>
          <td><span class="badge badge-active">${d.blood_group}</span></td>
          <td>${d.phone || 'N/A'}</td>
          <td>${d.location}</td>
          <td>${d.availability.replace('_', ' ')} (${d.maximum_travel_distance} km)</td>
          <td><span class="badge badge-${d.profile_status.toLowerCase()}">${d.profile_status.replace('_', ' ')}</span></td>
          <td><small>${d.next_verification_date ? d.next_verification_date.slice(0, 10) : 'N/A'}</small></td>
          <td>
            <select class="form-control" style="font-size:0.8rem; padding:0.25rem 0.4rem; width:auto;" onchange="overrideDonorStatus(${d.id}, this.value)">
              <option value="">Override...</option>
              <option value="ACTIVE" ${d.profile_status === 'ACTIVE' ? 'disabled' : ''}>Set ACTIVE</option>
              <option value="VERIFICATION_DUE" ${d.profile_status === 'VERIFICATION_DUE' ? 'disabled' : ''}>Set DUE</option>
              <option value="INACTIVE" ${d.profile_status === 'INACTIVE' ? 'disabled' : ''}>Set INACTIVE</option>
            </select>
          </td>
        </tr>
      `).join('');
    }
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="9" style="color:red; text-align:center;">Failed to load donors.</td></tr>';
  }
}

async function overrideDonorStatus(donorId, newStatus) {
  if (!newStatus) return;
  if (!confirm(`Are you sure you want to change donor #${donorId} status to ${newStatus}?`)) return;

  try {
    const res = await fetch(`/api/admin/donors/${donorId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    const json = await res.json();

    if (res.ok && json.success) {
      showToast(`Donor status changed to ${newStatus}`, 'success');
      await loadAdminStats();
      await loadAdminDonors();
    } else {
      showToast(json.error || 'Failed to update status', 'danger');
    }
  } catch (e) {
    showToast('Network error updating donor status', 'danger');
  }
}

async function loadAdminRequests() {
  const tbody = document.getElementById('requestsTableBody');
  try {
    const res = await fetch('/api/admin/blood-requests');
    const json = await res.json();

    if (res.ok && json.success) {
      const list = json.requests || [];
      if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">No blood requests found.</td></tr>';
        return;
      }

      tbody.innerHTML = list.map(r => `
        <tr>
          <td><strong>#${r.id}</strong></td>
          <td><strong>${r.patient_name}</strong><br><small style="color:var(--text-muted);">${r.patient_email}</small></td>
          <td><span class="badge badge-active">${r.required_blood_group}</span></td>
          <td>${r.required_units}</td>
          <td>${r.hospital_name} (${r.location})</td>
          <td><span class="badge badge-open">${r.urgency}</span></td>
          <td><span class="badge badge-${r.request_status.toLowerCase()}">${r.request_status}</span></td>
          <td><small>${r.created_at ? r.created_at.slice(0, 16).replace('T', ' ') : 'N/A'}</small></td>
        </tr>
      `).join('');
    }
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="8" style="color:red; text-align:center;">Failed to load requests.</td></tr>';
  }
}

async function loadAdminResponses() {
  const tbody = document.getElementById('responsesTableBody');
  try {
    const res = await fetch('/api/admin/responses');
    const json = await res.json();

    if (res.ok && json.success) {
      const list = json.responses || [];
      if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">No response records found.</td></tr>';
        return;
      }

      tbody.innerHTML = list.map(r => `
        <tr>
          <td><strong>#${r.id}</strong></td>
          <td>Req #${r.blood_request_id} (${r.required_blood_group})</td>
          <td>${r.hospital_name}</td>
          <td>${r.patient_name}</td>
          <td><strong>${r.donor_name}</strong></td>
          <td><span class="badge badge-${r.status.toLowerCase()}">${r.status}</span></td>
          <td><small>${r.message || 'None'}</small></td>
          <td><small>${r.updated_at ? r.updated_at.slice(0, 16).replace('T', ' ') : 'N/A'}</small></td>
        </tr>
      `).join('');
    }
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="8" style="color:red; text-align:center;">Failed to load responses.</td></tr>';
  }
}

async function loadAdminUsers() {
  const tbody = document.getElementById('usersTableBody');
  try {
    const res = await fetch('/api/admin/users');
    const json = await res.json();

    if (res.ok && json.success) {
      const list = json.users || [];
      tbody.innerHTML = list.map(u => `
        <tr>
          <td><strong>#${u.id}</strong></td>
          <td><strong>${u.full_name}</strong></td>
          <td>${u.email}</td>
          <td><span class="badge badge-open">${u.role}</span></td>
          <td><small>${u.created_at ? u.created_at.slice(0, 10) : 'N/A'}</small></td>
        </tr>
      `).join('');
    }
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:red; text-align:center;">Failed to load users.</td></tr>';
  }
}
