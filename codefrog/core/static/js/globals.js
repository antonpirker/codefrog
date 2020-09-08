
const link_color = '#FFAC33';
    const color_palette = ['#DD0F7E', '#009BBE', '#A8DA00', '#F2E205', '#EE5A02'];

window.chartColors = [
    'rgb(255, 99, 132)',
    'rgb(255, 159, 64)',
    'rgb(255, 205, 86)',
    'rgb(75, 192, 192)',
    'rgb(54, 162, 235)',
    'rgb(153, 102, 255)',
    'rgb(201, 203, 207)'
];

window.usedColors = [];

window.labelColors = {};



function parseQuery(queryString) {
    var query = {};
    var pairs = (queryString[0] === '?' ? queryString.substr(1) : queryString).split('&');
    for (var i = 0; i < pairs.length; i++) {
        var pair = pairs[i].split('=');
        query[decodeURIComponent(pair[0])] = decodeURIComponent(pair[1] || '');
    }
    return query;
}

function getDateRange() {
    // Default date range
    const dateRange = {
        'date_from': moment().subtract(14, 'days'),
        'date_to': moment()
    };

    // Check if we have a range defined in the window object
    if (window.projectDateFrom) {
        dateRange['date_from'] = window.projectDateFrom;
    }
    if (window.projectDateTo) {
        dateRange['date_to'] = window.projectDateTo;
    }

    // Check if there is a range defined in the URL query string
    // this overrides everything
    const urlParams = parseQuery(window.location.search);
    if ('date_to' in urlParams) {
        dateRange['date_to'] = moment(urlParams['date_to']);
    }
    if ('date_from' in urlParams) {
        dateRange['date_from'] = moment(urlParams['date_from']);
    }

    // Do not allow ranges in the future.
    if (dateRange['date_to'].isAfter()) {
        dateRange['date_to'] = moment()
    }

    return dateRange
}