#!/usr/bin/env python3
"""
Helm Push GitHub Action entrypoint.
Supports ECR OCI (access-token) or classic registry (username/password).
"""
import glob
import os
import subprocess
import sys
from urllib.parse import urlparse


def get_input(name: str, default: str = "") -> str:
    """Read action input from environment. GitHub Docker actions may pass INPUT_* with hyphens or underscores."""
    upper = name.upper()
    env_with_underscores = "INPUT_" + upper.replace("-", "_")
    env_with_hyphens = "INPUT_" + upper.replace("_", "-")
    return (
        os.environ.get(env_with_underscores)
        or os.environ.get(env_with_hyphens)
        or default
    ).strip()


def get_registry_host(registry_url: str) -> str:
    """Extract host from registry URL (oci://host/path or https://host/path)."""
    if registry_url.startswith("oci://"):
        url = "https://" + registry_url[6:]
    else:
        url = registry_url
    parsed = urlparse(url)
    if not parsed.netloc:
        print("error: could not parse registry host from URL", file=sys.stderr)
        sys.exit(1)
    return parsed.netloc


def _package_chart(chart_path: str, workspace: str) -> str:
    """Run helm package on a directory; return path to the created .tgz."""
    result = subprocess.run(
        ["helm", "package", chart_path],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )
    # Output: "Successfully packaged chart and saved it to: /path/name-version.tgz"
    for line in (result.stdout or "").strip().split("\n"):
        if "saved it to:" in line:
            path = line.split("saved it to:")[-1].strip()
            if os.path.isfile(path):
                return path
    # Fallback: find newest .tgz in workspace
    tgzs = glob.glob(os.path.join(workspace, "*.tgz"))
    if not tgzs:
        print("error: helm package did not produce a .tgz", file=sys.stderr)
        sys.exit(1)
    return max(tgzs, key=os.path.getmtime)


def main() -> None:
    registry_url = get_input("registry-url")
    chart_folder = get_input("chart-folder", "chart")
    force = get_input("force", "false").lower() == "true"
    plain_http = get_input("plain-http", "false").lower() == "true"

    if not registry_url:
        print("error: registry-url is required", file=sys.stderr)
        sys.exit(1)

    workspace = os.environ.get("GITHUB_WORKSPACE", ".")
    chart_path = os.path.join(workspace, chart_folder)

    if not os.path.exists(chart_path):
        print(f"error: chart not found: {chart_path}", file=sys.stderr)
        sys.exit(1)

    access_token = get_input("access-token")
    if access_token:
        # ECR OCI mode
        username = get_input("username") or "AWS"
        password = access_token
    else:
        # Classic registry (username + password)
        username = get_input("username")
        password = get_input("password")
        if not username or not password:
            print(
                "error: username and password are required when access-token is not set",
                file=sys.stderr,
            )
            sys.exit(1)

    if os.path.isdir(chart_path):
        chart_path = _package_chart(chart_path, workspace)
    elif not chart_path.endswith(".tgz"):
        print("error: chart must be a directory or a .tgz file", file=sys.stderr)
        sys.exit(1)

    registry_host = get_registry_host(registry_url)

    # helm registry login <host> --username ... --password-stdin [--plain-http]
    login_cmd = [
        "helm",
        "registry",
        "login",
        registry_host,
        "--username",
        username,
        "--password-stdin",
    ]
    if plain_http:
        login_cmd.append("--plain-http")
    try:
        subprocess.run(
            login_cmd,
            input=password.encode(),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print("error: helm registry login failed", file=sys.stderr)
        if e.stderr:
            print(e.stderr.decode(), file=sys.stderr)
        sys.exit(1)

    # helm push [chart] [registry_url] [--force] [--plain-http]
    push_cmd = ["helm", "push", chart_path, registry_url]
    if force:
        push_cmd.append("--force")
    if plain_http:
        push_cmd.append("--plain-http")

    try:
        subprocess.run(push_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("error: helm push failed", file=sys.stderr)
        if e.stderr:
            print(e.stderr.decode(), file=sys.stderr)
        sys.exit(1)

    # Set output for workflow
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write("push-status=success\n")

    print("Helm chart pushed successfully.")


if __name__ == "__main__":
    main()
