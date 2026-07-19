"""SSH/SFTP connection test.

Implements the spec scenario "Test the AutoDL connection": verifies SSH access,
the configured remote experiment root, and access to the configured ComfyUI
workspace (input + output directories). Reports SSH success separately from a
path failure, and reports a missing private key distinctly from an
authentication failure.
"""
from __future__ import annotations

import io
import socket
from dataclasses import dataclass
from pathlib import PurePosixPath

import paramiko

from app.core.config import AppConfig
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models import Connection
from app.schemas import ConnectionTestResult
from app.services import secrets


@dataclass
class _StageResult:
    ok: bool
    detail: str
    resolved: dict[str, str] | None = None


def _ssh_client(config: AppConfig, conn: Connection) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_bytes = secrets.read_secret(config, conn.private_key_ref)
    try:
        pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(key_bytes.decode("utf-8")))  # type: ignore[arg-type]
    except paramiko.SSHException:
        try:
            pkey = paramiko.RSAKey.from_private_key(io.StringIO(key_bytes.decode("utf-8")))  # type: ignore[arg-type]
        except paramiko.SSHException:
            pkey = paramiko.ECDSAKey.from_private_key(io.StringIO(key_bytes.decode("utf-8")))  # type: ignore[arg-type]
    client.connect(
        hostname=conn.host,
        port=conn.port,
        username=conn.username,
        pkey=pkey,
        timeout=10,
        banner_timeout=10,
        auth_timeout=10,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def check_connection(config: AppConfig, conn: Connection) -> ConnectionTestResult:
    log = get_logger("connection_test")

    # Stage 1: SSH access. Subdivide into network, missing key, auth.
    try:
        client = _ssh_client(config, conn)
    except NotFoundError as exc:
        log.info("ssh.missing_key")
        return ConnectionTestResult(
            ok=False,
            stage="ssh_access",
            detail=f"Private key file is not present: {exc.message}",
        )
    except FileNotFoundError as exc:
        log.info("ssh.missing_key")
        return ConnectionTestResult(
            ok=False,
            stage="ssh_access",
            detail=f"Private key file is missing on disk: {exc}",
        )
    except socket.gaierror as exc:
        log.info("ssh.dns_failed", host=conn.host)
        return ConnectionTestResult(
            ok=False,
            stage="ssh_access",
            detail=f"Host could not be resolved (network/DNS): {exc}",
        )
    except (socket.timeout, TimeoutError) as exc:
        log.info("ssh.timeout", host=conn.host)
        return ConnectionTestResult(
            ok=False,
            stage="ssh_access",
            detail=(
                "Could not reach the AutoDL instance within the timeout. "
                "Verify the instance is running and the port is correct. "
                f"({exc})"
            ),
        )
    except paramiko.AuthenticationException as exc:
        log.info("ssh.auth_failed")
        return ConnectionTestResult(
            ok=False,
            stage="ssh_access",
            detail=f"Authentication failed. Check the SSH key and username. ({exc})",
        )
    except paramiko.SSHException as exc:
        log.info("ssh.error")
        return ConnectionTestResult(
            ok=False,
            stage="ssh_access",
            detail=f"SSH error: {exc}",
        )

    resolved_paths: dict[str, str] = {}
    try:
        sftp = client.open_sftp()
        try:
            # Stage 2: remote_root exists and is accessible.
            try:
                stat = sftp.stat(conn.remote_root)
                resolved_paths["remote_root"] = conn.remote_root
            except FileNotFoundError:
                return ConnectionTestResult(
                    ok=False,
                    stage="remote_root",
                    detail=(
                        f"SSH succeeded but the configured remote root does not exist: "
                        f"{conn.remote_root}"
                    ),
                )
            except PermissionError as exc:
                return ConnectionTestResult(
                    ok=False,
                    stage="remote_root",
                    detail=f"SSH succeeded but the remote root is not accessible: {exc}",
                )

            # Stage 3: ComfyUI input + output directories.
            input_path = str(PurePosixPath(conn.remote_root) / conn.comfyui_input_path)
            output_path = str(PurePosixPath(conn.remote_root) / "output")
            input_ok = _safe_stat(sftp, input_path)
            output_ok = _safe_stat(sftp, output_path)
            resolved_paths["comfyui_input"] = input_path
            resolved_paths["comfyui_output"] = output_path
            if not input_ok and not output_ok:
                return ConnectionTestResult(
                    ok=False,
                    stage="comfyui_input",
                    detail=(
                        "SSH succeeded but neither the configured ComfyUI input nor the "
                        f"output directory exists under {conn.remote_root}. Verify "
                        "ComfyUI paths (input/, output/)."
                    ),
                    resolved_paths=resolved_paths,
                )
            return ConnectionTestResult(
                ok=True,
                stage="comfyui_input",
                detail="SSH, remote root, and ComfyUI workspace are reachable.",
                resolved_paths=resolved_paths,
            )
        finally:
            sftp.close()
    finally:
        client.close()


def _safe_stat(sftp: paramiko.SFTPClient, path: str) -> bool:
    try:
        sftp.stat(path)
        return True
    except FileNotFoundError:
        return False
    except PermissionError:
        return False
