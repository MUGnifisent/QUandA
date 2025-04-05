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
        
        // Get the current date in local timezone
        const now = new Date();
        
        // Compare date components instead of timestamp differences
        const isToday = isSameDay(now, date);
        const isYesterday = isYesterdayDate(now, date);
        
        let formattedDate;
        
        if (isToday) {
            // Today
            formattedDate = 'Today at ' + formatTime(date);
        } else if (isYesterday) {
            // Yesterday
            formattedDate = 'Yesterday at ' + formatTime(date);
        } else if (isThisWeek(now, date)) {
            // This week - show day name
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
 * Check if two dates are the same day in local time
 * @param {Date} date1 - First date
 * @param {Date} date2 - Second date
 * @returns {boolean} True if same day
 */
function isSameDay(date1, date2) {
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getDate() === date2.getDate();
}

/**
 * Check if date2 is yesterday compared to date1 in local time
 * @param {Date} date1 - The reference date (usually today)
 * @param {Date} date2 - The date to check
 * @returns {boolean} True if date2 is yesterday
 */
function isYesterdayDate(date1, date2) {
    // Create a copy of date1 and set it to yesterday
    const yesterday = new Date(date1);
    yesterday.setDate(date1.getDate() - 1);
    
    return yesterday.getFullYear() === date2.getFullYear() &&
           yesterday.getMonth() === date2.getMonth() &&
           yesterday.getDate() === date2.getDate();
}

/**
 * Check if date2 is in the same week as date1 in local time
 * @param {Date} date1 - The reference date (usually today)
 * @param {Date} date2 - The date to check
 * @returns {boolean} True if dates are in the same week
 */
function isThisWeek(date1, date2) {
    // If more than 7 days apart, definitely not same week
    const diffTime = Math.abs(date1 - date2);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays > 7) return false;
    
    // Get week start (Sunday or Monday depending on locale)
    const firstDay = date1.getDay();
    const date1Day = date1.getDate();
    
    // Calculate start of week for reference date (date1)
    const startOfWeek = new Date(date1);
    startOfWeek.setDate(date1Day - firstDay); // Set to beginning of week
    
    // Compare if date2 is after or equal to start of week and before or equal to end of week
    return date2 >= startOfWeek && date2 <= date1;
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