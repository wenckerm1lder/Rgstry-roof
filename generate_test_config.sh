GENERATED_CONFIG="test_registry.yaml"

CACHE_DIR=$CI_PROJECT_DIR/.cincan/cache

cat >> ${GENERATED_CONFIG} << EOF

# Configuration file of the cincan-registry Python module

registry: Quay  # Default registry wherefrom tools are used
cache_path: $CACHE_DIR # All cache files are in here
registry_cache_path: /home/nicce/.cincan/cache/tools.json # Contains details about tools (no version information)
tools_repo__path: None # Path for local 'tools' repository (Use metafiles from there)

# Configuration related to tool metafiles.

branch: master # Branch in GitLab for acquiring metafiles
meta_filename: meta.json # Filename of metafile in GitLab
index_filename: index.yml # Filename of index file in GitLab
disable_remote: False # Disable fetching metafiles from GitLab

tokens: # Possible authentication tokens to Quay, GitLab, GitHub and so on. Quay token is used for README updating.
    quay: ''
    github: '$GITHUB_TOKEN'
EOF

echo "Configuration file created into path: ${CI_PROJECT_DIR}/.cincan/cache"
mkdir -p "$CACHE_DIR"

ARTIFACT_LOCATION="https://gitlab.com/CinCan/cincan-registry/-/jobs/artifacts/master/raw/.cincan/cache/tooldb.sqlite?job=scrape_versions:on-schedule"
status_code=$(curl -L --write-out %{http_code} --silent --output /dev/null "$ARTIFACT_LOCATION")

if [[ "$status_code" -e 200 ]] ; then
    curl -L -o "$CACHE_DIR/tooldb.sqlite "$ARTIFACT_LOCATION"
else
    echo "No existing artifact found."
fi


