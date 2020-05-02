[![pipeline status](https://gitlab.com/CinCan/cincan-registry/badges/master/pipeline.svg)](https://gitlab.com/CinCan/cincan-registry/commits/master)

# CinCan Registry

CinCan registry is  a tool for listing available CinCan tools, their versions, size and possible updates. 

 Available tools can be found in the CinCan's [tool repository.](https://gitlab.com/CinCan/tools) In practice, source code for tools' Dockerfiles is available in there.

Currently, no other tools are supported for version information listing or for other details.

Docker images of remote tools are stored in Docker Hub, [under CinCan's profile.](https://hub.docker.com/u/cincan)

When checking versions beyond remote (Docker Hub), tool is using multiple different APIs such as GitHub's or GitLab's to acquire most recent availabe versions straight from the source. See more in [upstream checking.](#upstream-checker)

## Installation

Tool can be installed by running following command:

`pip install git+https://gitlab.com/cincan/cincan-registry`

Tool is not currently in pip, but should be in future.

## Usage

### Regular listing

The main purpose is to list available local or remote CinCan tools and their sizes and versions.

We are also able to list upstream versions of tools, for those where this feature is configured. This is handled more thoroughly in [Upstream Checker section.](#upstream-checker)


To list both available local and remote tools with tag "latest-stable", simply write
```
cincanegistry list

```

By default, "latest-stable" tag is always used, unless overrided with `--tag` or `-t` argument.

<!-- <img src="img/cincanreg_list.svg"  width="900" height="800"> -->


To list only locally available tools with tag "latest-stable", argument `--local` (or `-l`) can be used. Additionally, when listing only tools for specfic location, listing will show all viable tags pointing into same image.

```
cincanregistry list --local
```

To do same for remote, use `--remote` (or `-r`) argument. By adding flag `-a`, this shows tools with all possible tags.
```
cincanregistry list --remote -a 
```

All commands are supporting JSON output. Simply add `--json` or `-j` argument. To combine previosly mentioned `-t` flag, we can use following arguments to provide JSON output:

```
cincanregistry list -ljt latest
```
This lists locally available tools with 'latest' tag in JSON format.

JSON will contain also size of the images. For `local` images, size is *uncompressed* and for remote images, it is *compressed* size. 

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

tool will fetch version information from configured upstreams. By default it lists only locally available tools, and compares their versions into remote versions, and further remote versions into upstream versions. 

**With help of this, we should be always acknowledged whether our tool is up-to-date or not!**

Current implemention lists those tools as red `#AA0000`, where is immediate update available on remote. (local version differs from remote)

If local and remote are equal, but possible upstream of the tool has update, those are listed as grey `#808080`. 

![Version listing example](img/version_list.png)
In this example, we have only single tool installed, `cincan/radare2`.




<!-- If we lint output for example with [jq](https://stedolan.github.io/jq/), we can see following output:
 -->



## More in depth

This tool takes advantage of Docker Hub's registry API, when listing remote tools and their versions.

However, there is also a possibility to show their exact versions, if they are correctly defined; version information is acquired for `TOOL_VERSION` environment variable from the Docker image.

## Upstream checker

CinCan Registry has feature to check available new versions for tool, if this feature is just configured for selected tool.

This is based on looking for latest available release, tag-release, commit or other means of providing version information in original sources.
