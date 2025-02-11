document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            await handleLogin();
        });
    } else {
        console.error("Login form not found!");
    }
});

async function handleLogin() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const loginUrl = '/api/auth/login/';

    try {
        const response = await fetch(loginUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()  
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        console.log("Login Response:", data);

        if (response.ok && data.access) {
            sessionStorage.setItem('token', data.access);

            // ✅ Test API request with Authorization header
            const profileResponse = await fetch('/api/users/me/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${data.access}`
                }
            });

            const profileData = await profileResponse.json();
            
            if (profileResponse.ok) {
                console.log("User Profile:", profileData);
                alert('Login successful! Redirecting to dashboard...');
                window.location.replace("/login-home/");
            } else {
                alert("Login failed. Could not fetch profile.");
                sessionStorage.removeItem('token');
            }
        } else {
            alert(data.detail || 'Login failed. Please check your credentials.');
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('An error occurred. Please try again.');
    }
}

// Retrieve CSRF token
function getCSRFToken() {
    let cookieValue = null;
    if (document.cookie) {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith('csrftoken=')) {
                return cookie.substring('csrftoken='.length);
            }
        }
    }
    return cookieValue;
}
        // Placeholder functions for social login
        function loginWithGoogle() {
            alert('Redirecting to Google login...');
            // Replace with actual Google OAuth implementation
        }

        function loginWithFacebook() {
            alert('Redirecting to Facebook login...');
            // Replace with actual Facebook OAuth implementation
        }