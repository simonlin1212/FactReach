# -*- coding: utf-8 -*-
"""Zero-auth academic discovery across public scholarly indexes."""

from ._opencli_public import OpenCLIPublicChannel


class AcademicChannel(OpenCLIPublicChannel):
    name = "academic"
    description = "学术论文搜索"
    domains = (
        "arxiv.org",
        "pubmed.ncbi.nlm.nih.gov",
        "semanticscholar.org",
        "openreview.net",
        "dblp.org",
    )
    adapters = ("arxiv", "pubmed", "semanticscholar", "openreview", "dblp")
    usage = "opencli arxiv/pubmed/semanticscholar/openreview/dblp ... -f json"

    def check(self, config=None):
        status, message = super().check(config)
        if status in {"ok", "warn"}:
            message += (
                "；Semantic Scholar 匿名请求可能 429，遇到时改用其他"
                "论文库或配置官方免费 Key"
            )
        return status, message
