GENERATED_CONFIG="test_registry.yaml"

cat >> ${GENERATED_CONFIG} << EOF

# Configuration file of the cincan-registry Python module

registry: Quay  # Default registry wherefrom tools are used
cache_path: $CI_PROJECT_DIR/.cincan/cache # All cache files are in here
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
