/**
 * HEMONEXAS Interactive Search Page Controller
 * Invokes the 10-step requirement matching engine and renders sanitized donor cards.
 */
function initSearchPage() {
  const form = document.getElementById("searchDonorsForm");
  const loading = document.getElementById("searchLoading");
  const placeholder = document.getElementById("searchPlaceholder");
  const noResults = document.getElementById("noResultsMsg");
  const list = document.getElementById("searchResultsList");
  const countBadge = document.getElementById("resultsCountBadge");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    // UI state
    placeholder.style.display = "none";
    noResults.style.display = "none";
    list.style.display = "none";
    list.innerHTML = "";
    loading.style.display = "block";
    countBadge.style.display = "none";

    try {
      const res = await fetch("/api/search/donors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      loading.style.display = "none";

      if (!data.success) {
        showToast(data.error || "Search failed.", "error");
        placeholder.style.display = "block";
        return;
      }

      const results = data.results || [];
      countBadge.textContent = `${results.length} Matches`;
      countBadge.style.display = "inline-block";

      if (results.length === 0) {
        noResults.style.display = "block";
        return;
      }

      // Render cards
      list.style.display = "flex";
      results.forEach((d) => {
        const card = document.createElement("div");
        card.className = "card result-card";
        card.style.borderLeft = "4px solid var(--primary)";
        card.style.marginBottom = "0.8rem";

        const travelTimeHtml = d.estimated_travel_time !== null && d.estimated_travel_time !== undefined
          ? `&bull; <span style="color: var(--primary-dark); font-weight: 500;">~${d.estimated_travel_time} mins travel (estimated)</span>`
          : "";

        const scoreBadge = d.matching_score !== null && d.matching_score !== undefined
          ? `<div style="text-align: right;">
               <div style="font-size: 1.4rem; font-weight: 700; color: var(--primary);">${d.matching_score}%</div>
               <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Match Score</div>
             </div>`
          : "";

        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.8rem;">
            <div>
              <div style="display: flex; align-items: center; gap: 0.6rem;">
                <span class="badge badge-blood">${d.blood_group}</span>
                <h4 style="margin: 0; font-size: 1.15rem; color: var(--text-main);">#${d.rank} ${d.full_name}</h4>
                <span class="badge badge-active">&#10003; Active & Verified</span>
              </div>
              <div style="margin-top: 0.4rem; font-size: 0.88rem; color: var(--text-muted);">
                &#128205; ${d.masked_location} &bull; ~${d.approximate_distance_km} km away
                ${travelTimeHtml}
              </div>
            </div>
            ${scoreBadge}
          </div>

          <div class="grid-3" style="margin-top: 0.8rem; background: #f8fafc; padding: 0.6rem; border-radius: 6px; font-size: 0.84rem;">
            <div><strong>Schedule:</strong> ${d.availability_label || d.availability}</div>
            <div><strong>Max Travel:</strong> Up to ${d.maximum_travel_distance} km</div>
            <div><strong>Last Verified:</strong> ${d.last_verified_date ? d.last_verified_date.substring(0, 10) : 'Recent'}</div>
          </div>

          <div style="margin-top: 0.8rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
            <span style="font-size: 0.76rem; color: #718096; font-style: italic;">
              &#9888; ${d.medical_disclaimer}
            </span>
            <a href="/patient/dashboard" class="btn btn-primary btn-sm">&#128227; Send Request from Dashboard</a>
          </div>
        `;
        list.appendChild(card);
      });
    } catch (err) {
      loading.style.display = "none";
      placeholder.style.display = "block";
      showToast("Network error executing search.", "error");
    }
  });
}
