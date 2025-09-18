"""
Configuration settings for Instagram Content Downloader
"""

import os
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    min_delay: float = 3.0          # Minimum delay between requests (seconds)
    max_delay: float = 8.0          # Maximum delay between requests (seconds)
    batch_size: int = 10            # Items to process before longer break
    batch_delay: float = 300        # Break between batches (5 minutes)
    error_delay: float = 60         # Delay after errors (1 minute)
    rate_limit_delay: float = 900   # Delay after rate limit hit (15 minutes)
    
    # Dynamic adjustment factors
    success_reduction: float = 0.9  # Reduce delay after successful requests
    failure_increase: float = 1.5   # Increase delay after failures
    max_dynamic_delay: float = 30.0 # Maximum dynamic delay


@dataclass
class DownloadConfig:
    """Download configuration"""
    downloads_dir: str = "downloads"
    sessions_dir: str = "sessions"
    max_retries: int = 3
    download_timeout: float = 300.0
    create_profile_folders: bool = True
    preserve_metadata: bool = True
    
    # Content type settings
    download_photos: bool = True
    download_videos: bool = True
    download_reels: bool = True
    download_stories: bool = False  # More restrictive
    
    # Quality settings
    save_captions: bool = True
    save_comments: bool = False
    save_metadata: bool = True


class AppConfig:
    """Main application configuration"""
    
    def __init__(self):
        self.rate_limit = RateLimitConfig()
        self.download = DownloadConfig()
        
        # Create directories if they don't exist
        os.makedirs(self.download.downloads_dir, exist_ok=True)
        os.makedirs(self.download.sessions_dir, exist_ok=True)
    
    def get_session_file(self, username: str) -> str:
        """Get session file path for a username"""
        return os.path.join(self.download.sessions_dir, f"{username}_session")
    
    def get_download_path(self, profile_name: str) -> str:
        """Get download path for a profile"""
        if self.download.create_profile_folders:
            path = os.path.join(self.download.downloads_dir, profile_name)
            os.makedirs(path, exist_ok=True)
            return path
        return self.download.downloads_dir


# Global configuration instance
config = AppConfig()