# -*- coding: utf-8 -*-
"""Stack Overflow public search/read via OpenCLI."""

from ._opencli_public import OpenCLIPublicChannel


class StackOverflowChannel(OpenCLIPublicChannel):
    name = "stackoverflow"
    description = "Stack Overflow 问答"
    domains = ("stackoverflow.com",)
    adapters = ("stackoverflow",)
    usage = "opencli stackoverflow search QUERY; opencli stackoverflow read ID"
