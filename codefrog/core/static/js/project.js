
document.addEventListener("DOMContentLoaded", () => {
    let buttonDown = document.querySelector('#log-history-arrow-button-down');
    buttonDown.style.display = 'inline-block';

    let el = document.querySelector('#toggle-log-history');
    el.addEventListener('click', (e) => {
        let logHistory = document.querySelector('#log-history');
        let buttonDown = document.querySelector('#log-history-arrow-button-down');
        let buttonUp = document.querySelector('#log-history-arrow-button-up');
        let isVisible = logHistory.style.display === 'block';
        if(isVisible) {
            buttonDown.style.display = 'inline-block';
            buttonUp.style.display = null;

            logHistory.style.display = null;
        } else {
            buttonDown.style.display = null;
            buttonUp.style.display = 'inline-block';

            logHistory.style.display = 'block';
        }
    })
});
