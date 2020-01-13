/**
 * Counts an given action.
 *
 * This is for usage tracking. The timestamp and project as well as the user the action is counted for
 * are retrieved from the DOM or the session.
 *
 * @param action
 */
function count(action) {
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    let projectId = document.querySelector('[name=projectid]').value;

    let dateObj = new Date();
    let now = dateObj.toISOString();

    fetch('/count', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json;charset=utf-8',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            'project_id': projectId,
            'timestamp': now,
            'action': action
        })
    });
}
