/**
 * HEMONEXAS Auth Client
 */

function initLoginForm() {
  const form = document.getElementById('loginForm');
  const errorBox = document.getElementById('loginError');
  const submitBtn = document.getElementById('submitBtn');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Authenticating...';

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      const json = await res.json();

      if (res.ok && json.success) {
        showToast('Login successful! Redirecting...', 'success');
        const role = json.user.role;
        setTimeout(() => {
          if (role === 'donor') window.location.href = '/donor/dashboard';
          else if (role === 'patient') window.location.href = '/patient/dashboard';
          else if (role === 'admin') window.location.href = '/admin/dashboard';
          else window.location.href = '/';
        }, 600);
      } else {
        errorBox.textContent = json.error || 'Invalid credentials.';
        errorBox.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Sign In';
      }
    } catch (err) {
      errorBox.textContent = 'Network error connecting to HEMONEXAS server.';
      errorBox.style.display = 'block';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Sign In';
    }
  });
}

function initRegisterForm() {
  const form = document.getElementById('registerForm');
  const errorBox = document.getElementById('registerError');
  const submitBtn = document.getElementById('regSubmitBtn');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating Account...';

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Map patient phone/location if present
    if (data.role === 'patient') {
      if (data.p_phone) data.phone = data.p_phone;
      if (data.p_location) data.location = data.p_location;
    }

    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      const json = await res.json();

      if (res.ok && json.success) {
        showToast('Account created successfully!', 'success');
        const role = json.user.role;
        setTimeout(() => {
          if (role === 'donor') window.location.href = '/donor/dashboard';
          else if (role === 'patient') window.location.href = '/patient/dashboard';
          else window.location.href = '/';
        }, 700);
      } else {
        errorBox.textContent = json.error || 'Registration failed. Please check inputs.';
        errorBox.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Account';
      }
    } catch (err) {
      errorBox.textContent = 'Network error during registration.';
      errorBox.style.display = 'block';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Create Account';
    }
  });
}
