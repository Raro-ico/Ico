"""
Instagram Crawler Component
Discovers and catalogs content from profiles with selective filtering
"""

import instaloader
import time
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from instaloader.exceptions import ProfileNotExistsException, LoginRequiredException, TooManyRequestsException
from .config import config


@dataclass
class ContentItem:
    """Represents a piece of Instagram content to be downloaded"""
    shortcode: str          # Instagram shortcode for the post
    url: str               # Direct URL to the content
    content_type: str      # 'photo', 'video', 'reel'
    caption: str          # Post caption
    timestamp: float      # Unix timestamp
    filename: str         # Suggested filename
    metadata: Dict[str, Any]  # Additional metadata


class InstagramCrawler:
    """
    Discovers content from Instagram profiles with intelligent filtering
    Works with the SmartAnalyzer to respect rate limits
    """
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.loader = None
        self.current_profile = None
        self.session_username = None
        
        # Initialize instaloader with conservative settings
        self._initialize_loader()
    
    def _initialize_loader(self):
        """Initialize Instaloader with optimal settings"""
        try:
            self.loader = instaloader.Instaloader(
                dirname_pattern=config.download.downloads_dir,
                filename_pattern="{profile}_{shortcode}",
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=config.download.save_comments,
                save_metadata=config.download.save_metadata,
                compress_json=False,
                max_connection_attempts=1,
                request_timeout=config.download.download_timeout
            )
            
            print("✅ Instagram loader initialized")
            
        except Exception as e:
            self.loader = instaloader.Instaloader()  # Fallback to basic loader
            print(f"⚠️  Using basic loader due to error: {e}")
    
    def login(self, username: str, password: str) -> bool:
        """Login to Instagram for better rate limits"""
        if not self.loader:
            print("❌ Loader not initialized")
            return False
            
        try:
            session_file = config.get_session_file(username)
            
            # Try to load existing session first
            if os.path.exists(session_file):
                try:
                    self.loader.load_session_from_file(username, session_file)
                    self.session_username = username
                    print("✅ Loaded existing session")
                    return True
                except Exception:
                    print("⚠️  Existing session invalid, logging in fresh...")
            
            # Perform fresh login
            print("🔐 Logging into Instagram...")
            self.loader.login(username, password)
            
            # Save session for future use
            self.loader.save_session_to_file(session_file)
            self.session_username = username
            
            # Record successful login
            self.analyzer.record_event('success', 0.0, 0.0, "Login successful")
            
            return True
            
        except Exception as e:
            self.analyzer.record_event('error', 0.0, 0.0, f"Login failed: {e}")
            print(f"❌ Login failed: {e}")
            return False
    
    def crawl_profile(self, profile_name: str, content_types: List[str], 
                     limits: Dict[str, Any]) -> List[ContentItem]:
        """
        Crawl a profile and return a list of content items matching criteria
        """
        print(f"🔍 Starting to crawl profile: @{profile_name}")
        
        try:
            # Load profile with rate limiting
            profile = self._load_profile_safely(profile_name)
            if not profile:
                return []
            
            self.current_profile = profile
            
            # Get content based on requested types
            content_items = []
            
            if any(t in content_types for t in ['photos', 'videos', 'reels']):
                posts_items = self._crawl_posts(profile, content_types, limits)
                content_items.extend(posts_items)
            
            if 'stories' in content_types:
                stories_items = self._crawl_stories(profile, limits)
                content_items.extend(stories_items)
            
            # Apply overall limits
            content_items = self._apply_limits(content_items, limits)
            
            print(f"✅ Crawling completed. Found {len(content_items)} items")
            return content_items
            
        except Exception as e:
            self.analyzer.record_event('error', 0.0, 0.0, f"Crawl failed: {e}")
            print(f"❌ Profile crawling failed: {e}")
            return []
    
    def _load_profile_safely(self, profile_name: str):
        """Load Instagram profile with rate limiting and error handling"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # Apply rate limiting delay
                if attempt > 0:
                    delay = self.analyzer.get_next_delay() * (attempt + 1)
                    self.analyzer.wait_with_progress(delay, f"Retry {attempt + 1}/{max_retries}")
                
                # Load profile
                print(f"📋 Loading profile @{profile_name}...")
                if not self.loader:
                    raise Exception("Loader not initialized")
                profile = instaloader.Profile.from_username(self.loader.context, profile_name)
                
                response_time = time.time() - start_time
                self.analyzer.record_event('success', 0.0, response_time)
                
                # Show profile info
                print(f"✅ Profile loaded: @{profile.username}")
                print(f"📊 Posts: {profile.mediacount}, Followers: {profile.followers}")
                
                if profile.is_private:
                    print("🔒 Note: This is a private profile")
                    if not self.session_username:
                        print("❌ Private profile requires login")
                        return None
                
                return profile
                
            except ProfileNotExistsException:
                print(f"❌ Profile @{profile_name} does not exist")
                return None
                
            except LoginRequiredException:
                print(f"❌ Profile @{profile_name} requires login")
                return None
                
            except TooManyRequestsException:
                delay = config.rate_limit.rate_limit_delay * (attempt + 1)
                self.analyzer.record_event('rate_limit', delay, 0.0, "Profile load rate limited")
                
                if attempt < max_retries - 1:
                    print(f"⚠️  Rate limit hit. Waiting {delay/60:.1f} minutes before retry...")
                    self.analyzer.wait_with_progress(delay, "Rate limit cooldown")
                else:
                    print("❌ Rate limit exceeded. Try again later.")
                    return None
                    
            except Exception as e:
                response_time = time.time() - start_time
                self.analyzer.record_event('error', 0.0, response_time, str(e))
                
                if attempt < max_retries - 1:
                    delay = config.rate_limit.error_delay * (attempt + 1)
                    print(f"⚠️  Error loading profile: {e}")
                    print(f"🔄 Retrying in {delay} seconds...")
                    self.analyzer.wait_with_progress(delay, f"Error recovery")
                else:
                    print(f"❌ Failed to load profile after {max_retries} attempts: {e}")
                    return None
        
        return None
    
    def _crawl_posts(self, profile, content_types: List[str], limits: Dict[str, Any]) -> List[ContentItem]:
        """Crawl regular posts from profile"""
        content_items = []
        processed_count = 0
        
        print(f"📸 Crawling posts from @{profile.username}...")
        
        try:
            posts = profile.get_posts()
            
            for post in posts:
                try:
                    # Check if we should take a batch break
                    if self.analyzer.should_take_batch_break(processed_count):
                        batch_delay = self.analyzer.get_batch_delay()
                        print(f"\n⏸️  Batch break after {processed_count} items")
                        self.analyzer.wait_with_progress(batch_delay, "Batch cooldown")
                    
                    # Apply rate limiting before each request
                    delay = self.analyzer.get_next_delay()
                    self.analyzer.wait_with_progress(delay, "Rate limiting")
                    
                    start_time = time.time()
                    
                    # Determine content type
                    if post.is_video:
                        post_type = 'reel' if hasattr(post, 'is_reel') and post.is_reel else 'video'
                    else:
                        post_type = 'photo'
                    
                    # Check if this content type is requested
                    if post_type not in content_types and not any(t in content_types for t in ['photos', 'videos', 'reels']):
                        continue
                    
                    # Get the appropriate URL for the content
                    content_url = post.video_url if post.is_video else post.url
                    
                    # Create content item
                    content_item = ContentItem(
                        shortcode=post.shortcode,
                        url=content_url,
                        content_type=post_type,
                        caption=post.caption or "",
                        timestamp=post.date_utc.timestamp(),
                        filename=f"{profile.username}_{post.shortcode}",
                        metadata={
                            'likes': post.likes,
                            'comments': post.comments,
                            'is_video': post.is_video,
                            'dimensions': f"{post.dimensions[0]}x{post.dimensions[1]}" if hasattr(post, 'dimensions') else None,
                            'accessibility_caption': getattr(post, 'accessibility_caption', None),
                            'post_object': post  # Store post object for proper download
                        }
                    )
                    
                    content_items.append(content_item)
                    processed_count += 1
                    
                    response_time = time.time() - start_time
                    self.analyzer.record_event('success', delay, response_time)
                    
                    print(f"✅ Found {post_type}: {post.shortcode} ({len(content_items)} total)")
                    
                    # Check total limit
                    if limits.get('total') and len(content_items) >= limits['total']:
                        print(f"🎯 Reached limit of {limits['total']} items")
                        break
                    
                except TooManyRequestsException:
                    delay = config.rate_limit.rate_limit_delay
                    self.analyzer.record_event('rate_limit', delay, 0.0, "Post crawl rate limited")
                    print(f"⚠️  Rate limited. Waiting {delay/60:.1f} minutes...")
                    self.analyzer.wait_with_progress(delay, "Rate limit recovery")
                    
                except Exception as e:
                    response_time = time.time() - start_time if 'start_time' in locals() else 0.0
                    self.analyzer.record_event('error', delay if 'delay' in locals() else 0.0, response_time, str(e))
                    print(f"⚠️  Error processing post {getattr(post, 'shortcode', 'unknown')}: {e}")
                    continue
            
        except Exception as e:
            print(f"❌ Error crawling posts: {e}")
        
        return content_items
    
    def _crawl_stories(self, profile, limits: Dict[str, Any]) -> List[ContentItem]:
        """Crawl stories from profile (requires login and more restrictive)"""
        if not self.session_username:
            print("⚠️  Stories require login - skipping")
            return []
        
        content_items = []
        
        try:
            print(f"📱 Crawling stories from @{profile.username}...")
            
            # Apply extra delay for stories (more restrictive)
            delay = self.analyzer.get_next_delay() * 2
            self.analyzer.wait_with_progress(delay, "Stories rate limiting")
            
            start_time = time.time()
            if not self.loader:
                raise Exception("Loader not initialized")
            stories = self.loader.get_stories([profile.userid])
            
            for story in stories:
                for item in story.get_items():
                    content_item = ContentItem(
                        shortcode=f"story_{item.mediaid}",
                        url=item.url,
                        content_type='story_video' if item.is_video else 'story_photo',
                        caption="",
                        timestamp=item.date_utc.timestamp(),
                        filename=f"{profile.username}_story_{item.mediaid}",
                        metadata={
                            'story_id': item.mediaid,
                            'is_video': item.is_video
                        }
                    )
                    
                    content_items.append(content_item)
                    
                    if limits.get('total') and len(content_items) >= limits['total']:
                        break
            
            response_time = time.time() - start_time
            self.analyzer.record_event('success', delay, response_time)
            
        except Exception as e:
            response_time = time.time() - start_time if 'start_time' in locals() else 0.0
            self.analyzer.record_event('error', delay, response_time, str(e))
            print(f"⚠️  Error crawling stories: {e}")
        
        return content_items
    
    def _apply_limits(self, content_items: List[ContentItem], limits: Dict[str, Any]) -> List[ContentItem]:
        """Apply user-specified limits to content list"""
        if not content_items:
            return content_items
        
        # Sort by timestamp if newest_first is requested
        if limits.get('newest_first', False):
            content_items.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply total limit
        if limits.get('total'):
            content_items = content_items[:limits['total']]
        
        return content_items