/**
 * Load all project related data from API
 * @param projectId
 */
let loadProject = function (projectId) {
    // Update date picker if there is a date range in the URL
    const params = getDateRange();
    const urlParams = parseQuery(window.location.search);
    const dateRangeDefinedInUrl = 'date_to' in urlParams || 'date_from' in urlParams
    if (dateRangeDefinedInUrl) {
        // Update date picker
        $('#reportrange span').html(params['date_from'].format('MMM D, YYYY') + ' - ' + params['date_to'].format('MMM D, YYYY'));
    }

    // Format to iso date format
    params['date_from'] = params['date_from'].format('YYYY-MM-DD');
    params['date_to'] = params['date_to'].format('YYYY-MM-DD');

    const qs = (new URLSearchParams(params)).toString();

    const fetchData = function (url) {
        url = url + '?' + qs;
        console.log('Fetching ' + url);

        return fetch(url)
            .then(response => response.json())
            .then(data => {
                return data;
            });
    }
    const handleProjectData = function (data) {
        window.project = data;
    }
    const handleMetricsData = function (data) {
        window.projectMetrics = data['results'];
    }
    const handleReleasesData = function (data) {
        window.projectReleases = data['results'];
    }
    const handleFileChangesData = function (data) {
        window.projectFileChanges = data['results'];
    }
    const handleSourceStatusData = function (data) {
        window.projectSourceStatus = data[0];
    }

    const urlsAndHandlers = [
        {
            url: location.origin + '/api-internal/projects/' + projectId + '/',
            handler: handleProjectData,
        }, {
            url: location.origin + '/api-internal/projects/' + projectId + '/metrics/',
            handler: handleMetricsData,
        }, {
            url: location.origin + '/api-internal/projects/' + projectId + '/releases/',
            handler: handleReleasesData,
        }, {
            url: location.origin + '/api-internal/projects/' + projectId + '/file-changes/',
            handler: handleFileChangesData,
        }, {
            url: location.origin + '/api-internal/projects/' + projectId + '/source-status/',
            handler: handleSourceStatusData,
        }
    ];

    // load data from all remote urls in parallel
    (async () => {
        const promises = urlsAndHandlers.map((urlAndHandler, index) => fetchData(urlAndHandler['url']));
        await Promise.all(promises).then(responses => {
            responses.map((response, index) => urlsAndHandlers[index]['handler'](response));
            console.log('All data of project loaded.');
            const event = new Event('projectLoaded');
            document.dispatchEvent(event);
        });
    })();
}


/**
 * Update the data in the "State of affairs" part of the project page
 * @param data
 */
let updateStateOfAffairs = function (data) {
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

    for (let i in ids) {
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


/**
 * When project data is loaded, update UI.
 */
document.addEventListener('projectLoaded', function (e) {
    updateStateOfAffairs(window.project);
    createEvolutionOfIssuesDiagram(window.projectMetrics, window.projectReleases);
    createEvolutionOfPullRequestsDiagram(window.projectMetrics, window.projectReleases);
    createFileChurnDiagram(window.projectFileChanges);
    createProblemAreasDiagram(window.projectSourceStatus);
}, false);


/**
 * When page is loaded, setup UI buttons.
 */
document.addEventListener("DOMContentLoaded", () => {
    let buttonDown = document.querySelector('#log-history-arrow-button-down');
    buttonDown.style.display = 'inline-block';

    let el = document.querySelector('#toggle-log-history');
    el.addEventListener('click', (e) => {
        let logHistory = document.querySelector('#log-history');
        let buttonDown = document.querySelector('#log-history-arrow-button-down');
        let buttonUp = document.querySelector('#log-history-arrow-button-up');
        let isVisible = logHistory.style.display === 'block';
        if (isVisible) {
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
