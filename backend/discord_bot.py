import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent

DEPLOY_BRANCH = os.getenv(
    "LOADX_DEPLOY_BRANCH",
    "desenvolvimento",
)

CHECK_INTERVAL_SECONDS = int(
    os.getenv(
        "LOADX_DEPLOY_INTERVAL",
        "60",
    )
)

RESTART_EXIT_CODE = 75


def _git_output(*args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT_DIR),
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )

    return result.stdout.strip()


def _local_head() -> str:
    return _git_output(
        "rev-parse",
        "HEAD",
    )


def _current_branch() -> str:
    return _git_output(
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
    )


def _remote_head(
    branch: str,
) -> str:
    output = _git_output(
        "ls-remote",
        "--heads",
        "origin",
        f"refs/heads/{branch}",
    )

    if not output:
        raise RuntimeError(f"Branch remota não encontrada: {branch}")

    return output.split()[0]


def _remote_update_available(
    branch: str,
) -> bool:
    current_branch = _current_branch()

    if current_branch != branch:
        raise RuntimeError(
            f"Branch local inesperada: {current_branch}. Esperada: {branch}."
        )

    return _local_head() != _remote_head(branch)


def _auto_deploy_enabled() -> bool:
    return os.getenv("AUTO_UPDATE") == "1"


def _start_bot() -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "app.integrations.discord.bot",
        ],
        cwd=BACKEND_DIR,
    )


def _stop_bot(
    process: subprocess.Popen[bytes],
) -> None:
    process.terminate()

    try:
        process.wait(timeout=10)

    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    bot_process = _start_bot()

    if not _auto_deploy_enabled():
        return bot_process.wait()

    print(
        "Auto deploy ativo: monitorando "
        f"origin/{DEPLOY_BRANCH} "
        f"a cada {CHECK_INTERVAL_SECONDS}s.",
        flush=True,
    )

    while True:
        try:
            return bot_process.wait(timeout=CHECK_INTERVAL_SECONDS)

        except subprocess.TimeoutExpired:
            pass

        try:
            update_available = _remote_update_available(DEPLOY_BRANCH)

        except (
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
        ) as exc:
            print(
                f"Falha ao verificar atualização remota; bot seguirá online: {exc}",
                flush=True,
            )

            continue

        if not update_available:
            continue

        print(
            "Nova versão detectada em "
            f"origin/{DEPLOY_BRANCH}. "
            "Reiniciando para atualizar...",
            flush=True,
        )

        _stop_bot(bot_process)

        return RESTART_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
