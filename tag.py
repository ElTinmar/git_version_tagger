import subprocess
import re
import argparse
from pathlib import Path

# Pre-compiled regex for better performance during history scanning
VERSION_RE = re.compile(
    r"^\s*version\s*=\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)

def run_command(args):
    """Executes a shell command and returns stripped output or None on failure."""
    try:
        result = subprocess.check_output(
            args,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return result.strip()
    except subprocess.CalledProcessError:
        return None

def get_commit_history(filename):
    """Returns a list of commit hashes where the file was changed, oldest to newest."""
    output = run_command([
        "git",
        "log",
        "--reverse",
        "--format=%H",
        "--",
        filename,
    ])
    return output.splitlines() if output else []

def get_version_at_commit(commit_hash, filename):
    """Extracts the version string from a specific file at a specific commit."""
    content = run_command([
        "git",
        "show",
        f"{commit_hash}:{filename}",
    ])

    if not content:
        return None

    match = VERSION_RE.search(content)
    return match.group(1) if match else None

def tag_exists(tag_name):
    """Checks if a git tag already exists in the local repository."""
    result = run_command([
        "git",
        "tag",
        "-l",
        tag_name,
    ])
    return bool(result)

def apply_git_tag(tag_name, commit_hash, version, execute=False):
    """Checks for tag existence and optionally applies an annotated tag."""
    if tag_exists(tag_name):
        print(f"[SKIP] {tag_name} already exists.")
        return False

    if execute:
        print(f"[ACTION] Tagging {commit_hash[:7]} as {tag_name}")
        try:
            subprocess.check_call([
                "git",
                "tag",
                "-a",
                tag_name,
                commit_hash,
                "-m",
                f"Retroactive tag for version {version}",
            ])
            return True
        except subprocess.CalledProcessError:
            print(f"[ERROR] Failed to apply tag {tag_name}")
            return False
    else:
        print(f"[DRY-RUN] Would tag {commit_hash[:7]} as {tag_name}")
        return True

def sync_tags_from_history(filename="setup.py", execute=False):
    """Orchestrates scanning history and applying tags when version changes."""
    hashes = get_commit_history(filename)
    if not hashes:
        print(f"No history found for '{filename}'. Ensure you are in the repo root.")
        return

    last_version = None
    tag_count = 0

    for commit_hash in hashes:
        current_version = get_version_at_commit(commit_hash, filename)
        
        # Only proceed if a version is found and it differs from the last seen version
        if current_version and current_version != last_version:
            tag_name = f"v{current_version}"
            
            if apply_git_tag(tag_name, commit_hash, current_version, execute):
                tag_count += 1
            
            last_version = current_version

    print(f"\nTotal tags identified: {tag_count}")
    
    if execute:
        if tag_count > 0:
            print("\nSUCCESS: Local tags applied.")
            print("To sync these with GitHub, run:")
            print("    git push origin --tags")
        else:
            print("No new versions were found to tag.")
    elif tag_count > 0:
        print("\n>>> Review the dry-run output above.")
        print(">>> To apply these tags locally, run with: --execute")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Retroactively tag Git commits based on version changes in a file."
    )
    parser.add_argument(
        "--file", 
        default="setup.py", 
        help="The file to monitor for version changes (default: setup.py)"
    )
    parser.add_argument(
        "--execute", 
        action="store_true", 
        help="Actually apply the tags to the local repository."
    )
    
    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"Error: File '{args.file}' not found. Please run this in your project root.")
    else:
        mode = "EXECUTION" if args.execute else "DRY-RUN"
        print(f"--- Starting Retroactive Tagging ({mode} mode) ---")
        sync_tags_from_history(filename=args.file, execute=args.execute)