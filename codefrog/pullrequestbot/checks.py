from core.models import Project
from core.utils import get_path_complexity, run_shell_command


def get_project_matching_github_hook(payload):
    try:
        return Project.object.get(external_services__github__repository_id=payload['repository']['id'])
    except Project.DoesNotExist:
        return None


def perform_complexity_check(project, commit_sha_before, commit_sha_after):
    with project.get_tmp_repo_dir() as tmp_dir:
        # Calculate complexity before
        cmd = f'git reset --hard "{commit_sha_before}"'
        run_shell_command(cmd, cwd=tmp_dir)
        complexity_before = get_path_complexity(tmp_dir)

        # Calculate complexity after
        cmd = f'git reset --hard "{commit_sha_after}"'
        run_shell_command(cmd, cwd=tmp_dir)
        complexity_after = get_path_complexity(tmp_dir)

        # Calculate change
        complexity_change = round((100 / complexity_before) * complexity_after - 100, 1)

        # Create "weather forecast" for the complexity change
        sunny = '🌞'  # U+1F31E
        party_cloudy = '⛅'  # U+26C5
        cloudy = '☁'  # U+2601
        stormy = '⛈'  # U+26C8
        unknown = ''  # nothing :)

        if complexity_change <= 0:
            icon = sunny
            summary = f"""You have decreased your complexity of the system by {complexity_change:+.1f}%.
                Well done! You are on the right tracks to make your project more maintainable!"""
            conclusion = 'success'

        elif 0 < complexity_change <= 2.5:
            icon = party_cloudy
            summary = f"""You have increased your complexity of the system by {complexity_change:+.1f}%.
                This is OK."""
            conclusion = 'neutral'

        elif 2.5 < complexity_change <= 5:
            icon = cloudy
            summary = f"""You have increased your complexity of the system by {complexity_change:+.1f}%.
                This is OK if you implement some new features. 
                Just make sure, that you keep an eye on the overall complexity."""
            conclusion = 'neutral'

        elif complexity_change > 5:
            icon = stormy
            summary = f"""You have increased your complexity of the system by {complexity_change:+.1f}%.
                This is not a good sign. Maybe see if you can refactor your code
                a little to have less complexity."""
            conclusion = 'neutral'

        else:
            icon = unknown
            summary = f"""I do not know the complexity in your system has changed. Strange thing..."""
            conclusion = 'neutral'

        title = f'{icon} Complexity: {complexity_change:+.1f}%'

        output = {
            'title': title,
            'summary': summary,
            'conclusion': conclusion,
        }

        return output