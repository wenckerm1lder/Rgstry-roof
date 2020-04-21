# CinCan registry

CinCan registry is  a tool for listing available CinCan tools, their versions and possible updates. 

Tools are available in the CinCan's [tool repository.](https://gitlab.com/CinCan/tools)

Currently, no other tools are supported for version information listing.

Remote tools are stored in Docker Hub, [under CinCan's profile.](https://hub.docker.com/u/cincan)

## Installation

Tool can be simply installed by running following command:

`pip install git+https://gitlab.com/cincan/cincan-registry`

Tool is not currently in pip, but might be in future.

## Usage

Tool can be used to list available local or remote tools, also possibly showing their versions, if they are correctly defined.
Tools is looking for `TOOL_VERSION` environment variable from the Docker image.

It is able to list upstream versions of some tools, where this feature is implemented. This is handled more thoroughly in [Upstream Checker section.](#upstream-checker)


To list both available local and remote tools, simply write
```
cincan-registry list

```

To list only locally available tools with tag "latest-stable":
```
cincan-registry list local
```

To do same for remote, use `remote` subcommend. By adding flag `-a`, this shows tools with all possible tags.
```
cincan-registry list remote -a 
```



## Upstream checker

This tool has feature check available new versions for tool, if this is configured for selected tool.

