#!/bin/bash

# Copyright 2021 The KubeEdge Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -o errexit
set -o nounset
set -o pipefail

readonly REPO=roboartisan-term/robot-teleop
readonly TMP_DIR=$(mktemp -d --suffix=.roboartisan)
readonly DEFAULT_ROBOSDK_VERSION=0.0.1

if [ -z "$IMAGE_REPO" ]
then
   echo "Using default Docker hub"
   IMAGE_REPO="kubeedge"
fi

trap "rm -rf '$TMP_DIR'" EXIT 

function get_latest_version() {
    {
    curl -s https://raw.githubusercontent.com/${REPO}/main/VERSION |
    sed 's/ //g'|sed /^$/d
  } || echo $DEFAULT_ROBOSDK_VERSION # fallback
}

function check_kubectl () {
    kubectl get pod >/dev/null
}

function check_nodes () {
    kubectl get nodes -l kubernetes.io/deploy=roboartisan -ojsonpath='{.items[*].metadata.name}'
}

function do_check() {
  check_kubectl
  check_nodes
}

function download_configs() {
    yaml_dir=scripts/build
    yaml_files=(
        teleop.yaml
    )

    for yaml in ${yaml_files[@]}; do
        if [ ! -e $yaml_dir/${yaml} ]
        then
            echo "downloading $yaml into $yaml_dir"

            local try_times=30 i=1 timeout=2
            while ! timeout ${timeout}s curl -sS -o ${yaml_dir}/${yaml} https://raw.githubusercontent.com/${REPO}/main/${yaml_dir}/${yaml}; do
                ((++i>try_times)) && {
                    echo timeout to download $yaml
                    exit 2
                }
                echo -en "retrying to download $yaml after $[i*timeout] seconds...\r"
            done
        fi
    done
}

function build_images() {
    dockerfiles=(
        client
        robot
        server
    )

    for dockerfile in ${dockerfiles[@]}; do
        echo "Building $dockerfile"
        file_uri=${dockerfile}/Dockerfile
        docker build -f $file_uri -t ${REPO_PREFIX}${dockerfile}:${REPO_VERSION} --label roboartisan=app ..
    done
}

function deploy_app() {
    download_configs

}

function prepare() {
    do_check
}

function build() {
    build_images
}

function deploy() {

}

CLUSTER_NODES=($(echo "${CLUSTER_NODES[@]}" | tr ' ' '\n' | sort -u))

: ${REPO_VERSION:=$(get_latest_version)}
: ${REPO_PREFIX}=${IMAGE_REPO}/robot-teleop-