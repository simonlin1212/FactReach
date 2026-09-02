# -*- coding: utf-8 -*-
"""
Channel registry — lists all supported platforms for doctor checks.
"""

from typing import List, Optional

from .academic import AcademicChannel

# Import all channels
from .base import Channel
from .bilibili import BilibiliChannel
from .douyin import DouyinChannel
from .exa_search import ExaSearchChannel
from .facebook import FacebookChannel
from .github import GitHubChannel
from .github_trending import GitHubTrendingChannel
from .hackernews import HackerNewsChannel
from .instagram import InstagramChannel
from .linkedin import LinkedInChannel
from .reddit import RedditChannel
from .rss import RSSChannel
from .stackoverflow import StackOverflowChannel
from .twitter import TwitterChannel
from .v2ex import V2EXChannel
from .web import WebChannel
from .web_search import WebSearchChannel
from .wechat_public import WeChatPublicChannel
from .weibo import WeiboChannel
from .xiaohongshu import XiaoHongShuChannel
from .xiaoyuzhou import XiaoyuzhouChannel
from .xueqiu import XueqiuChannel
from .youtube import YouTubeChannel

ALL_CHANNELS: List[Channel] = [
    GitHubTrendingChannel(),
    GitHubChannel(),
    WebSearchChannel(),
    HackerNewsChannel(),
    WeChatPublicChannel(),
    AcademicChannel(),
    StackOverflowChannel(),
    DouyinChannel(),
    TwitterChannel(),
    YouTubeChannel(),
    RedditChannel(),
    FacebookChannel(),
    InstagramChannel(),
    WeiboChannel(),
    BilibiliChannel(),
    XiaoHongShuChannel(),
    LinkedInChannel(),
    XiaoyuzhouChannel(),
    V2EXChannel(),
    XueqiuChannel(),
    RSSChannel(),
    ExaSearchChannel(),
    WebChannel(),
]


def get_channel(name: str) -> Optional[Channel]:
    """Get a channel by name."""
    for ch in ALL_CHANNELS:
        if ch.name == name:
            return ch
    return None


def get_all_channels() -> List[Channel]:
    """Get all registered channels."""
    return ALL_CHANNELS


__all__ = [
    "Channel",
    "ALL_CHANNELS",
    "get_channel",
    "get_all_channels",
]
