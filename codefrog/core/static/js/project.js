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

        return fetch(url)
            .then(response => response.json())
            .then(data => {
                return data;
            });
    }

    console.log(`Loading source-status ... ` + new Date());
    let sourceStatusUrl = location.origin + '/api-internal/projects/' + projectId + '/source-status/';
    fetchData(sourceStatusUrl).then(resp => {
            window.projectSourceStatus = resp[0];

            console.log(`Everything loaded from source-status ` + new Date());

            const event = new Event('source-status-loaded');
            document.dispatchEvent(event);
        });

    loadPaginatedResource(projectId, 'file-changes', 'projectFileChanges');


    const evolutionPromises = [];
    console.log(`Loading project... ` + new Date());
    let projectUrl = location.origin + '/api-internal/projects/' + projectId + '/';
    let promise1 = fetchData(projectUrl).then(resp => {
            window.project = resp;

            console.log(`Everything loaded from project ` + new Date());

            const event = new Event('project-loaded');
            document.dispatchEvent(event);
        });
    let promise2 = loadPaginatedResource(projectId, 'metrics', 'projectMetrics');
    let promise3 = loadPaginatedResource(projectId, 'releases', 'projectReleases');

    Promise.all([promise1, promise2, promise3]).then(response => {
        console.log("Everything for evolution diagramm loaded!");
        const event = new Event('evolution-loaded');
        document.dispatchEvent(event);
    });
}


let loadPaginatedResource = function(projectId, action, propertyName) {
    console.log(`Loading ${action} ... ` + new Date());

    let params = getDateRange();
    params['date_from'] = params['date_from'].format('YYYY-MM-DD');
    params['date_to'] = params['date_to'].format('YYYY-MM-DD');
    const qs = (new URLSearchParams(params)).toString();

    let url = location.origin + '/api-internal/projects/' + projectId + '/' + action+ '/';

    let numPages = 0;
    return fetch(url + '?' + qs)
        .then(response => response.json())
        .then(data => {
            // Fetch all pages
            const apiPromises = [];
            numPages = data['num_pages'];
            console.log(`${action}: There are ${numPages} pages to load.`);
            for (let page=1; page<=numPages; page++) {
                params['page'] = page;
                const qs = (new URLSearchParams(params)).toString();
                let pageUrl = url + '?' + qs;

                let promise = fetch(pageUrl)
                    .then(response => response.json())
                    .then(data => {
                        return data;
                    });

                apiPromises.push(promise);
            }

            // Wait until loading of all pages is done.
            let allPromise = Promise.all(apiPromises)
                .then(responses => {
                    const processedResponses = [];
                    responses.map(data => {
                        processedResponses.push(data);
                    });

                    // Save the results of all pages into window object
                    window[propertyName] = [];
                    for (let i in processedResponses) {
                        window[propertyName] = window[propertyName].concat(processedResponses[i]['results']);
                    }
                    console.log(`Everything loaded from ${action} ` + new Date());

                    // Tell everyone that we are done loading stuff
                    const event = new Event(action + '-loaded');
                    document.dispatchEvent(event);
                });
            return allPromise;
        });
}


/**
 * When project data is loaded, update UI.
 */
document.addEventListener('evolution-loaded', function (e) {
    updateStateOfAffairs(window.project);
    createEvolutionOfIssuesDiagram(window.projectMetrics, window.projectReleases);
    createEvolutionOfPullRequestsDiagram(window.projectMetrics, window.projectReleases);
}, false);

document.addEventListener('file-changes-loaded', function (e) {
    createFileChurnDiagram(window.projectFileChanges);
}, false);

document.addEventListener('source-status-loaded', function (e) {
    createProblemAreasDiagram(window.projectSourceStatus);
}, false);


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
