// document.addEventListener("DOMContentLoaded", function () {
//     const loginForm = document.getElementById('loginForm');
//     if (loginForm) {
//         loginForm.addEventListener('submit', async function (e) {
//             e.preventDefault();
//             await handleLogin();
//         });
//     } else {
//         console.error("Login form not found!");
//     }
// });

// async function handleLogin() {
//     const email = document.getElementById('email').value;
//     const password = document.getElementById('password').value;
//     const loginUrl = '/api/auth/login/';

//     try {
//         const response = await fetch(loginUrl, {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//                 'X-CSRFToken': getCSRFToken(),  // Include CSRF token
//             },
//             body: JSON.stringify({ email, password }),
//             credentials: 'include',  // Include cookies in the request
//         });

//         const data = await response.json();
//         console.log("Login Response:", data);

//         if (response.ok) {
//             // ✅ Test API request to fetch user profile
//             const profileResponse = await fetch('/api/users/me/', {
//                 method: 'GET',
//                 headers: {
//                 'Authorization': `Bearer ${data.access}`,  // Include access token
//             },
//                 credentials: 'include',  // Include cookies in the request
//             });

//             if (profileResponse.ok) {
//                 const profileData = await profileResponse.json();
//                 console.log("User Profile:", profileData);
//                 alert('Login successful! Redirecting to dashboard...');
//                 window.location.replace("/login-home/");
//             } else {
//                 console.error('Failed to fetch profile:', profileResponse.status, profileResponse.statusText);
//                 alert("Login failed. Could not fetch profile.");
//             }
//         } else {
//             alert(data.detail || 'Login failed. Please check your credentials.');
//         }
//     } catch (error) {
//         console.error('Login error:', error);
//         alert('An error occurred. Please try again.');
//     }
// }

// // Retrieve CSRF token
// function getCSRFToken() {
//     let cookieValue = null;
//     if (document.cookie) {
//         const cookies = document.cookie.split(';');
//         for (let cookie of cookies) {
//             cookie = cookie.trim();
//             if (cookie.startsWith('csrftoken=')) {
//                 return cookie.substring('csrftoken='.length);
//             }
//         }
//     }
//     return cookieValue;
// }


document.addEventListener("DOMContentLoaded", function () {
    const googleLoginButton = document.getElementById('googleLoginButton');  // No # in getElementById
    if (googleLoginButton) {
        googleLoginButton.addEventListener('click', loginWithGoogle);
    } else {
        console.error("Google login button not found!");
    }
});

function loginWithGoogle() {
    let button = document.getElementById('googleLoginButton');  // Ensure button is re-fetched
    if (!button) {
        console.error("Google login button not found during login attempt!");
        return;
    }

    try {
        button.disabled = true;
        button.innerHTML = 'Redirecting...';
        window.location.href = '/accounts/google/login/';
    } catch (error) {
        console.error('Google auth redirect failed:', error);
        alert('Failed to start Google authentication. Please try again.');
        button.disabled = false;
        button.innerHTML = 'Continue with Google';
    }
}

