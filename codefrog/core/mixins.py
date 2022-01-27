class GithubMixin:
    @property
    def on_github(self):
        return self.source == "github"

    @property
    def github_repo_url(self):
        if self.on_github:
            return self.git_url.replace(".git", "")

        return None

    @property
    def github_repo_full_name(self):
        if self.on_github:
            return "/".join(self.github_repo_url.split("/")[-2:])

        return None

    @property
    def github_repo_owner(self):
        if self.on_github:
            return self.github_repo_url.split("/")[-2]

        return None

    @property
    def github_repo_name(self):
        if self.on_github:
            return self.github_repo_url.split("/")[-1]

        return None
