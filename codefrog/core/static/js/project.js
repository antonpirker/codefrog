
document.addEventListener("DOMContentLoaded", () => {
    let el = document.querySelector('#toggle-log-history');
    el.addEventListener('click', (e) => {
        let logHistory = document.querySelector('#log-history');
        let isVisible = logHistory.style.display === 'block';
        if(isVisible) {
            logHistory.style.display = null;
        } else {
            logHistory.style.display = 'block';
        }
    })
});
