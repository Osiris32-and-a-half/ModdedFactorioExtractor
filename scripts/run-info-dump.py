#!/usr/bin/env python3
"""Launch Factorio, run /ap-get-info-dump over RCON, and shut it down."""

import argparse
import json
import os
import re
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Deque, Optional, Tuple

import build as mod_build


ROOT: Path = Path(__file__).resolve().parents[1]
SPACE_AGE_DISABLED_MOD_LIST: Path = ROOT / "scripts" / "mod-list.json"
MOD_NAME = "modded-archipelago-extractor"
OLD_MOD_NAME = "archipelago-extractor"
SUPPORTED_FACTORIO_TARGETS = ("2.0", "2.1")
FACTORIO_VERSION_PATTERN = re.compile(r"Version:\s*(\d+\.\d+)\.\d+")


def send_packet(
    connection: socket.socket, request_id: int, packet_type: int, body: str
) -> None:
    payload = struct.pack("<ii", request_id, packet_type) + body.encode("utf-8") + b"\0\0"
    connection.sendall(struct.pack("<i", len(payload)) + payload)


def receive_exact(connection: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = connection.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError("Factorio closed the RCON connection")
        chunks.extend(chunk)
    return bytes(chunks)


def receive_packet(connection: socket.socket) -> Tuple[int, int, str]:
    size = struct.unpack("<i", receive_exact(connection, 4))[0]
    if size < 10 or size > 4 * 1024 * 1024:
        raise ConnectionError(f"Invalid RCON packet size: {size}")
    payload = receive_exact(connection, size)
    request_id, packet_type = struct.unpack("<ii", payload[:8])
    body = payload[8:-2].decode("utf-8", errors="replace")
    return request_id, packet_type, body


def detect_factorio_target(factorio: Path) -> str:
    result = subprocess.run(
        [str(factorio), "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    version_output = result.stdout + result.stderr
    version_match = FACTORIO_VERSION_PATTERN.search(version_output)
    if version_match is None:
        raise ValueError(f"Could not determine Factorio version:\n{version_output}")

    target = version_match.group(1)
    if target not in SUPPORTED_FACTORIO_TARGETS:
        supported = ", ".join(SUPPORTED_FACTORIO_TARGETS)
        raise ValueError(
            f"Unsupported Factorio version {target}; supported versions: {supported}"
        )
    print(f"Detected factorio version: {target}")
    return target


def build_mod_archive(target: str, output_directory: Path) -> Path:
    return mod_build.build_target(target, output_directory)


def stage_mods(
    staging_directory: Path,
    mod_archive: Path,
    installed_mods: Optional[Path],
    disable_space_age: bool,
) -> None:
    staging_directory.mkdir()
    if installed_mods is not None:
        if not installed_mods.is_dir():
            raise ValueError(f"Mod directory does not exist: {installed_mods}")
        for entry in installed_mods.iterdir():
            if entry.name.startswith((MOD_NAME, OLD_MOD_NAME)):
                continue
            destination = staging_directory / entry.name
            try:
                destination.symlink_to(entry, target_is_directory=entry.is_dir())
            except OSError:
                if entry.is_dir():
                    shutil.copytree(entry, destination)
                else:
                    shutil.copy2(entry, destination)

    mod_list = staging_directory / "mod-list.json"
    if not mod_list.exists() and disable_space_age:
        shutil.copy2(SPACE_AGE_DISABLED_MOD_LIST, mod_list)

    shutil.copy2(mod_archive, staging_directory / mod_archive.name)


def wait_for_rcon(
    process: subprocess.Popen[str],
    port: int,
    password: str,
    timeout: int,
    log_tail: Deque[str],
) -> socket.socket:
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Factorio exited with status {process.returncode}")
        try:
            connection = socket.create_connection(("127.0.0.1", port), timeout=1)
            connection.settimeout(1)
            send_packet(connection, 1, 3, password)
            request_id, _, _ = receive_packet(connection)
            if request_id != 1:
                connection.close()
                raise RuntimeError("Factorio rejected the RCON password")
            return connection
        except (ConnectionError, OSError, struct.error) as error:
            last_error = error
            time.sleep(0.5)

    detail = f": {last_error}" if last_error else ""
    recent_log = "".join(log_tail)
    raise TimeoutError(f"Factorio RCON did not become ready{detail}\n{recent_log}")


def run_dump(
    factorio: Path,
    installed_mods: Optional[Path],
    config_file: Optional[Path],
    save: Optional[Path],
    timeout: int,
    disable_space_age: bool,
) -> None:
    factorio_target = detect_factorio_target(factorio)
    log_tail = deque(maxlen=200)
    log_lock = threading.Lock()
    with tempfile.TemporaryDirectory(prefix="factorio-info-dump-") as temp_dir:
        temp_path = Path(temp_dir)
        mods_path = temp_path / "mods"
        mod_archive = build_mod_archive(factorio_target, temp_path / "build")
        stage_mods(mods_path, mod_archive, installed_mods, disable_space_age)
        save_path = save or (temp_path / "extractor-test.zip")

        common_args = [str(factorio), "--disable-audio", "--mod-directory", str(mods_path)]
        if config_file:
            common_args.extend(["--config", str(config_file)])
        if save is None:
            subprocess.run(
                [*common_args, "--create", str(save_path)],
                check=True,
            )
        elif not save.is_file():
            raise ValueError(f"Save file does not exist: {save}")

        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        password = secrets.token_urlsafe(24)
        process = subprocess.Popen(
            [
                *common_args,
                "--start-server",
                str(save_path),
                "--rcon-port",
                str(port),
                "--rcon-password",
                password,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def forward_output() -> None:
            if process.stdout is None:
                return
            for line in process.stdout:
                with log_lock:
                    log_tail.append(line)
                print(line, end="", flush=True)

        output_thread = threading.Thread(target=forward_output, daemon=True)
        output_thread.start()
        connection = None
        try:
            connection = wait_for_rcon(process, port, password, timeout, log_tail)
            connection.settimeout(0.5)
            send_packet(connection, 2, 2, "/ap-get-info-dump")
            command_deadline = time.monotonic() + timeout
            while time.monotonic() < command_deadline:
                if process.poll() is not None:
                    raise RuntimeError(
                        f"Factorio exited with status {process.returncode} while running the dump"
                    )
                try:
                    response_id, _, response = receive_packet(connection)
                    if response_id == 2:
                        if response:
                            print(f"Factorio response: {response}")
                        break
                except socket.timeout:
                    continue
            else:
                raise TimeoutError("Timed out waiting for /ap-get-info-dump to finish")

            time.sleep(0.5)
            with log_lock:
                recent_log = "".join(log_tail)
            if 'Error while running command "ap-get-info-dump"' in response:
                raise RuntimeError("Factorio reported an error while running the dump")
            elif 'Unknown command "ap-get-info-dump". Type /h or /help for more help about commands.' in response:
                raise RuntimeError("Factorio does not recognize the /ap-get-info-dump command; is the mod loaded?")
            print("Dump command completed.")
        finally:
            if connection is not None:
                connection.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            output_thread.join(timeout=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch Factorio and run /ap-get-info-dump over RCON."
    )
    parser.add_argument(
        "--factorio",
        type=Path,
        default=os.environ.get("FACTORIO_BIN"),
        help="Path to the Factorio executable (or set FACTORIO_BIN).",
    )
    parser.add_argument(
        "--mods",
        type=Path,
        help="Optional Factorio mods directory to load alongside the extractor.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional Factorio config.ini path.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        help="Optional existing save file; otherwise a temporary fresh map is created.",
    )
    parser.add_argument(
        "--disable-space-age",
        action="store_true",
        help="Use the bundled expansion-disabled mod list if no mod list exists.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Seconds to wait for Factorio/RCON and the dump command (default: 120).",
    )
    args = parser.parse_args()
    if args.factorio is None:
        parser.error("Pass --factorio or set FACTORIO_BIN.")
    args.factorio = args.factorio.expanduser().resolve()
    if not args.factorio.is_file():
        parser.error(f"Factorio executable not found: {args.factorio}")
    if args.mods is not None:
        args.mods = args.mods.expanduser().resolve()
    if args.config is not None:
        args.config = args.config.expanduser().resolve()
    if args.save is not None:
        args.save = args.save.expanduser().resolve()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero.")
    return args


def main() -> int:
    args = parse_args()
    try:
        run_dump(
            args.factorio,
            args.mods,
            args.config,
            args.save,
            args.timeout,
            args.disable_space_age,
        )
    except (OSError, RuntimeError, TimeoutError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
