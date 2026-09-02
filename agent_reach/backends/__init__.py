# -*- coding: utf-8 -*-
"""Cross-channel backends.

A backend here is an upstream runtime that serves MULTIPLE channels
(e.g. OpenCLI covers xiaohongshu/reddit/bilibili/twitter through one
browser session), as opposed to the per-platform tools probed inside
each channel file.
"""

from .browser_harness import (  # noqa: F401
    BrowserHarnessError,
    BrowserHarnessStatus,
    browser_harness_read,
    browser_harness_status,
)
from .firecrawl import (  # noqa: F401
    FirecrawlError,
    FirecrawlStatus,
    firecrawl_scrape,
    firecrawl_status,
)
from .opencli import (  # noqa: F401
    OPENCLI_EXTENSION_URL,
    OPENCLI_PACKAGE,
    OpenCLIStatus,
    opencli_status,
    opencli_summary,
    probe_opencli_adapters,
    probe_opencli_public,
    probe_opencli_public_adapters,
    probe_opencli_wechat_adapter,
    probe_opencli_weibo_adapter,
)
