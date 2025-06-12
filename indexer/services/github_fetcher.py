"""GitHub repository fetcher service.

Note: for simplicity we fetch the entire repo for each tag instead of using git checkout locally"""

import logging
import shutil
import zipfile
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


def download_repo(repo_url: str, target_dir: Path, tag: str = None) -> bool:
    """
    Download a GitHub repository to a target directory.

    Args:
        repo_url: GitHub repository URL
        target_dir: Directory to save the repository
        tag: Optional git tag/branch to checkout

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Construct ZIP download URL
        if tag:
            # For tags: https://github.com/owner/repo/archive/refs/tags/tag.zip
            zip_url = f"{repo_url.rstrip('/')}/archive/refs/tags/{tag}.zip"
        else:
            # For main branch: https://github.com/owner/repo/archive/refs/heads/main.zip
            zip_url = f"{repo_url.rstrip('/')}/archive/refs/heads/main.zip"

        logger.info(f"Downloading {zip_url} to {target_dir}")

        # Download the ZIP file
        response = requests.get(zip_url, stream=True)
        response.raise_for_status()

        # Save ZIP file temporarily
        zip_path = target_dir / "repo.zip"
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Extract ZIP file
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(target_dir)

        # Remove the ZIP file
        zip_path.unlink()

        # GitHub archives create a subdirectory with format "repo-tag" or "repo-branch"
        # Move contents up one level to target_dir
        extracted_dirs = [d for d in target_dir.iterdir() if d.is_dir()]
        if len(extracted_dirs) == 1:
            extracted_dir = extracted_dirs[0]
            # Move all contents from extracted_dir to target_dir
            for item in extracted_dir.iterdir():
                shutil.move(str(item), str(target_dir))
            # Remove the now-empty extracted directory
            extracted_dir.rmdir()

        logger.info(f"Successfully downloaded {repo_url}")
        return True

    except Exception as e:
        logger.error(f"Failed to download {repo_url}: {e}")
        # Clean up on failure
        if target_dir.exists():
            shutil.rmtree(target_dir)
        return False
