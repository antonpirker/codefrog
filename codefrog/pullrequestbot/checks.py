import os
import shutil

from django.conf import settings
from git import Repo

from core.utils import get_path_complexity


def perform_complexity_check(
        installation_access_token, repository_full_name, repository_github_id,
        commit_sha_before, commit_sha_after,
):
    # Get the source code
    git_url = f'https://x-access-token:{installation_access_token}@github.com/{repository_full_name}.git'
    repo_dir = os.path.join(settings.PROJECT_SOURCE_CODE_DIR, repository_full_name)

    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    if not os.path.exists(repo_dir):
        os.makedirs(repo_dir)

    repo = Repo.clone_from(git_url, repo_dir)

    # Calculate complexity before
    repo.git.reset('--hard', commit_sha_before)
    complexity_before = get_path_complexity(repo_dir)

    # Calculate complexity after
    repo.git.reset('--hard', commit_sha_after)
    complexity_after = get_path_complexity(repo_dir)

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
        This is OK if you implement some new features. Just make sure, that you keep an eye on the overall complexity."""
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