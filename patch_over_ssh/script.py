import click
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

def setup_build_dir(build_dir: str) -> None:
    """Create build directory structure"""
    try:
        build_path = Path(build_dir).resolve()
        Path(build_path, 'scripts', 'files').mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        raise RuntimeError(f"Unable to create build directory: {e}")

def copy_file(src: Path, dst: Path) -> None:
    """Copy a single file with error handling"""
    try:
        shutil.copy2(src, dst)
    except (shutil.Error, OSError) as e:
        raise RuntimeError(f"Failed to copy {src} to {dst}: {e}")

def copy_scripts(src_dir: str, build_dir: str) -> None:
    """Copy scripts and their files to build directory"""
    try:
        src_path = Path(src_dir).resolve()
        build_path = Path(build_dir).resolve()
        
        # Copy shell scripts to scripts directory
        shutil.copytree(src_path, build_path / 'scripts',
                       dirs_exist_ok=True,
                       ignore=lambda d, files: [f for f in files if not f.endswith('.sh') and f != 'files'])
        
        # Copy files directory separately
        src_files = src_path / 'files'
        if src_files.exists():
            shutil.copytree(src_files, build_path / 'files', dirs_exist_ok=True)
            
    except Exception as e:
        raise RuntimeError(f"Failed to copy scripts and files: {e}")

def clean_scripts(build_dir: str) -> None:
    """Remove specified lines from shell scripts"""
    patterns = ['set -x', 'set -e', 'export LC_ALL=C', 'source /common.sh', 'install_cleanup_trap']
    
    try:
        scripts_path = Path(build_dir, 'scripts').resolve()
        for script in scripts_path.glob('*.sh'):
            with open(script, 'r') as f:
                lines = [line for line in f.readlines() 
                        if not any(pattern in line for pattern in patterns)]
            
            with open(script, 'w') as f:
                f.writelines(lines)
    except IOError as e:
        raise RuntimeError(f"Failed to clean scripts: {e}")

def run_script(script_path: Path, env_vars: Dict[str, str]) -> bool:
    """Execute a single script with the given environment variables"""
    if not script_path.exists():
        click.echo(f"Warning: Script {script_path} not found", err=True)
        return False
    
    # Skip scripts that start with 99
    if script_path.name.startswith('99'):
        click.echo(f"Skipping script {script_path.name} as it starts with 99")
        return True
        
    click.echo(f"Executing: {script_path.name}")
    
    try:
        script_path.chmod(0o755)
        subprocess.run([str(script_path)], env=env_vars, check=True)
        return True
    except (PermissionError, subprocess.CalledProcessError) as e:
        click.echo(f"Error executing {script_path.name}: {e}", err=True)
        return False

def get_ordered_scripts(scripts_dir: str) -> List[str]:
    """Get all shell scripts in numerical order"""
    try:
        return sorted(script.name for script in Path(scripts_dir).glob('[0-9][0-9]-*.sh'))
    except OSError as e:
        raise RuntimeError(f"Failed to get ordered scripts: {e}")

def replace_files_path(build_dir: str) -> None:
    """Replace /files with absolute path to files directory in all shell scripts"""
    try:
        scripts_path = Path(build_dir, 'scripts').resolve()
        files_path = Path(build_dir, 'files').resolve()
        
        for script in scripts_path.glob('*.sh'):
            with open(script, 'r') as f:
                content = f.read()
            
            # Replace with absolute path to files directory
            modified_content = content.replace('/files/', f'{files_path}/')
            modified_content = modified_content.replace('/files ', f'{files_path} ')
            modified_content = modified_content.replace('/files"', f'{files_path}"')
            modified_content = modified_content.replace("/files'", f"{files_path}'")
            
            with open(script, 'w') as f:
                f.write(modified_content)
    except IOError as e:
        raise RuntimeError(f"Failed to replace files paths: {e}")

def make_files_readable(build_dir: str) -> None:
    """Make all files in build directory readable by all users"""
    try:
        build_path = Path(build_dir).resolve()
        for root, dirs, files in os.walk(build_path):
            for d in dirs:
                Path(root, d).chmod(0o755)  # rwxr-xr-x for directories
            for f in files:
                Path(root, f).chmod(0o644)  # rw-r--r-- for files
    except OSError as e:
        raise RuntimeError(f"Failed to make files readable: {e}")

@click.command()
@click.option('--scripts-dir',
              help='Directory containing the scripts to process',
              required=True)
@click.option('--temp-dir',
              help='Build directory where scripts will be copied and executed',
              required=True)
@click.option('--dry-run', is_flag=True,
              help='Show what would be done without executing scripts')
@click.option('--scripts', '-s', multiple=True,
              help='Specific scripts to run (e.g., -s 00-update-system.sh -s 01-make-pioreactor-user.sh)')
def main(scripts_dir: str, temp_dir: str, dry_run: bool, scripts: Optional[tuple]) -> None:
    """Process and execute configuration scripts with the specified parameters."""
    
    try:
        if not scripts_dir or not temp_dir:
            raise click.UsageError("--scripts-dir and --temp-dir are required arguments")

        # Resolve absolute paths
        scripts_dir = str(Path(scripts_dir).resolve())
        temp_dir = str(Path(temp_dir).resolve())

        env_vars = {
            **os.environ,
        }
        
        click.echo("Setting up build environment...")
        setup_build_dir(temp_dir)
        
        click.echo("Copying scripts...")
        copy_scripts(scripts_dir, temp_dir)
        
        click.echo("Cleaning scripts...")
        clean_scripts(temp_dir)
        
        click.echo("Replacing files paths...")
        replace_files_path(temp_dir)
        
        click.echo("Making files readable...")
        make_files_readable(temp_dir)
        
        scripts_to_run = list(scripts) if scripts else get_ordered_scripts(scripts_dir)
        
        if dry_run:
            click.echo("\nDry Run - Would Execute These Scripts:")
            for script in scripts_to_run:
                click.echo(f"- {script}")
            return
        
        for script in scripts_to_run:
            script_path = Path(temp_dir) / 'scripts' / script
            if not run_script(script_path, env_vars):
                raise RuntimeError(f"Failed to execute {script}")
        
        click.echo("All scripts executed successfully!")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        exit(1)

if __name__ == '__main__':
    main()