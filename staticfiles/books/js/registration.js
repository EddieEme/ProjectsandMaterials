// Handle registration form submission
document.addEventListener("DOMContentLoaded", function () {
    document.querySelector("form").addEventListener("submit", async function (e) {
        e.preventDefault();

        // Get form values
        const firstName = document.getElementById('firstName').value.trim();
        const lastName = document.getElementById('lastName').value.trim();
        const email = document.getElementById('email').value.trim();
        const password1 = document.getElementById('password1').value;
        const password2 = document.getElementById('password2').value;

        // Basic validation
        if (!firstName || !lastName || !email || !password1 || !password2) {
            alert('Please fill in all fields');
            return;
        }

        if (password1 !== password2) {
            alert('Passwords do not match!');
            return;
        }

        const registrationUrl = '/api/auth/register/';  // Relative path

        try {
            const response = await fetch(registrationUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value, // CSRF token
                },
                credentials: 'include',  // Include cookies (e.g., CSRF token)
                body: JSON.stringify({
                    first_name: firstName,
                    last_name: lastName,
                    email: email,
                    password: password1,
                }),
            });

            const data = await response.json();

            if (response.ok) {
                alert('Registration successful! Please check your email for verification.');
                window.location.href = '/user_login/';  // Redirect to login page
            } else {
                // Detailed error handling
                let errorMessage = 'Registration failed: ';
                if (data.detail) {
                    errorMessage += data.detail;
                } else if (data.email) {
                    errorMessage += `Email: ${data.email.join(', ')}`;
                } else if (data.password) {
                    errorMessage += `Password: ${data.password.join(', ')}`;
                } else {
                    errorMessage += 'Please check your information and try again.';
                }
                alert(errorMessage);
            }
        } catch (error) {
            console.error('Registration error:', error);
            alert('An error occurred. Please try again.');
        }
    });
});