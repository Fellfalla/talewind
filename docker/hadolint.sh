#!/usr/bin/env sh
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

# Find all Dockerfiles in the current directory and its subdirectories, ignoring '.dockerignore' files
DOCKERFILES=$(find $DIR -type f -regex ".*[Dd]ockerfile.*" ! -name "*.[Dd]ockerignore")
RESULT_CODE=""

# Iterate over each Dockerfile
for DOCKERFILE in $DOCKERFILES; do
  # Print the path of the Dockerfile
  echo "-------- Linting $DOCKERFILE via hadolint ----------"

  set +e # Don't stop execution if hadolint returns error code
  $(docker run --rm -i --name hado -v $DIR/hadolint.yaml:/.config/hadolint.yaml \
    hadolint/hadolint hadolint "$@" - <"$DOCKERFILE" >hadolint.report)
  HADO_RES=$?
  set -e

  # Get the return code of the docker https://stackoverflow.com/a/50153668/5006592
  # !! this must be executed directly after docker command

  cat hadolint.report

  RESULT_CODE=$RESULT_CODE$HADO_RES
  echo "ResultCode: $HADO_RES"

  echo
done

echo "Summary of hadolint: $RESULT_CODE"

exit $RESULT_CODE
