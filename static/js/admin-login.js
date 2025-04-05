/**
 * Admin login functionality for the Q&A application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the admin login modal
    initAdminLoginModal();
});

/**
 * Initialize the admin login modal functionality
 */
function initAdminLoginModal() {
    const loginLink = document.getElementById('admin-login-link');
    const loginModal = document.getElementById('admin-login-modal');
    
    if (!loginLink || !loginModal) return;
    
    // Open modal when login link is clicked or redirect if already logged in
    loginLink.addEventListener('click', function(e) {
        e.preventDefault();
        
        // Check if admin is already logged in
        const isLoggedIn = loginLink.getAttribute('data-logged-in') === 'true';
        
        if (isLoggedIn) {
            // If already logged in, redirect to admin dashboard
            window.location.href = '/admin/dashboard';
        } else {
            // Otherwise show login modal
            loginModal.classList.add('is-active');
            
            // Focus on username field
            setTimeout(() => {
                const usernameField = loginModal.querySelector('input[name="username"]');
                if (usernameField) usernameField.focus();
            }, 100);
        }
    });
    
    // Close modal when close button or cancel button is clicked
    const closeButtons = loginModal.querySelectorAll('#close-login-modal, #cancel-login');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            loginModal.classList.remove('is-active');
            
            // Reset form
            const form = loginModal.querySelector('form');
            if (form) form.reset();
            
            // Hide error message if visible
            const errorMessage = loginModal.querySelector('#login-error');
            if (errorMessage) errorMessage.classList.add('is-hidden');
        });
    });
    
    // Handle form submission via AJAX
    const loginForm = document.getElementById('admin-login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            // Disable submit button during request
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Logging in...';
            
            // Send request
            fetch('/admin/login', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (response.redirected) {
                    // Successful login, redirect to the URL provided by the server
                    window.location.href = response.url;
                } else {
                    // Failed login, show error message
                    return response.text();
                }
            })
            .then(html => {
                if (html) {
                    // If we got HTML back, login failed
                    const errorMessage = loginModal.querySelector('#login-error');
                    if (errorMessage) errorMessage.classList.remove('is-hidden');
                    
                    // Reset submit button
                    submitButton.disabled = false;
                    submitButton.textContent = originalText;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                
                // Show generic error message
                const errorMessage = loginModal.querySelector('#login-error');
                if (errorMessage) {
                    errorMessage.textContent = 'An error occurred. Please try again.';
                    errorMessage.classList.remove('is-hidden');
                }
                
                // Reset submit button
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            });
        });
    }
    
    // Close error message when delete button is clicked
    const errorDeleteButton = loginModal.querySelector('#login-error .delete');
    if (errorDeleteButton) {
        errorDeleteButton.addEventListener('click', function() {
            const errorMessage = this.parentNode;
            errorMessage.classList.add('is-hidden');
        });
    }
}