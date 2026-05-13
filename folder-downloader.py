#!/usr/bin/env python3
"""
GitHub Folder Downloader CLI Tool
Download a single folder from a GitHub repository without cloning the whole repo
"""

import os
import sys
import argparse
import requests
import urllib3
from pathlib import Path
from typing import List, Dict, Any

# Disable SSL warnings if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GitHubFolderDownloader:
    def __init__(self, token: str = None, no_ssl_verify: bool = False):
        self.session = requests.Session()
        self.no_ssl_verify = no_ssl_verify
        
        # Disable SSL verification if flag is set
        if no_ssl_verify:
            self.session.verify = False
            print("⚠️  Warning: SSL certificate verification is DISABLED")
        
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})
    
    def download_folder(self, repo_url: str, folder_path: str, output_dir: str = ".") -> bool:
        """
        Download a specific folder from GitHub repository
        """
        # Parse GitHub URL
        repo_path = self._parse_github_url(repo_url)
        if not repo_path:
            print(f"❌ Error: Invalid GitHub URL: {repo_url}")
            return False
        
        # Clean folder path
        folder_path = folder_path.strip('/')
        
        print(f"\n📁 Target: {repo_path}/{folder_path}")
        print(f"📂 Output directory: {output_dir}")
        
        # Build API URL
        api_url = f"https://api.github.com/repos/{repo_path}/contents/{folder_path}"
        
        try:
            # Get folder contents
            response = self.session.get(api_url)
            
            if response.status_code == 404:
                print(f"❌ Error: Folder '{folder_path}' not found in repository!")
                print(f"   Check the path and try again.")
                return False
            
            if response.status_code == 403:
                print(f"❌ Error: Rate limit exceeded. Please provide a GitHub token using --token")
                print(f"   Get your token at: https://github.com/settings/tokens")
                return False
            
            if response.status_code != 200:
                print(f"❌ Error: Failed to fetch data (HTTP {response.status_code})")
                return False
            
            contents = response.json()
            
            # Prepare output directory
            folder_name = os.path.basename(folder_path)
            output_path = Path(output_dir) / folder_name
            output_path.mkdir(parents=True, exist_ok=True)
            
            print(f"\n📥 Downloading files...")
            
            # Download all files
            stats = self._download_items(contents, output_path, repo_path, folder_path)
            
            # Print summary
            print(f"\n✅ Download complete!")
            print(f"   📁 Location: {output_path.absolute()}")
            print(f"   📄 Files downloaded: {stats['files']}")
            print(f"   📁 Subfolders: {stats['folders']}")
            
            if stats['failed'] > 0:
                print(f"   ⚠️  Failed downloads: {stats['failed']}")
            
            return True
            
        except requests.RequestException as e:
            print(f"❌ Network error: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return False
    
    def _download_items(self, items: List[Dict], output_path: Path, repo_path: str, current_folder_path: str) -> Dict[str, int]:
        """Download items recursively"""
        stats = {'files': 0, 'folders': 0, 'failed': 0}
        
        for item in items:
            if item['type'] == 'file':
                # Download single file
                if self._download_file(item['download_url'], output_path / item['name']):
                    stats['files'] += 1
                else:
                    stats['failed'] += 1
                    
            elif item['type'] == 'dir':
                # Handle subfolder
                stats['folders'] += 1
                subfolder_path = item['path']
                sub_api_url = f"https://api.github.com/repos/{repo_path}/contents/{subfolder_path}"
                
                try:
                    sub_response = self.session.get(sub_api_url)
                    if sub_response.status_code == 200:
                        sub_items = sub_response.json()
                        sub_output_path = output_path / item['name']
                        sub_stats = self._download_items(sub_items, sub_output_path, repo_path, subfolder_path)
                        
                        stats['files'] += sub_stats['files']
                        stats['folders'] += sub_stats['folders']
                        stats['failed'] += sub_stats['failed']
                    else:
                        print(f"   ⚠️  Failed to access subfolder: {item['name']}")
                        stats['failed'] += 1
                except Exception as e:
                    print(f"   ❌ Error downloading subfolder {item['name']}: {str(e)}")
                    stats['failed'] += 1
        
        return stats
    
    def _download_file(self, url: str, filepath: Path) -> bool:
        """Download a single file"""
        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file with optional SSL verification disabled
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            # Get file size for progress
            total_size = int(response.headers.get('content-length', 0))
            
            # Download with progress
            downloaded = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"   ⬇️  {filepath.name} [{percent:.1f}%]")
                        else:
                            print(f"   ⬇️  {filepath.name}")
            
            return True
            
        except requests.exceptions.SSLError as e:
            print(f"   ❌ SSL Error for {filepath.name}: {str(e)}")
            print(f"   💡 Tip: Use --no-ssl-verify flag to bypass SSL verification")
            return False
        except Exception as e:
            print(f"   ❌ Failed to download {filepath.name}: {str(e)}")
            return False
    
    def _parse_github_url(self, url: str) -> str:
        """Extract username/repo from GitHub URL"""
        # Remove protocol
        url = url.replace('https://', '').replace('http://', '')
        
        # Remove github.com prefix
        if url.startswith('github.com/'):
            url = url[11:]
        elif url.startswith('www.github.com/'):
            url = url[15:]
        else:
            return None
        
        # Remove trailing slash and .git
        url = url.rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]
        
        # Should be username/repo now
        parts = url.split('/')
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        
        return None

def main():
    parser = argparse.ArgumentParser(
        description='Download a single folder from GitHub repository without cloning',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://github.com/pandas-dev/pandas pandas/core
  %(prog)s https://github.com/tensorflow/tensorflow tensorflow/python/keras --output ./models
  %(prog)s https://github.com/facebook/react packages/react-dom --token ghp_xxxxx
  %(prog)s https://github.com/company/repo src/folder --no-ssl-verify
        """
    )
    
    parser.add_argument(
        'repo_url',
        help='GitHub repository URL (e.g., https://github.com/username/repo)'
    )
    
    parser.add_argument(
        'folder_path',
        help='Path to folder inside repository (e.g., src/utils or docs)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='.',
        help='Output directory (default: current directory)'
    )
    
    parser.add_argument(
        '-t', '--token',
        help='GitHub personal access token (for private repos or higher rate limits)'
    )
    
    parser.add_argument(
        '--no-ssl-verify',
        action='store_true',
        help='Disable SSL certificate verification (not recommended for production)'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate inputs
    if not args.repo_url or not args.folder_path:
        parser.print_help()
        sys.exit(1)
    
    # Check if requests is installed
    try:
        import requests
    except ImportError:
        print("❌ Error: 'requests' library is required")
        print("   Install it using: pip install requests")
        sys.exit(1)
    
    # Warning for SSL bypass
    if args.no_ssl_verify:
        print("⚠️  SECURITY WARNING: SSL certificate verification is disabled")
        print("   This connection is not secure and may be vulnerable to MITM attacks")
        print()
    
    # Create downloader instance
    downloader = GitHubFolderDownloader(token=args.token, no_ssl_verify=args.no_ssl_verify)
    
    # Download folder
    success = downloader.download_folder(
        repo_url=args.repo_url,
        folder_path=args.folder_path,
        output_dir=args.output
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
