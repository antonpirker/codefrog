
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

    let updateStateOfAffairs = function(data) {
        window.project = data;

        let ids = ['complexity', 'issue-age', 'pr-age']
        let trendValues = [
            data['state_of_affairs']['complexity_change'].toFixed(1),
            data['state_of_affairs']['issue_age_change'].toFixed(1),
            data['state_of_affairs']['pr_age_change'].toFixed(1)
        ]
        let values = [
            0,
            data['state_of_affairs']['issue_age'].toFixed(1),
            data['state_of_affairs']['pr_age'].toFixed(1)
        ]

        for(let i in ids) {
            let valueElement = document.querySelector('#' + ids[i] + ' span')
            let trendElement = document.querySelector('#' + ids[i] + '-trend')
            let caretElement = document.querySelector('#' + ids[i] + '-trend i')
            let trendValueElement = document.querySelector('#' + ids[i] + '-trend span')

            valueElement.innerHTML = values[i]

            trendElement.classList.remove('red')
            trendElement.classList.remove('green')

            caretElement.classList.remove('fa-caret-up')
            caretElement.classList.remove('fa-caret-down')

            trendValueElement.innerHTML = trendValues[i]
            if (trendValues[i] <= 0.01) {
                trendElement.classList.add('green')
                caretElement.classList.add('fa-caret-down')
            } else {
                trendElement.classList.add('red')
                caretElement.classList.add('fa-caret-up')
            }
        }
    };

    let projectUrl = 'http://localhost:8000/api-internal/projects/' + window.projectId + '/';
    fetch(projectUrl)
        .then(response => response.json())
        .then(updateStateOfAffairs);

    let updateProjectMetrics = function(data) {
        window.projectMetrics = data['results']; // TODO: fetch all pages of metrics!!!!
    }

    let projectMetricsUrl = 'http://localhost:8000/api-internal/projects/' + window.projectId + '/metrics/';
    fetch(projectMetricsUrl)
        .then(response => response.json())
        .then(updateProjectMetrics);

});
