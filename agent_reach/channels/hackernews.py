# -*- coding: utf-8 -*-
"""Hacker News via OpenCLI's public adapter."""

from ._opencli_public import OpenCLIPublicChannel


class HackerNewsChannel(OpenCLIPublicChannel):
    name = "hackernews"
    description = "Hacker News 热门、搜索和讨论"
    domains = ("news.ycombinator.com",)
    adapters = ("hackernews",)
    usage = "opencli hackernews search/read/top -f json"
