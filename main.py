#!/usr/bin/env python3
"""
Instagram Content Downloader
A smart Instagram downloader with rate limiting, selective content downloading, and progress tracking.
"""

import argparse
import sys
from src.cli import InteractiveCLI
from src.analyzer import SmartAnalyzer
from src.crawler import InstagramCrawler
from src.downloader import ContentDownloader


def main():
    """Main entry point for Instagram Content Downloader"""
    print("🚀 Instagram Content Downloader")
    print("=" * 50)
    
    # Initialize components
    analyzer = SmartAnalyzer()
    crawler = InstagramCrawler(analyzer)
    downloader = ContentDownloader(analyzer)
    cli = InteractiveCLI(crawler, downloader)
    
    # Connect downloader to crawler's loader for authentication sharing
    downloader.set_loader(crawler.loader)
    
    try:
        # Start interactive session
        cli.start_session()
    except KeyboardInterrupt:
        print("\n\n❌ Download interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()