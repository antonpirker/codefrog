from django.test import TestCase
from django.test.client import RequestFactory

from connectors.github.views import authorization, hook, setup


class GithubChecksWebhooksTestCase(TestCase):
    def test_check_suite__requested(self):
        rf = RequestFactory()

        request = rf.post(
            "/incoming/hook",
            content_type="application/json",
            data=b'{"action":"requested","check_suite":{"id":234959143,"node_id":"MDEwOkNoZWNrU3VpdGUyMzQ5NTkxNDM=","head_branch":"test_states","head_sha":"ff6d4a6c035c56e92ea0bda647821bf34822ea53","status":"queued","conclusion":null,"url":"https://api.github.com/repos/antonpirker/django-docker-setup/check-suites/234959143","before":"1cdc05f8e66bd8d99d32186e7b52f82c4fecd87d","after":"ff6d4a6c035c56e92ea0bda647821bf34822ea53","pull_requests":[],"app":{"id":41302,"slug":"codefrog-checks","node_id":"MDM6QXBwNDEzMDI=","owner":{"login":"antonpirker","id":202325,"node_id":"MDQ6VXNlcjIwMjMyNQ==","avatar_url":"https://avatars1.githubusercontent.com/u/202325?v=4","gravatar_id":"","url":"https://api.github.com/users/antonpirker","html_url":"https://github.com/antonpirker","followers_url":"https://api.github.com/users/antonpirker/followers","following_url":"https://api.github.com/users/antonpirker/following{/other_user}","gists_url":"https://api.github.com/users/antonpirker/gists{/gist_id}","starred_url":"https://api.github.com/users/antonpirker/starred{/owner}{/repo}","subscriptions_url":"https://api.github.com/users/antonpirker/subscriptions","organizations_url":"https://api.github.com/users/antonpirker/orgs","repos_url":"https://api.github.com/users/antonpirker/repos","events_url":"https://api.github.com/users/antonpirker/events{/privacy}","received_events_url":"https://api.github.com/users/antonpirker/received_events","type":"User","site_admin":false},"name":"Codefrog Checks","description":"","external_url":"http://antonpirker.pagekite.me","html_url":"https://github.com/apps/codefrog-checks","created_at":"2019-09-17T10:00:13Z","updated_at":"2019-09-23T10:12:31Z","permissions":{"checks":"write","contents":"read","metadata":"read"},"events":["check_run"]},"created_at":"2019-09-23T12:17:09Z","updated_at":"2019-09-23T12:17:09Z","latest_check_runs_count":0,"check_runs_url":"https://api.github.com/repos/antonpirker/django-docker-setup/check-suites/234959143/check-runs","head_commit":{"id":"ff6d4a6c035c56e92ea0bda647821bf34822ea53","tree_id":"b6997d75eee5ce4ab25964c919a0896215f7ce57","message":"Test","timestamp":"2019-09-23T12:17:04Z","author":{"name":"Anton Pirker","email":"anton@ignaz.at"},"committer":{"name":"Anton Pirker","email":"anton@ignaz.at"}}},"repository":{"id":208989587,"node_id":"MDEwOlJlcG9zaXRvcnkyMDg5ODk1ODc=","name":"django-docker-setup","full_name":"antonpirker/django-docker-setup","private":false,"owner":{"login":"antonpirker","id":202325,"node_id":"MDQ6VXNlcjIwMjMyNQ==","avatar_url":"https://avatars1.githubusercontent.com/u/202325?v=4","gravatar_id":"","url":"https://api.github.com/users/antonpirker","html_url":"https://github.com/antonpirker","followers_url":"https://api.github.com/users/antonpirker/followers","following_url":"https://api.github.com/users/antonpirker/following{/other_user}","gists_url":"https://api.github.com/users/antonpirker/gists{/gist_id}","starred_url":"https://api.github.com/users/antonpirker/starred{/owner}{/repo}","subscriptions_url":"https://api.github.com/users/antonpirker/subscriptions","organizations_url":"https://api.github.com/users/antonpirker/orgs","repos_url":"https://api.github.com/users/antonpirker/repos","events_url":"https://api.github.com/users/antonpirker/events{/privacy}","received_events_url":"https://api.github.com/users/antonpirker/received_events","type":"User","site_admin":false},"html_url":"https://github.com/antonpirker/django-docker-setup","description":"A sample application to show how to use docker-compose to setupa non trivial Django project. (For our Django Meetup)","fork":false,"url":"https://api.github.com/repos/antonpirker/django-docker-setup","forks_url":"https://api.github.com/repos/antonpirker/django-docker-setup/forks","keys_url":"https://api.github.com/repos/antonpirker/django-docker-setup/keys{/key_id}","collaborators_url":"https://api.github.com/repos/antonpirker/django-docker-setup/collaborators{/collaborator}","teams_url":"https://api.github.com/repos/antonpirker/django-docker-setup/teams","hooks_url":"https://api.github.com/repos/antonpirker/django-docker-setup/hooks","issue_events_url":"https://api.github.com/repos/antonpirker/django-docker-setup/issues/events{/number}","events_url":"https://api.github.com/repos/antonpirker/django-docker-setup/events","assignees_url":"https://api.github.com/repos/antonpirker/django-docker-setup/assignees{/user}","branches_url":"https://api.github.com/repos/antonpirker/django-docker-setup/branches{/branch}","tags_url":"https://api.github.com/repos/antonpirker/django-docker-setup/tags","blobs_url":"https://api.github.com/repos/antonpirker/django-docker-setup/git/blobs{/sha}","git_tags_url":"https://api.github.com/repos/antonpirker/django-docker-setup/git/tags{/sha}","git_refs_url":"https://api.github.com/repos/antonpirker/django-docker-setup/git/refs{/sha}","trees_url":"https://api.github.com/repos/antonpirker/django-docker-setup/git/trees{/sha}","statuses_url":"https://api.github.com/repos/antonpirker/django-docker-setup/statuses/{sha}","languages_url":"https://api.github.com/repos/antonpirker/django-docker-setup/languages","stargazers_url":"https://api.github.com/repos/antonpirker/django-docker-setup/stargazers","contributors_url":"https://api.github.com/repos/antonpirker/django-docker-setup/contributors","subscribers_url":"https://api.github.com/repos/antonpirker/django-docker-setup/subscribers","subscription_url":"https://api.github.com/repos/antonpirker/django-docker-setup/subscription","commits_url":"https://api.github.com/repos/antonpirker/django-docker-setup/commits{/sha}","git_commits_url":"https://api.github.com/repos/antonpirker/django-docker-setup/git/commits{/sha}","comments_url":"https://api.github.com/repos/antonpirker/django-docker-setup/comments{/number}","issue_comment_url":"https://api.github.com/repos/antonpirker/django-docker-setup/issues/comments{/number}","contents_url":"https://api.github.com/repos/antonpirker/django-docker-setup/contents/{+path}","compare_url":"https://api.github.com/repos/antonpirker/django-docker-setup/compare/{base}...{head}","merges_url":"https://api.github.com/repos/antonpirker/django-docker-setup/merges","archive_url":"https://api.github.com/repos/antonpirker/django-docker-setup/{archive_format}{/ref}","downloads_url":"https://api.github.com/repos/antonpirker/django-docker-setup/downloads","issues_url":"https://api.github.com/repos/antonpirker/django-docker-setup/issues{/number}","pulls_url":"https://api.github.com/repos/antonpirker/django-docker-setup/pulls{/number}","milestones_url":"https://api.github.com/repos/antonpirker/django-docker-setup/milestones{/number}","notifications_url":"https://api.github.com/repos/antonpirker/django-docker-setup/notifications{?since,all,participating}","labels_url":"https://api.github.com/repos/antonpirker/django-docker-setup/labels{/name}","releases_url":"https://api.github.com/repos/antonpirker/django-docker-setup/releases{/id}","deployments_url":"https://api.github.com/repos/antonpirker/django-docker-setup/deployments","created_at":"2019-09-17T07:38:43Z","updated_at":"2019-09-17T10:35:41Z","pushed_at":"2019-09-23T12:17:08Z","git_url":"git://github.com/antonpirker/django-docker-setup.git","ssh_url":"git@github.com:antonpirker/django-docker-setup.git","clone_url":"https://github.com/antonpirker/django-docker-setup.git","svn_url":"https://github.com/antonpirker/django-docker-setup","homepage":null,"size":72,"stargazers_count":0,"watchers_count":0,"language":"Python","has_issues":true,"has_projects":true,"has_downloads":true,"has_wiki":true,"has_pages":false,"forks_count":0,"mirror_url":null,"archived":false,"disabled":false,"open_issues_count":2,"license":null,"forks":0,"open_issues":2,"watchers":0,"default_branch":"master"},"sender":{"login":"antonpirker","id":202325,"node_id":"MDQ6VXNlcjIwMjMyNQ==","avatar_url":"https://avatars1.githubusercontent.com/u/202325?v=4","gravatar_id":"","url":"https://api.github.com/users/antonpirker","html_url":"https://github.com/antonpirker","followers_url":"https://api.github.com/users/antonpirker/followers","following_url":"https://api.github.com/users/antonpirker/following{/other_user}","gists_url":"https://api.github.com/users/antonpirker/gists{/gist_id}","starred_url":"https://api.github.com/users/antonpirker/starred{/owner}{/repo}","subscriptions_url":"https://api.github.com/users/antonpirker/subscriptions","organizations_url":"https://api.github.com/users/antonpirker/orgs","repos_url":"https://api.github.com/users/antonpirker/repos","events_url":"https://api.github.com/users/antonpirker/events{/privacy}","received_events_url":"https://api.github.com/users/antonpirker/received_events","type":"User","site_admin":false},"installation":{"id":1939914,"node_id":"MDIzOkludGVncmF0aW9uSW5zdGFsbGF0aW9uMTkzOTkxNA=="}}',  # noqa
        )

        request.headers = {
            "Content-Length": "8780",
            "Content-Type": "application/json",
            "X-Forwarded-For": "::ffff:140.82.115.245",
            "X-Forwarded-Proto": "http",
            "X-Pagekite-Port": "80",
            "Host": "antonpirker.pagekite.me",
            "Accept": "*/*",
            "User-Agent": "GitHub-Hookshot/acf94e7",
            "X-Github-Event": "check_suite",
            "X-Github-Delivery": "10c2f4e0-ddfc-11e9-899e-65272afcd6ed",
        }

        out = hook(request)

    def test_installation__created(self):
        rf = RequestFactory()

        request = rf.post(
            "/incoming/hook",
            content_type="application/json",
            data=b'{"action":"created","installation":{"id":2129618,"account":{"login":"antonpirker","id":202325,"node_id":"MDQ6VXNlcjIwMjMyNQ==","avatar_url":"https://avatars1.githubusercontent.com/u/202325?v=4","gravatar_id":"","url":"https://api.github.com/users/antonpirker","html_url":"https://github.com/antonpirker","followers_url":"https://api.github.com/users/antonpirker/followers","following_url":"https://api.github.com/users/antonpirker/following{/other_user}","gists_url":"https://api.github.com/users/antonpirker/gists{/gist_id}","starred_url":"https://api.github.com/users/antonpirker/starred{/owner}{/repo}","subscriptions_url":"https://api.github.com/users/antonpirker/subscriptions","organizations_url":"https://api.github.com/users/antonpirker/orgs","repos_url":"https://api.github.com/users/antonpirker/repos","events_url":"https://api.github.com/users/antonpirker/events{/privacy}","received_events_url":"https://api.github.com/users/antonpirker/received_events","type":"User","site_admin":false},"repository_selection":"all","access_tokens_url":"https://api.github.com/app/installations/2129618/access_tokens","repositories_url":"https://api.github.com/installation/repositories","html_url":"https://github.com/settings/installations/2129618","app_id":41302,"target_id":202325,"target_type":"User","permissions":{"checks":"write","contents":"read","metadata":"read"},"events":["check_run"],"created_at":1569310815,"updated_at":1569310815,"single_file_name":null},"repositories":[{"id":5150097,"node_id":"MDEwOlJlcG9zaXRvcnk1MTUwMDk3","name":"django-postmark","full_name":"antonpirker/django-postmark","private":false},{"id":5193607,"node_id":"MDEwOlJlcG9zaXRvcnk1MTkzNjA3","name":"django-fiber","full_name":"antonpirker/django-fiber","private":false},{"id":6124848,"node_id":"MDEwOlJlcG9zaXRvcnk2MTI0ODQ4","name":"anton-pirker-at","full_name":"antonpirker/anton-pirker-at","private":false},{"id":6275378,"node_id":"MDEwOlJlcG9zaXRvcnk2Mjc1Mzc4","name":"django-inlinetrans","full_name":"antonpirker/django-inlinetrans","private":false},{"id":14665930,"node_id":"MDEwOlJlcG9zaXRvcnkxNDY2NTkzMA==","name":"django-friends-vienna","full_name":"antonpirker/django-friends-vienna","private":false},{"id":31005233,"node_id":"MDEwOlJlcG9zaXRvcnkzMTAwNTIzMw==","name":"sorl-thumbnail","full_name":"antonpirker/sorl-thumbnail","private":false},{"id":33363849,"node_id":"MDEwOlJlcG9zaXRvcnkzMzM2Mzg0OQ==","name":"antonpirker.github.io","full_name":"antonpirker/antonpirker.github.io","private":false},{"id":33615011,"node_id":"MDEwOlJlcG9zaXRvcnkzMzYxNTAxMQ==","name":"django-meetup-talk-django-1.8","full_name":"antonpirker/django-meetup-talk-django-1.8","private":false},{"id":35161715,"node_id":"MDEwOlJlcG9zaXRvcnkzNTE2MTcxNQ==","name":"djangocms-text-ckeditor","full_name":"antonpirker/djangocms-text-ckeditor","private":false},{"id":41903907,"node_id":"MDEwOlJlcG9zaXRvcnk0MTkwMzkwNw==","name":"giants","full_name":"antonpirker/giants","private":false},{"id":46784887,"node_id":"MDEwOlJlcG9zaXRvcnk0Njc4NDg4Nw==","name":"angular-schema-form","full_name":"antonpirker/angular-schema-form","private":false},{"id":46793440,"node_id":"MDEwOlJlcG9zaXRvcnk0Njc5MzQ0MA==","name":"django-jsonschema","full_name":"antonpirker/django-jsonschema","private":false},{"id":49884529,"node_id":"MDEwOlJlcG9zaXRvcnk0OTg4NDUyOQ==","name":"cmsplugin-filer","full_name":"antonpirker/cmsplugin-filer","private":false},{"id":55842799,"node_id":"MDEwOlJlcG9zaXRvcnk1NTg0Mjc5OQ==","name":"kulinarische-weltreise","full_name":"antonpirker/kulinarische-weltreise","private":false},{"id":72339921,"node_id":"MDEwOlJlcG9zaXRvcnk3MjMzOTkyMQ==","name":"button","full_name":"antonpirker/button","private":false},{"id":86747780,"node_id":"MDEwOlJlcG9zaXRvcnk4Njc0Nzc4MA==","name":"Rocket","full_name":"antonpirker/Rocket","private":false},{"id":91196887,"node_id":"MDEwOlJlcG9zaXRvcnk5MTE5Njg4Nw==","name":"vanguard","full_name":"antonpirker/vanguard","private":false},{"id":111899586,"node_id":"MDEwOlJlcG9zaXRvcnkxMTE4OTk1ODY=","name":"franz","full_name":"antonpirker/franz","private":false},{"id":112877830,"node_id":"MDEwOlJlcG9zaXRvcnkxMTI4Nzc4MzA=","name":"player-wireframe","full_name":"antonpirker/player-wireframe","private":false},{"id":123118104,"node_id":"MDEwOlJlcG9zaXRvcnkxMjMxMTgxMDQ=","name":"django-pipinator","full_name":"antonpirker/django-pipinator","private":false},{"id":127290012,"node_id":"MDEwOlJlcG9zaXRvcnkxMjcyOTAwMTI=","name":"dotfiles","full_name":"antonpirker/dotfiles","private":false},{"id":127426878,"node_id":"MDEwOlJlcG9zaXRvcnkxMjc0MjY4Nzg=","name":"jupyter-vagrant-box","full_name":"antonpirker/jupyter-vagrant-box","private":false},{"id":182089533,"node_id":"MDEwOlJlcG9zaXRvcnkxODIwODk1MzM=","name":"codefrog","full_name":"antonpirker/codefrog","private":true},{"id":190761837,"node_id":"MDEwOlJlcG9zaXRvcnkxOTA3NjE4Mzc=","name":"nowstagram","full_name":"antonpirker/nowstagram","private":false},{"id":208989587,"node_id":"MDEwOlJlcG9zaXRvcnkyMDg5ODk1ODc=","name":"django-docker-setup","full_name":"antonpirker/django-docker-setup","private":false}],"requester":null,"sender":{"login":"antonpirker","id":202325,"node_id":"MDQ6VXNlcjIwMjMyNQ==","avatar_url":"https://avatars1.githubusercontent.com/u/202325?v=4","gravatar_id":"","url":"https://api.github.com/users/antonpirker","html_url":"https://github.com/antonpirker","followers_url":"https://api.github.com/users/antonpirker/followers","following_url":"https://api.github.com/users/antonpirker/following{/other_user}","gists_url":"https://api.github.com/users/antonpirker/gists{/gist_id}","starred_url":"https://api.github.com/users/antonpirker/starred{/owner}{/repo}","subscriptions_url":"https://api.github.com/users/antonpirker/subscriptions","organizations_url":"https://api.github.com/users/antonpirker/orgs","repos_url":"https://api.github.com/users/antonpirker/repos","events_url":"https://api.github.com/users/antonpirker/events{/privacy}","received_events_url":"https://api.github.com/users/antonpirker/received_events","type":"User","site_admin":false}}',  # noqa
        )

        request.headers = {
            "Content-Length": "6028",
            "Content-Type": "application/json",
            "X-Forwarded-For": "::ffff:140.82.115.247",
            "X-Forwarded-Proto": "http",
            "X-Pagekite-Port": "80",
            "Host": "antonpirker.pagekite.me",
            "Accept": "*/*",
            "User-Agent": "GitHub-Hookshot/2df7131",
            "X-Github-Event": "installation",
            "X-Github-Delivery": "8c9a6b00-de9e-11e9-9be4-0d46c056aa1e",
            "X-Hub-Signature": "sha1=ff9ccc0087e9695caa5155e3294a0e63b6e4e794",
        }

        out = hook(request)

    def test_setup(self):
        rf = RequestFactory()

        request = rf.post(
            "/incoming/setup",
            content_type="application/json",
            data=b"",
        )

        request.headers = {
            "Content-Length": "",
            "Content-Type": "text/plain",
            "X-Forwarded-For": "::ffff:80.110.97.51",
            "X-Forwarded-Proto": "http",
            "X-Pagekite-Port": "80",
            "Host": "antonpirker.pagekite.me",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0",  # noqa
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Dnt": "1",
            "Connection": "keep-alive",
            "Cookie": "csrftoken=s7VX6uSSzgs1JqQsvoyrC1Nr4IuoOiCj4Pwq3qhmVVlvHOmbNtoCJqnZP9FRdrIE",  # noqa
            "Upgrade-Insecure-Requests": "1",
        }

        out = setup(request)

    def test_authorization(self):
        rf = RequestFactory()

        request = rf.post(
            "/incoming/authorization",
            content_type="application/json",
            data=b"",
        )

        request.headers = {
            "Content-Length": "",
            "Content-Type": "text/plain",
            "X-Forwarded-For": "::ffff:80.110.97.51",
            "X-Forwarded-Proto": "http",
            "X-Pagekite-Port": "80",
            "Host": "antonpirker.pagekite.me",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0",  # noqa
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Dnt": "1",
            "Connection": "keep-alive",
            "Cookie": "csrftoken=s7VX6uSSzgs1JqQsvoyrC1Nr4IuoOiCj4Pwq3qhmVVlvHOmbNtoCJqnZP9FRdrIE",  # noqa
            "Upgrade-Insecure-Requests": "1",
        }

        out = authorization(request)
