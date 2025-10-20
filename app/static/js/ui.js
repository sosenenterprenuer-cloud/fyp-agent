// UI Helper Functions for Flask App

// Mobile navigation toggle
function toggleMobileNav() {
  const nav = document.querySelector('.nav');
  if (nav) {
    nav.classList.toggle('mobile-open');
  }
}

// Progress bar update for quiz
function updateProgressBar(percentage) {
  const progressBar = document.querySelector('.progress > span');
  if (progressBar) {
    progressBar.style.width = percentage + '%';
  }
}

// Star rating functionality
function initStarRating() {
  const starContainers = document.querySelectorAll('.stars');
  
  starContainers.forEach(container => {
    const labels = container.querySelectorAll('label');
    const inputs = container.querySelectorAll('input[type="radio"]');
    
    labels.forEach((label, index) => {
      label.addEventListener('click', () => {
        // Clear all selections
        inputs.forEach(input => input.checked = false);
        
        // Check the clicked star and all previous stars
        for (let i = 0; i <= index; i++) {
          if (inputs[i]) {
            inputs[i].checked = true;
          }
        }
      });
    });
  });
}

// Initialize all UI components when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  initStarRating();
  
  // Add mobile nav toggle button if on small screen
  if (window.innerWidth <= 768) {
    const nav = document.querySelector('.nav');
    if (nav && !document.querySelector('.mobile-nav-toggle')) {
      const toggle = document.createElement('button');
      toggle.className = 'mobile-nav-toggle';
      toggle.innerHTML = '☰';
      toggle.onclick = toggleMobileNav;
      
      const navContainer = document.querySelector('.nav').parentElement;
      navContainer.insertBefore(toggle, nav);
    }
  }
});

// Export functions for use in other scripts
window.UI = {
  toggleMobileNav,
  updateProgressBar,
  initStarRating
};
