"""
Interactive Command Line Interface
Handles user input and coordinates between components
"""

import os
import sys
from typing import List, Dict, Optional, Tuple
from .config import config


class InteractiveCLI:
    """
    Interactive command-line interface for Instagram content downloader
    Guides users through the download process and handles input validation
    """
    
    def __init__(self, crawler, downloader):
        self.crawler = crawler
        self.downloader = downloader
        self.current_session = {}
    
    def start_session(self):
        """Start an interactive download session"""
        print("\n🎯 Welcome to Instagram Content Downloader!")
        print("This tool helps you download Instagram content while respecting rate limits.\n")
        
        try:
            # Get user preferences
            self._get_user_preferences()
            
            # Show session summary
            self._show_session_summary()
            
            # Confirm and start download
            if self._confirm_download():
                self._execute_download()
            else:
                print("❌ Download cancelled by user.")
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Session interrupted by user")
            return
        except Exception as e:
            print(f"\n💥 Session error: {e}")
            return
    
    def _get_user_preferences(self):
        """Collect user preferences for the download session"""
        print("📋 Let's configure your download session:\n")
        
        # Get profile name
        self.current_session['profile'] = self._get_profile_name()
        
        # Get content types to download
        self.current_session['content_types'] = self._get_content_types()
        
        # Get download limits
        self.current_session['limits'] = self._get_download_limits()
        
        # Get additional options
        self.current_session['options'] = self._get_additional_options()
    
    def _get_profile_name(self) -> str:
        """Get and validate Instagram profile name"""
        while True:
            profile = input("👤 Enter Instagram profile username (without @): ").strip()
            
            if not profile:
                print("❌ Profile name cannot be empty. Please try again.")
                continue
            
            # Remove @ if user included it
            profile = profile.lstrip('@')
            
            # Basic validation
            if not profile.replace('_', '').replace('.', '').isalnum():
                print("❌ Invalid profile name. Use only letters, numbers, dots, and underscores.")
                continue
            
            # Confirm profile
            confirm = input(f"✅ Download from '@{profile}'? (y/n): ").lower().strip()
            if confirm in ['y', 'yes']:
                return profile
            
            print("Let's try again...\n")
    
    def _get_content_types(self) -> List[str]:
        """Get what types of content to download"""
        print("\n📸 What content would you like to download?")
        print("1. Photos only")
        print("2. Reels/Videos only") 
        print("3. Both photos and reels/videos")
        print("4. Custom selection")
        
        while True:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                return ["photos"]
            elif choice == "2":
                return ["reels", "videos"]
            elif choice == "3":
                return ["photos", "reels", "videos"]
            elif choice == "4":
                return self._custom_content_selection()
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
    
    def _custom_content_selection(self) -> List[str]:
        """Allow custom content type selection"""
        content_types = []
        
        options = {
            'photos': "📷 Regular photos/images",
            'reels': "🎬 Reels",
            'videos': "🎥 Videos (IGTV, etc.)",
            'stories': "📱 Stories (if available - more restrictive)"
        }
        
        print("\n🛠️  Custom content selection:")
        for key, description in options.items():
            while True:
                choice = input(f"Download {description}? (y/n): ").lower().strip()
                if choice in ['y', 'yes']:
                    content_types.append(key)
                    break
                elif choice in ['n', 'no']:
                    break
                else:
                    print("Please enter 'y' for yes or 'n' for no.")
        
        if not content_types:
            print("⚠️  No content types selected. Defaulting to photos and reels.")
            return ["photos", "reels"]
        
        return content_types
    
    def _get_download_limits(self) -> Dict[str, int]:
        """Get download limits from user"""
        print("\n📊 Set download limits:")
        print("(This helps avoid rate limits and manages download size)")
        
        limits = {}
        
        # Get overall limit
        while True:
            try:
                total_limit = input("\n🔢 Maximum total items to download (or 'all' for everything): ").strip().lower()
                
                if total_limit == 'all':
                    limits['total'] = None
                    break
                else:
                    total_limit = int(total_limit)
                    if total_limit <= 0:
                        print("❌ Please enter a positive number or 'all'.")
                        continue
                    limits['total'] = total_limit
                    break
            except ValueError:
                print("❌ Please enter a valid number or 'all'.")
        
        # Ask about recent content preference
        recent_choice = input("\n📅 Download newest content first? (y/n): ").lower().strip()
        limits['newest_first'] = recent_choice in ['y', 'yes']
        
        return limits
    
    def _get_additional_options(self) -> Dict[str, any]:
        """Get additional download options"""
        print("\n⚙️  Additional options:")
        
        options = {}
        
        # Login option
        login_choice = input("🔐 Use your Instagram login for better rate limits? (y/n): ").lower().strip()
        options['use_login'] = login_choice in ['y', 'yes']
        
        if options['use_login']:
            options['username'] = input("👤 Your Instagram username: ").strip()
            # Note: We'll handle password securely during execution
        
        # Metadata options
        metadata_choice = input("📝 Save captions and metadata? (y/n): ").lower().strip()
        options['save_metadata'] = metadata_choice in ['y', 'yes']
        
        # Resume option
        resume_choice = input("🔄 Enable resume functionality for interrupted downloads? (y/n): ").lower().strip()
        options['enable_resume'] = resume_choice in ['y', 'yes']
        
        return options
    
    def _show_session_summary(self):
        """Display a summary of the current session configuration"""
        print("\n" + "="*60)
        print("📋 DOWNLOAD SESSION SUMMARY")
        print("="*60)
        
        print(f"👤 Profile: @{self.current_session['profile']}")
        print(f"📸 Content types: {', '.join(self.current_session['content_types'])}")
        
        total_limit = self.current_session['limits']['total']
        if total_limit:
            print(f"🔢 Download limit: {total_limit} items")
        else:
            print("🔢 Download limit: All available content")
        
        if self.current_session['limits']['newest_first']:
            print("📅 Order: Newest content first")
        else:
            print("📅 Order: Default order")
        
        if self.current_session['options']['use_login']:
            print(f"🔐 Using login: {self.current_session['options']['username']}")
        else:
            print("🔐 Using anonymous access")
        
        print(f"📝 Save metadata: {'Yes' if self.current_session['options']['save_metadata'] else 'No'}")
        print(f"🔄 Resume capability: {'Yes' if self.current_session['options']['enable_resume'] else 'No'}")
        
        print("="*60)
    
    def _confirm_download(self) -> bool:
        """Get final confirmation from user before starting download"""
        print("\n⚠️  IMPORTANT NOTES:")
        print("• This tool respects Instagram's rate limits to avoid account restrictions")
        print("• Downloads may take time due to built-in delays")
        print("• You can interrupt the process anytime with Ctrl+C")
        print("• Downloaded content is for personal use only")
        
        while True:
            confirm = input(f"\n🚀 Start downloading from @{self.current_session['profile']}? (y/n): ").lower().strip()
            
            if confirm in ['y', 'yes']:
                return True
            elif confirm in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    def _execute_download(self):
        """Execute the download process with the configured settings"""
        print(f"\n🚀 Starting download from @{self.current_session['profile']}...")
        print("=" * 60)
        
        try:
            # Phase 1: Initialize and login if needed
            if self.current_session['options']['use_login']:
                self._handle_login()
            
            # Phase 2: Crawl and discover content
            print("\n🔍 Phase 1: Discovering content...")
            content_list = self.crawler.crawl_profile(
                profile_name=self.current_session['profile'],
                content_types=self.current_session['content_types'],
                limits=self.current_session['limits']
            )
            
            if not content_list:
                print("❌ No content found or profile might be private.")
                return
            
            print(f"✅ Found {len(content_list)} items to download")
            
            # Phase 3: Download content
            print("\n⬇️  Phase 2: Downloading content...")
            self.downloader.download_content_list(
                content_list=content_list,
                profile_name=self.current_session['profile'],
                options=self.current_session['options']
            )
            
            print("\n🎉 Download session completed!")
            self._show_completion_summary()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Download interrupted by user")
            self._handle_interruption()
        except Exception as e:
            print(f"\n💥 Download error: {e}")
            self._handle_error(e)
    
    def _handle_login(self):
        """Handle Instagram login process"""
        import getpass
        
        username = self.current_session['options']['username']
        
        # Check for existing session
        session_file = config.get_session_file(username)
        if os.path.exists(session_file):
            use_existing = input("🔄 Found existing login session. Use it? (y/n): ").lower().strip()
            if use_existing in ['y', 'yes']:
                return
        
        # Get password securely
        password = getpass.getpass("🔐 Enter your Instagram password: ")
        
        # Initialize login through crawler
        success = self.crawler.login(username, password)
        
        if success:
            print("✅ Login successful!")
        else:
            print("❌ Login failed. Continuing with anonymous access...")
            self.current_session['options']['use_login'] = False
    
    def _show_completion_summary(self):
        """Show summary after download completion"""
        download_path = config.get_download_path(self.current_session['profile'])
        print("\n" + "="*60)
        print("✅ DOWNLOAD COMPLETED")
        print("="*60)
        print(f"📁 Files saved to: {download_path}")
        print("📊 Check the download folder for your content")
        print("💡 You can run this tool again to download more content")
    
    def _handle_interruption(self):
        """Handle user interruption gracefully"""
        if self.current_session['options']['enable_resume']:
            print("💾 Resume data has been saved.")
            print("💡 You can restart the download to continue where you left off.")
    
    def _handle_error(self, error):
        """Handle errors gracefully"""
        print(f"🔍 Error details: {error}")
        print("💡 Try adjusting your settings or try again later.")
        print("🆘 If the problem persists, the profile might be private or restricted.")