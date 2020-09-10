
const link_color = '#FFAC33'; // not used in JS, only here for reference

let colorGradient = [ // from: https://learnui.design/tools/data-color-picker.html
    '#0070a3',
    '#8171c2',
    '#e263ab',
    '#ff6e69',
    '#ffa600',
];

// OLD Chart colors
//const chartColors = ['#DD0F7E', '#0082A5', '#99cddb', '#82a500']; // https://www.color-hex.com/color/0082a5

let COLOR_COMPLEXITY = 0

let COLOR_METRIC1 = 1
let COLOR_METRIC1_ALT = 2

let COLOR_METRIC2 = 3
let COLOR_METRIC2_ALT = 4

let COLOR_FILE_CHANGES = 5


let colorsLufthansa = [
    '#ddd',
    'hsla(230, 96, 12, 1)',
    'hsla(230, 8, 41, 1)',
    'hsla(22, 96, 48, 1)',
    'hsla(39, 96, 48, 1)',
    'hsla(28, 96, 48, 1)',
];
let colorsUsingWeather = [
    '#ddd',
    'hsla(146, 96, 28, 1)',
    'hsla(118, 31, 63, 1)',
    'hsla(11, 84, 68, 1)',
    'hsla(22, 84, 68, 1)',
    'hsla(213, 96, 33, 1)',
];
let colorsDataVizCollection = [
    '#ddd',
    'hsla(185, 60, 28, 1)',
    'hsla(163, 60, 34, 1)',
    'hsla(5, 85, 64, 1)',
    'hsla(33, 84, 68, 1)',
    'hsla(39, 84, 67, 1)',
];
let colorsBoat = [
    '#ddd',
    'hsla(354, 87, 58, 1)',
    'hsla(354, 82, 71, 1)',
    'hsla(174, 96, 28, 1)',
    'hsla(39, 63, 59, 1)',
    'hsla(33, 86, 63, 1)',
];
let colorsPredictiveAnalytics = [
    '#ddd',
    'hsla(191, 68, 44, 1)',
    'hsla(50, 34, 48, 1)',
    'hsla(16, 96, 28, 1)',
    'hsla(11, 94, 48, 1)',
    'hsla(22, 89, 51, 1)',
];

const chartColors = colorsDataVizCollection;


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