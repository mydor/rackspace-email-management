#!/bin/bash
#

ARGS=""
CACHE=".setup.cache"
DEFAULT_DIR="env"
DEFAULT_PROMPT="dev"
PROG="$0"
REQ=""
sourced=""
VENV_DIR=""
VENV_PROMPT=""
PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

clear_var () {
  unset DEFAULT_DIR DEFAULT_PROMPT
  unset VENV_DIR    VENV_PROMPT
  unset ARGS CACHE PROG REQ sourced
  unset -f isexit sourced clear_var help setup_req
}

isexit () {
  sourced && clear_var && return 1

  clear_var
  return 0
}

sourced () {
  [ -n "$sourced" ] && return 0 || return 1
}

setup_req () {
    reqver_file="requirements.txt-${PYTHON_VER}"
    reqdist_file="requirements.txt.dist"
    req_file="requirements.txt"

    if [ ! -f "${reqver_file}" ]; then
        cp -v "${reqdist_file}" "${reqver_file}"
    fi

    target=$(basename $(readlink -f "${req_file}"))

    if \
       [ ! -f "${req_file}" ] ||           # No requirements file
       [ "${target}" == "${req_file}" ] || # Requirements file no symlink
       [ "${target}" != "${reqver_file}" ] # Requirements file pointing to another python version
    then
	ln -sf "${reqver_file}" "${req_file}"
    fi
}

help () {
  echo "$PROG [[-d | --dir] <venv_dir>] [[-p | --prompt] <venv_prompt>]" >&2
  echo ""
  echo "  -h       This help message"
  echo "  --help   This help message"
  echo "  -d       <venv_dir>     Venv directory to setup"
  echo "  --dir    <venv_dir>     Venv directory to setup"
  echo "  -p       <venv_prompt>  Venv prompt to use"
  echo "  --prompt <venv_prompt>  Venv prompt to use"
  echo ""
  echo "NOTE: Use command line switches or arguments, not both"
}

if [ "$0" == "bash" ]; then
  sourced=true
  PROG="source ${BASH_SOURCE[0]}"
elif [ ! -f "$0" ]; then
  PROG="source ${BASH_SOURCE[0]}"
  sourced=true
fi

while (( "$#" )); do
  case "$1" in
    -h|--help)
      help && isexit && exit 1 || return 1
      shift
      ;;
    -d|--dir)
      VENV_DIR="$2"
      shift 2
      ;;
    -p|--prompt)
      VENV_PROMPT="$2"
      shift 2
      ;;
    -r|--requirements)
      REQ="install"
      shift
      ;;
    -*|--*)
      echo "Error: Unsupported flag $1"
      isexit && exit 1 || return 1
      ;;
    *)
      ARGS="$ARGS $1"
      shift
      ;;
  esac
done

eval set -- "$ARGS"

[ -z "$VENV_DIR" ]    && [ -n "$1" ] && VENV_DIR="$1"
[ -z "$VENV_PROMPT" ] && [ -n "$2" ] && VENV_PROMPT="$2"

VENV_DIR="${VENV_DIR:=${DEFAULT_DIR}}"
VENV_PROMPT="${VENV_PROMPT:=${DEFAULT_PROMPT}}"

if [ ! -d "${VENV_DIR}" ]; then
  # Setup python3 Venv
  python3 -mvenv --prompt "${VENV_PROMPT}" "${VENV_DIR}"

  # Activate Venv for setup
  . "${VENV_DIR}"/bin/activate

  # Update pip to latest
  pip install --upgrade pip

  # Setup the requrements file
  setup_req

  # Install required packages
  pip install -r requirements.txt

  # deactivate, yes we will re-activate shortly (IF SOURCED)
  # But, this block only runs for initial setup
  deactivate

  REQ=""
  ### echo "VENV_DIR=\"${VENV_DIR}\"" >"${CACHE}"
  ### echo "VENV_PROMPT=\"${VENV_PROMPT}\"" >>"${CACHE}"
fi

if [ -n "$REQ" ]; then
  . "${VENV_DIR}"/bin/activate

  # Setup the requrements file
  setup_req

  pip install -r requirements.txt | fgrep -v -e 'Requirement already satisfied'

  deactivate
fi

if sourced; then
  source "${VENV_DIR}/bin/activate"
  clear_var
else
  echo -e "\nYou must now run \`source "${VENV_DIR}/bin/activate"\`\n"
fi
