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

function download() {
    target_uri=$1
    download_dir=$2
    file_name=($(basename $target_uri))
    echo "downloading $target_uri into $download_dir"

    local try_times=30 i=1 timeout=2
    while ! timeout ${timeout}s curl -sS -o ${download_dir}/${file_name} $target_uri; do
        ((++i>try_times)) && {
            echo timeout to download $file_name
            exit 2
        }
        echo -en "retrying to download $file_name after $[i*timeout] seconds...\r"
    done
}

function deploy_app() {
    yaml_dir=build
    yaml_files=(
        conf
        turnserver
        server
        client
        robot
    )

    for yaml in ${yaml_files[@]}; do
        file_uri=${yaml_dir}/teleop-${yaml}.yaml

        if [ ! -e ${file_uri} ]
        then
            download https://raw.githubusercontent.com/${REPO}/main/scripts/${file_uri} $yaml_dir
        fi

        kubectl apply -f ${file_uri}
    done

}

function build_images() {
    df_dir=build 
    dockerfiles=(
        client
        robot
        server
        turnserver
    )

    for dockerfile in ${dockerfiles[@]}; do
        file_uri=${df_dir}/${dockerfile}.Dockerfile

        if [ ! -e ${file_uri} ]
        then
            download https://raw.githubusercontent.com/${REPO}/main/scripts/${file_uri} $df_dir
        fi

        echo "Building $dockerfile"
        docker build -f $file_uri -t ${REPO_PREFIX}${dockerfile}:${REPO_VERSION} --label roboartisan=app .. &
    done

    wait
}

function build() {
    build_images
}

function deploy() {
    do_check
    deploy_app
}

CLUSTER_NODES=($(echo "${CLUSTER_NODES[@]}" | tr ' ' '\n' | sort -u))

: ${REPO_VERSION:=$(get_latest_version)}
: ${REPO_PREFIX}=${IMAGE_REPO}/robot-teleop-