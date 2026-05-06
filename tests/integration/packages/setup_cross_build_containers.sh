#!/bin/bash
# Set up LXD containers for cross-build integration testing.
# Creates one container per (Ubuntu release × target architecture) combination
# in the "copilot" LXD project.

set -euo pipefail

PROJECT="copilot"
RELEASES=("20.04" "22.04" "24.04" "25.10" "26.04")

# Target architectures to test cross-building for.
# riscv64 was only added in 20.10, so it's excluded for focal below.
TARGET_ARCHS=("arm64" "armhf" "i386" "ppc64el" "riscv64" "s390x")

# Map release versions to codenames
declare -A VERSION_TO_CODENAME=(
    ["20.04"]="focal"
    ["22.04"]="jammy"
    ["24.04"]="noble"
    ["25.10"]="questing"
    ["26.04"]="resolute"
)

archs_for_release() {
    local version="$1"
    if [[ "$version" == "20.04" ]]; then
        echo "arm64 armhf i386 ppc64el s390x"
    else
        echo "${TARGET_ARCHS[*]}"
    fi
}

setup_container() {
    local version="$1"
    local target_arch="$2"
    local codename="${VERSION_TO_CODENAME[$version]}"
    local container_name="cross-${version//./-}-${target_arch}"

    echo "=== Setting up ${container_name} (Ubuntu ${version} → ${target_arch}) ==="

    # Launch container if it doesn't exist
    if lxc info "$container_name" --project "$PROJECT" &>/dev/null; then
        echo "Container ${container_name} already exists, skipping launch."
    else
        echo "Launching ${container_name}..."
        lxc launch "ubuntu:${version}" "$container_name" --project "$PROJECT"
        echo "Waiting for cloud-init..."
        lxc exec "$container_name" --project "$PROJECT" -- cloud-init status --wait
    fi

    # Update package lists
    echo "Updating package lists..."
    lxc exec "$container_name" --project "$PROJECT" -- apt-get update -qq

    # Install test dependencies
    echo "Installing test dependencies..."
    lxc exec "$container_name" --project "$PROJECT" -- apt-get install -y -qq \
        python3 python3-pip python3-venv pipx git file chisel 2>/dev/null || \
    lxc exec "$container_name" --project "$PROJECT" -- apt-get install -y -qq \
        python3 python3-pip python3-venv git file

    echo "=== ${container_name} ready ==="
    echo ""
}

# Main
echo "Setting up cross-build test containers in LXD project '${PROJECT}'"
echo "Releases: ${RELEASES[*]}"
echo "Target architectures: ${TARGET_ARCHS[*]}"
echo ""

for version in "${RELEASES[@]}"; do
    archs=$(archs_for_release "$version")
    for arch in $archs; do
        setup_container "$version" "$arch"
    done
done

echo "All containers ready. List with: lxc list --project ${PROJECT}"
