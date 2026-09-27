# Class for Github Errors

class GitHubApiError(Exception):
    """Any failure to get usable data from GitHub."""


class ResourceNotFound(GitHubApiError):
    """404, e.g. a repo deleted between listing and accuracy sampling."""
