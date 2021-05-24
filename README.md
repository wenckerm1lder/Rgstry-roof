

# CinCan Registry

CinCan registry is  a tool for listing available CinCan tools, their versions, sizes and possible updates as far as into their original source. 

 Available tools can be found in the CinCan's [tool repository.](https://gitlab.com/CinCan/tools) Source code for tools' Dockerfiles is available in there.

Currently, no other tools are supported for version information listing or for other details.

Docker images of the remote tools are stored in [Quay](https://quay.io/organization/cincan), [GitHub's Container Registry](https://github.com/orgs/cincanproject/packages) and [Docker Hub](https://hub.docker.com/u/cincan).

By default, Quay has been used as image registry.

When checking versions beyond remote (remote registry), tool is using multiple different APIs such as GitHub's or GitLab's to acquire most recent availabe versions straight from the source. See more in [upstream checking.](#upstream-checker)

[![pipeline status](https://gitlab.com/CinCan/cincan-registry/badges/master/pipeline.svg)](https://gitlab.com/CinCan/cincan-registry/commits/master)

## Installation

Latest release can be installed from PyPi as:

`pip install cincan-registry`

To be able to list information from locally available tools, "Docker Daemon" must be running on your machine.

Tool is part of the [cincan-command](https://gitlab.com/CinCan/cincan-command). Command `cincanregistry` in future examples can be replaced with `cincan` when using in there.

Make sure that your PATH is working as intended, if not installing as 'sudo'.

## Usage

### Regular listing

Listing available local or remote CinCan tools with their sizes and versions is the general purpose of this program.

We are also able to list upstream versions of tools, for those where this feature is configured. This is handled more thoroughly in [Upstream Checker section.](#upstream-checker)


To list both available local and remote tools with tag "latest":
```
cincanregistry list

```

When running first time, output could look something like this:

<img src="https://gitlab.com/CinCan/cincan-registry/-/raw/master/img/list_tools.svg">



By default, "latest" tag is always used, unless over-written with `--tag` or `-t` argument.


To list only locally available tools with tag "latest", argument `--local` (or `-l`) can be used. Additionally, when listing only tools for specific location, listing will show all viable tags pointing into same image.

For example if version '0.1' of the tool is tagged with 'dev' tag, that specific tag should be used to use version '0.1' of the tool. 

```
cincanregistry list --local
```
Example output should look something like [this.](https://gitlab.com/CinCan/cincan-registry/-/raw/master/img/local_tool_list.png)


To do same for remote, use `--remote` (or `-r`) argument. By adding flag `-a`, this shows tools with all possible tags.
```
cincanregistry list --remote -a 
```

All commands are supporting JSON output. Add `--json` or `-j` argument. To combine previously mentioned `-t` flag, we can use following arguments to provide JSON output:

```
cincanregistry list -ljt dev
```
This lists locally available tools with 'dev' tag in JSON format.

JSON will contain also size of the images. 

For `local` images, size is as *uncompressed* and for remote images, as *compressed* size. 

By adding size column for regular listing, `--size` (or `-s`) argument can be used.

To list local images with all tags and size column included:

```
cincanregistry list -lsa
```

### Version listing and comparison

To see more about versions, we need to use `versions` subcommand. By running

```
cincanregistry list versions
```

tool will fetch version information from configured upstreams. By default, it lists only locally available tools, and compares their versions into remote versions, and further remote versions into upstream versions. 

**This helps us to acknowledge whether our tool is *really* up-to-date or not.**

Current implementation lists those tools as red `#AA0000`, where is immediate update available on remote. (local version differs from remote)

If local and remote are equal, but possible upstream of the tool has an update, those are listed as grey `#808080`. 

![Version listing example](https://gitlab.com/CinCan/cincan-registry/-/raw/master/img/version_list.png)

As seen in the above image, green should indicate, that at least for that line, everything there is *fine*.

Argument `--name` (or `-n`) can be used to check updates for single tool, and exclusive argument `--only-updates` or `-u` can be used to show only tools where there are updates available.

It should be noted, that tool is not able to directly tell, if there is actually newer version available. It only detects deviations. 

We can mark only deviations, because there is no golden standard for marking version information; it varies a lot among developers. However, tool is able to detect same versions with good accuracy, even if they are marked a bit differently.

Most of the preceding arguments with `list` subcommand will change the behavior of `versions` subcommand as well.

For example command:
```
cincanregistry list -rj versions --only-updates
```

Will produce JSON output from remote tools; generating their versions and filtering only for ones with available version updates, after checking configured upstreams for those available.


### All available options

| Specific to `list`      |    | Description |
|-------------------------|----|-------------|
| --config                | -c | Path to configuration file |
| --tag                   | -t | Filter images by tag name. |
| --all                   | -a | Show images with all tags. (Excludes --tag or -t) |
| --size                  | -s | Include  size column when listing |
| --json                  | -j | Produce output in JSON format
| --local                 | -l | List only locally available 'cincan' tools. Excludes --remote or -r
| --remote                | -r | List remotely available 'cincan' tools. Excludes --local or -l

Size will be here always included in JSON regardless is it used with argument or not.

| Specific to `list versions` |    | Description
|-------------------------|----|-------------|
| --name                  | -n | Check single tool by the name.
| --only-updates          | -u | Lists only available updates. Excludes --name or -n
| --with-tags             | -w | Include tag column when listing single tool; shows usable tags for that version.
| --force-refresh         | -f | Refresh all version related cache data including meta files.

These can be used with the combination of `list` options `-l` and `-r` to produce varying outputs. Arguments `-t`, `-a` and `-s` are ineffective when used with `versions` subcommand.

Tool is attempting to always find the latest available version among all tags.



### Utilities

> Only for development purpose

There is available feature to update description and README of the tool(s) in Quay and Docker Hub.

This requires locally cloned CinCan tools repository - READMEs from there are used.

For example command
```
cincanregistry -t ../tools utils update-readme --all
```

Uploads every README file for corresponding repository in CinCan's Quay Container Registry or Docker Hub. The first header (# ) of the README is used as *description* of image.

#### Providing credentials

```
docker login
```

Must be used beforehand to log in for Docker Hub - same credentials will be used on upload process.

#### All available options for 'utils'

| Specific to `utils`      |    | Description |
|-------------------------|----|-------------|
| --config                | -c | Path to configuration file |


| Specific to `utils update-readme` |    | Description
|-------------------------|----|-------------|
| --name                  | -n | Update README and description of single tool by the name.
| --all          |  | Attempt to update README and description of every tool from 'tools' folder, matching the repository on Docker Hub

## Upstream checker

CinCan Registry has a feature to check available new versions for tool, if this feature is just configured for selected tool and there is implementation for provider.

Currently, supported providers are:

* `GitHub` - versions by release, tag-release or commit
* `GitLab` - versions by release or tag-release
* `BitBucket` - versions by release or tag-release
* `Debian packages` - latest package version for any suite
* `Alpine packages` - latest package version for any Alpine version
* `PyPi` - latest release for any package
* `Tools by Didier Stevens` - latest release for any published tool in his GitHub repository with similar versioning
 
Multiple origins can be configured for every tool, however two should be enough, and in most cases just one. One for source of the tool (e.g. GitHub) and second origin for installation method in Dockerfile (e.g. tool installed as Alpine package into Dockerfile). Only one is needed and is ideal; hopefully tool is installed from direct source in Dockerfile.

### Configuring tool to be checked for origin version updates

Currently, configuration files, so called 'metafiles' are stored into same place as Dockerfiles: [CinCan's tool repository.](https://gitlab.com/CinCan/tools) Every file is named as `meta.json`.

Here is [example configuration](https://gitlab.com/CinCan/tools/-/blob/master/binwalk/meta.json) of binwalk. It has two providers where another is *source code* origin, and another is just *upstream for Dockefile*.

```json
{
  "upstreams": [
    {
      "uri": "https://github.com/ReFirmLabs/binwalk",
      "repository": "ReFirmLabs",
      "tool": "binwalk",
      "provider": "GitHub",
      "method": "release",
      "origin": true
    },
    {
      "uri": "https://sources.debian.org/api/src/binwalk/",
      "tool": "binwalk",
      "provider": "Debian",
      "method": "release",
      "suite": "buster",
      "docker_origin": true
    }
  ]
}
```
Required attributes depends on provider, but usually at least repository, tool, provider and method are required. URI might be enough some cases.

(TODO add provider  specific documentation)

These files are stored into Docker image at build phase as last layer into the image, making it possibly to fetch without pulling the whole image. **Cache is refreshed every 24 hours.**

However, there is option make tool to use local path, and disable remote downloading to help development. Path could be for example place, where you clone `tools` repository.

See [configuration for more details.](#Additional-configuration)


### Adding new provider

Adding new provider is straighforward - [inherit UpstreamChecker](cincanregistry/checkers/_checker.py) class and add implementation in the same folder. Existing implementations can be used as model. 

Short idea is, that there is meta file for every tool, containing upstream information in JSON format, and based on this information, correct provider implementation is selected, and tool information is forwarded for it, and finally version information is fetched from correct place with this way.

New provider class should implement at least one method `_get_version()` which returns latest version of tool from the provider, based on configuration.

As result. this *checker* just returns latest available version in configured format. (Latest release number, latest tag, latest commit? Or something else.)

Additionally, in [__init__](cincanregistry/checkers/__init__.py) file, provider name must be mapped for correct classname.

JSON file is given as dictionary parameter into constructor of UpstreamChecker, so all values should be accessible in child-class.

Once this is implemented, everything else should work automatically. Either tool with configuration for new provider is requred for testing, or simply add tests for it in [tests](tests) folder.

##  Additional configuration

By default, configuration file is stored in $HOME/.cincan/registry.yaml

Different file can be used with `--config` or `-c` option.

Configuration file does not have many options, but some are needed.

Data from remote registry and from upstreams is cached into specific path with `cache_path` attribute. This contains SQLite 3 database, which is used to manage all information.

`tools_repo_path` attribute can be used to set path for locally cloned [CinCan tools repository](https://gitlab.com/CinCan/tools). Then this local directory is used for meta files instead. Also some utilities are using this path (e.g. syncing README and description information into Docker Hub from tools repository.)

`tokens` attribute can contain multiple tokens with schema \<provider\>:token.
Tokens are helpful in cases, when API limit is needed to be increased for version checking. Caching is used to reduce the amount of requests.


`metadata_filename` is filename to be checked as metafile.

`disable_remote` when set as `True`, disables downloading of metafiles from GitLab, which are required for upstream checking, if files do not exist yet. Disabling might be helpful when some tool is in development phase and version checking is just to be added.


```yaml
# Configuration file of the cincan-registry Python module

registry: Quay  # Default registry wherefrom tools are used
cache_path: /home/nicce/.cincan/cache # All cache files are in here
tools_repo__path: None # Path for local 'tools' repository (Use metafiles from there)

# Configuration related to tool metafiles.

branch: master # Branch in GitLab for acquiring metafiles
meta_filename: meta.json # Filename of metafile in GitLab
index_filename: index.yml # Filename of index file in GitLab
disable_remote: False # Disable fetching metafiles from GitLab

tokens: # Possible authentication tokens to Quay, GitLab, GitHub and so on. Quay token is used for README updating.
    quay: '<my-token>'
    github: '<my-token>'
```


## Extra information

This tool takes advantage of [Docker Hub's Registry API](https://github.com/distribution/distribution/blob/main/docs/spec/api.md) from the selected registry, when listing remote tools and their sizes and versions. Version information is extracted from `container config` file, which is containing the configuration of Docker Image. `Manifest` has been used to detect the SHA256 digest for container config to be able to download it, as Manifest Schema v2 requires.

Version information value is acquired for `TOOL_VERSION` environment variable in the configuration.

This same variable is used for acquiring the version information on local as well, however we are using configuration information provided by `Docker Engine`.

Docker Images should have been build by using this variable, so the information is correct.

Manifest is also used to identify final layer from the image, to download `meta.json` file.
