/**
 * HEMONEXAS In-App Notification Manager
 */
async function loadNotifications() {
  const badge = document.getElementById("notifBadge");
  const list = document.getElementById("notifList");
  if (!badge || !list) return;

  try {
    const res = await fetch("/api/notifications");
    if (!res.ok) return;
    const data = await res.json();
    if (!data.success) return;

    const unread = data.unread_count || 0;
    if (unread > 0) {
      badge.textContent = unread > 99 ? "99+" : unread;
      badge.style.display = "inline-block";
    } else {
      badge.style.display = "none";
    }

    list.innerHTML = "";
    const notifs = data.notifications || [];
    if (notifs.length === 0) {
      list.innerHTML = `<div style="padding: 1rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">No notifications.</div>`;
      return;
    }

    notifs.slice(0, 8).forEach(n => {
      const item = document.createElement("a");
      item.href = n.link || "#";
      item.className = `notif-item ${n.is_read ? 'read' : 'unread'}`;
      item.innerHTML = `
        <div style="font-weight: 600; font-size: 0.85rem; color: var(--text-main);">${n.title}</div>
        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">${n.message}</div>
        <div style="font-size: 0.72rem; color: #a0aec0; margin-top: 4px;">${n.created_at ? n.created_at.substring(0, 16).replace('T', ' ') : ''}</div>
      `;
      list.appendChild(item);
    });
  } catch (e) {
    // Silently ignore network failures for background notification polling
  }
}

function initNotifications() {
  const toggleBtn = document.getElementById("notifToggleBtn");
  const dropdown = document.getElementById("notifDropdown");
  const markAllBtn = document.getElementById("notifMarkAllBtn");

  if (toggleBtn && dropdown) {
    toggleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("active");
    });

    document.addEventListener("click", (e) => {
      if (!dropdown.contains(e.target) && e.target !== toggleBtn) {
        dropdown.classList.remove("active");
      }
    });
  }

  if (markAllBtn) {
    markAllBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      try {
        await fetch("/api/notifications/read-all", { method: "POST" });
        loadNotifications();
      } catch (err) {}
    });
  }

  loadNotifications();
}

document.addEventListener("DOMContentLoaded", initNotifications);
