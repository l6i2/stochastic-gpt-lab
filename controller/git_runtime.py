"""Resolve Git for interactive and scheduled processes without changing PATH."""
from pathlib import Path
import shutil


def command(*arguments):
    found=shutil.which('git')
    candidates=[Path(found)] if found else []
    candidates.extend([Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe',
        Path('C:/Program Files/Git/cmd/git.exe')])
    executable=next((p for p in candidates if p.is_file()),None)
    if executable is None:raise RuntimeError('GIT_RUNTIME_UNAVAILABLE_NO_UNVERIFIED_HEAD')
    return [str(executable),*arguments]
