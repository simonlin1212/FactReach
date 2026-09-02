# -*- coding: utf-8 -*-
"""GitHub Trending public discovery via OpenCLI."""

from urllib.parse import urlsplit

from agent_reach.utils.url import host_matches

from ._opencli_public import OpenCLIPublicChannel


class GitHubTrendingChannel(OpenCLIPublicChannel):
    name = "github_trending"
    description = "GitHub Trending 热门仓库"
    domains = ("github.com",)
    adapters = ("github-trending",)
    usage = "opencli github-trending repos -f json"

    def can_handle(self, url: str) -> bool:
        if not host_matches(url, "github.com"):
            return False
        path = urlsplit(url).path.lower().rstrip("/")
        return path == "/trending" or path.startswith("/trending/")
