# Containers and Docker

A container packages an application together with its dependencies so that it runs the
same way on any machine. This solves the classic problem where code works on a
developer's laptop but fails in production because some library version differs.

The key distinction from a virtual machine is that a container shares the host kernel
rather than booting its own operating system. A virtual machine virtualizes hardware
and runs a full guest OS, which is heavy; a container is just an isolated process on
the host, which is why containers start in milliseconds and use far less memory.

A Docker image is built from a layered filesystem. Each instruction in a Dockerfile
adds a layer, and layers are cached and shared between images. When you rebuild after
changing only your application code, the earlier layers, such as the installed
dependencies, are reused from cache, so only the changed layers are rebuilt.

An image is immutable: once built it never changes, which is what makes deployments
reproducible. A container is a running instance of an image, with a thin writable
layer on top for runtime changes that are discarded when the container is removed,
unless they are written to a mounted volume.

Volumes exist precisely because container filesystems are ephemeral. A volume is
storage managed outside the container's lifecycle, so a database's data or a shared
upload directory survives restarts and can be mounted into more than one container at
once, which is how the API and worker in this project share staged files.

Orchestration tools take this further by running many containers across many machines,
handling scheduling, restarts, and networking. Compose is the lightweight version used
here to declare the services, their dependencies, and how they connect as a single
unit.
