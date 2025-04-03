/**
 * JavaScript functions for the Q&A application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the nickname field functionality
    initNicknameField();
});

/**
 * Initialize the nickname field with focus/blur behavior
 */
function initNicknameField() {
    const nicknameField = document.getElementById('nickname-field');
    
    if (nicknameField) {
        // When the field gets focus and contains the default value
        nicknameField.addEventListener('focus', function() {
            if (this.value === 'anon') {
                this.value = '';
                this.classList.remove('has-text-grey-light');
            }
        });
        
        // When the field loses focus and is empty
        nicknameField.addEventListener('blur', function() {
            if (this.value === '') {
                this.value = 'anon';
                this.classList.add('has-text-grey-light');
            }
        });
    }
}

/**
 * Submit the question form via AJAX (example for future implementation)
 * @param {Event} event - The form submit event
 */
function submitQuestionForm(event) {
    // Prevent the default form submission
    event.preventDefault();
    
    // Get form data
    const form = event.target;
    const formData = new FormData(form);
    
    // Example AJAX submission (commented out for now)
    /*
    fetch('/submit-question', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            showNotification('Your question has been submitted!', 'is-success');
            // Reset the form
            form.reset();
            // Re-initialize the nickname field
            initNicknameField();
        } else {
            // Show error message
            showNotification('Error submitting your question. Please try again.', 'is-danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred. Please try again later.', 'is-danger');
    });
    */
}

/**
 * Display a notification message to the user
 * @param {string} message - The message to display
 * @param {string} type - The Bulma notification type (is-info, is-success, is-warning, is-danger)
 */
function showNotification(message, type = 'is-info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    // Add delete button
    const deleteButton = document.createElement('button');
    deleteButton.className = 'delete';
    deleteButton.addEventListener('click', function() {
        notification.remove();
    });
    
    // Add message text
    const messageText = document.createTextNode(message);
    
    // Assemble and add to page
    notification.appendChild(deleteButton);
    notification.appendChild(messageText);
    
    // Add to page (at the top of the main content)
    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(notification, mainContent.firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}