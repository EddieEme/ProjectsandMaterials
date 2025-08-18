 // Logout function
        async function handleLogout() {
            const logoutUrl = '/api/auth/logout/';  // Relative path to the logout endpoint

            // Get the CSRF token
            const csrfTokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
            if (!csrfTokenElement) {
                console.error('CSRF token not found!');
                alert('CSRF token missing. Please refresh the page and try again.');
                return;
            }

            const csrfToken = csrfTokenElement.value;

            try {
                const response = await fetch(logoutUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,  // Include CSRF token
                    },
                    credentials: 'include',  // Include cookies (e.g., CSRF token)
                });

                if (response.ok) {
                    alert('Logout successful! Redirecting to login page...');
                    window.location.href = "/";  // Redirect to home page
                } else {
                    const data = await response.json();
                    alert(data.detail || 'Logout failed. Please try again.');
                }
            } catch (error) {
                console.error('Logout error:', error);
                alert('An error occurred. Please try again.');
            }
        }

        // Attach logout function to the logout link
        document.addEventListener("DOMContentLoaded", function () {
            const logoutLink = document.getElementById('logoutLink');
            if (logoutLink) {
                logoutLink.addEventListener('click', function (e) {
                    e.preventDefault();  // Prevent default link behavior
                    handleLogout();     // Call the logout function
                });
            }
        });