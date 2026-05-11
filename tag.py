import subprocess
import re
import argparse

def run_command(command):
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL)
        return result.decode('utf-8').strip()
    except subprocess.CalledProcessError:
        return None

def get_commit_history(filename):
    """Returns a list of commit hashes where the file was changed, oldest to newest."""
    output = run_command(f"git log --reverse --format=%H -- {filename}")
    return output.split('\n') if output else []

def get_version_at_commit(commit_hash, filename):
    """Extracts the version string from a specific file at a specific commit."""
    content = run_command(f"git show {commit_hash}:{filename}")
    if not content:
        return None
    
    match = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", content)
    return match.group(1) if match else None

def apply_git_tag(tag_name, commit_hash, version, execute=False):
    """Checks for tag existence and optionally applies it."""
    exists = run_command(f"git rev-parse {tag_name}")
    
    if exists:
        print(f"[SKIP] {tag_name} already exists.")
        return False

    if execute:
        print(f"[ACTION] Tagging {commit_hash[:7]} as {tag_name}")
        run_command(f"git tag -a {tag_name} {commit_hash} -m 'Retroactive tag for version {version}'")
    else:
        print(f"[DRY-RUN] Would tag {commit_hash[:7]} as {tag_name}")
    
    return True

def sync_tags_from_history(filename="setup.py", execute=False):

    hashes = get_commit_history(filename)
    last_version = None
    tag_count = 0

    for commit_hash in hashes:
        current_version = get_version_at_commit(commit_hash, filename)
        
        if current_version and current_version != last_version:
            tag_name = f"v{current_version}"
            if apply_git_tag(tag_name, commit_hash, current_version, execute):
                tag_count += 1
            
            last_version = current_version

    print(f"\nTotal tags identified: {tag_count}")
    if not execute and tag_count > 0:
        print(">>> Run again with --execute to apply changes.")

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Retroactively tag versions.")
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()

    print(f"--- Starting Cleanup ({'EXECUTE' if args.execute else 'DRY-RUN'}) ---")
    sync_tags_from_history(execute=args.execute)