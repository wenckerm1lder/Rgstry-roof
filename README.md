[![pipeline status](https://gitlab.com/CinCan/cincan-registry/badges/master/pipeline.svg)](https://gitlab.com/CinCan/cincan-registry/commits/master)

# CinCan Registry

CinCan registry is  a tool for listing available CinCan tools, their versions and possible updates. 

Source code for tools' Dockerfiles are available in the CinCan's [tool repository.](https://gitlab.com/CinCan/tools)

Currently, no other tools are supported for version information listing.

Docker images of remote tools are stored in Docker Hub, [under CinCan's profile.](https://hub.docker.com/u/cincan)

This tool takes advantage of Docker Hub's registry API, when listing remote tools and their versions.

When checking versions beyond remote (Docker Hub), tool is using multiple different APIs such as GitHub's or Debian's. See [upstream checking.](#upstream-checker)

## Installation

Tool can be installed by running following command:

`pip install git+https://gitlab.com/cincan/cincan-registry`

Tool is not currently in pip, but should be in future.

## Usage

Tool can be used to list available local or remote CinCan tools, by also providing a possibly to show their versions, if they are correctly defined.
Tools is looking for `TOOL_VERSION` environment variable from the Docker image.

It is able to list upstream versions of some tools, where this feature is implemented. This is handled more thoroughly in [Upstream Checker section.](#upstream-checker)


To list both available local and remote tools, simply write
```
cincanegistry list

```
<img src="img/cincanreg_list.svg"  width="900" height="800">


To list only locally available tools with tag "latest-stable":
```
cincanregistry list local
```

To do same for remote, use `remote` subcommand. By adding flag `-a`, this shows tools with all possible tags.
```
cincanregistry list remote -a 
```



## Upstream checker

This tool has feature check available new versions for tool, if this feature is configured for selected tool.

