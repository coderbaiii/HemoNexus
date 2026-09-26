/**
 * HemoNexus Operations Dashboard Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  if (!document.getElementById('dashboardRoot')) return;

  initDashboardData();
  initInventoryVisuals();
});

const initDashboardData = () => {
  const donors = HemoStore.getDonors();
  const requests = HemoStore.getRequests();

  // Metrics
  const availableDonors = donors.filter(d => d.status === 'available').length;
  const activeRequests = requests.filter(r => r.status !== 'fulfilled').length;
  const criticalRequests = requests.filter(r => r.urgency === 'critical' && r.status !== 'fulfilled').length;
  const fulfilledCount = requests.filter(r => r.status === 'fulfilled').length;

  const countDonorsEl = document.getElementById('statAvailableDonors');
  const countRequestsEl = document.getElementById('statActiveRequests');
  const countCriticalEl = document.getElementById('statCriticalRequests');
  const countFulfilledEl = document.getElementById('statFulfilled');

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

  animateValue(countDonorsEl, availableDonors);
  animateValue(countRequestsEl, activeRequests);
  animateValue(countCriticalEl, criticalRequests);
  animateValue(countFulfilledEl, fulfilledCount);
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
