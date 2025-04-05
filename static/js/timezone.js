/**
 * Timezone handling for the Q&A application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Format all timestamps to local timezone
    formatTimestamps();
});

/**
 * Format all timestamps on the page to the user's local timezone
 */
function formatTimestamps() {
    // Format question timestamps
    const questionTimes = document.querySelectorAll('.question-time');
    questionTimes.forEach(formatTimeElement);
    
    // Format answer timestamps
    const answerTimes = document.querySelectorAll('.answer-time');
    answerTimes.forEach(formatTimeElement);
}

/**
 * Format a single time element from UTC to local timezone with a nice format
 * @param {HTMLElement} timeElement - The element containing the timestamp
 */
function formatTimeElement(timeElement) {
    const timestamp = timeElement.getAttribute('data-timestamp');
    if (!timestamp) return;
    
    try {
        // Parse the timestamp (assuming it's in UTC)
        const date = new Date(timestamp + 'Z'); // Append Z to treat as UTC
        
        // Check if the date is valid
        if (isNaN(date.getTime())) {
            console.error('Invalid date:', timestamp);
            return;
        }
        
        // Format the date based on how recent it is
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        let formattedDate;
        
        if (diffDays === 0) {
            // Today
            formattedDate = 'Today at ' + formatTime(date);
        } else if (diffDays === 1) {
            // Yesterday
            formattedDate = 'Yesterday at ' + formatTime(date);
        } else if (diffDays < 7) {
            // This week
            formattedDate = date.toLocaleDateString(undefined, { weekday: 'long' }) + 
                           ' at ' + formatTime(date);
        } else {
            // Older than a week
            formattedDate = date.toLocaleDateString(undefined, { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric'
            }) + ' at ' + formatTime(date);
        }
        
        // Update the element's displayed time
        const timeChild = timeElement.querySelector('time');
        if (timeChild) {
            timeChild.textContent = formattedDate;
        } else {
            timeElement.textContent = formattedDate;
        }
    } catch (error) {
        console.error('Error formatting time:', error);
    }
}

/**
 * Format the time part of a date in 24-hour format
 * @param {Date} date - The date object to format
 * @returns {string} Formatted time string
 */
function formatTime(date) {
    return date.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}